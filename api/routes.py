"""路線管理 API；SQL 統一引用 api/sql.py，不使用瀏覽器示範資料。"""
import hmac
import secrets

import psycopg2
from flask import current_app, jsonify, request, session
from psycopg2.extras import RealDictCursor

from link import get_connection
from .sql import (BACKSTAGE_LIST_ROUTES, BACKSTAGE_INSERT_ROUTE,
                  BACKSTAGE_UPDATE_ROUTE, BACKSTAGE_LOCK_ROUTE, BACKSTAGE_DELETE_ROUTE)


def _response(payload, status=200):
    response = jsonify(payload)
    response.headers['Cache-Control'] = 'no-store'
    return response, status


def _error(message, status):
    return _response({'status': 'error', 'message': message}, status)


def _csrf_token():
    # 與其他後台 API 使用同一個 session token；不是管理者登入權限。
    if 'backstage_api_csrf' not in session:
        session['backstage_api_csrf'] = secrets.token_urlsafe(32)
    return session['backstage_api_csrf']


def _valid_csrf():
    expected = session.get('backstage_api_csrf')
    supplied = request.headers.get('X-CSRF-Token', '')
    return isinstance(expected, str) and hmac.compare_digest(expected.encode(), supplied.encode())


def _rollback(conn):
    if conn is not None:
        try:
            conn.rollback()
        except Exception:
            pass


def _valid_text(value, maximum):
    return isinstance(value, str) and 0 < len(value.strip()) <= maximum and '\x00' not in value


def _route_payload(route_id=None):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, '請以 JSON 傳送路線資料。'
    if route_id is None:
        route_id = payload.get('routeId')
    elif 'routeId' in payload and payload['routeId'] != route_id:
        return None, '編輯時不可變更路線編號。'
    if not _valid_text(route_id, 50):
        return None, '請填寫 1 至 50 字的路線編號。'
    if not _valid_text(payload.get('routeName'), 100):
        return None, '請填寫 1 至 100 字的路線名稱。'
    for key, label in (('origin', '起點'), ('destination', '終點')):
        if not _valid_text(payload.get(key), 100):
            return None, f'請填寫 1 至 100 字的{label}。'
    allowed = {'routeName', 'origin', 'destination'} | ({'routeId'} if 'routeId' in payload else set())
    if set(payload) != allowed:
        return None, '路線資料包含不支援的欄位，或缺少必要欄位。'
    return {'routeId': route_id.strip(), **{k: payload[k].strip() for k in ('routeName', 'origin', 'destination')}}, None



def list_routes():
    """GET /api/routes；管理用完整清單，可選填 keyword。"""
    keyword = request.args.get('keyword', '').strip()
    if len(keyword) > 200:
        return _error('搜尋關鍵字不得超過 200 字元。', 400)
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(BACKSTAGE_LIST_ROUTES, {'keyword': keyword or None})
            rows = [dict(row) for row in cur.fetchall()]
        return _response({'status': 'ok', 'routes': rows, 'count': len(rows), 'csrfToken': _csrf_token()})
    except Exception:
        current_app.logger.warning('Route list database query failed.')
        return _error('無法讀取路線資料，請確認資料庫連線後重試。', 503)
    finally:
        if conn is not None:
            conn.close()


def _write(query, params, message, status=200, delete=False):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if delete:
                # 先鎖定目標，讓後續引用檢查和刪除使用同一交易，保護收藏不被 CASCADE 刪除。
                cur.execute(BACKSTAGE_LOCK_ROUTE, params)
                if cur.fetchone() is None:
                    _rollback(conn)
                    return _error('此路線已不存在，請重新載入列表。', 404)
            cur.execute(query, params)
            row = cur.fetchone()
        if row is None:
            _rollback(conn)
            if delete:
                return _error('此路線仍被站序、班次或會員收藏使用，請先處理相關資料後再刪除。', 409)
            return _error('此路線已不存在，請重新載入列表。', 404)
        record = dict(row)
        conn.commit()
        return _response({'status': 'ok', 'route': record, 'message': message}, status)
    except psycopg2.IntegrityError as error:
        _rollback(conn)
        if error.pgcode == '23505':
            return _error('此路線編號已存在，請使用不同編號。', 409)
        if error.pgcode == '23503':
            return _error('此路線仍被其他資料使用，無法刪除。', 409)
        return _error('路線資料不符合資料庫限制，請確認路線編號、名稱及起訖站。', 400)
    except Exception:
        _rollback(conn)
        current_app.logger.warning('Route database update failed.')
        return _error('資料庫操作失敗，請重新載入確認目前資料後再試。', 503)
    finally:
        if conn is not None:
            conn.close()


def create_route():
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    params, error = _route_payload()
    if error:
        return _error(error, 400)
    return _write(BACKSTAGE_INSERT_ROUTE, params, '已新增資料庫路線。', 201)


def update_route(route_id):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    params, error = _route_payload(route_id)
    if error:
        return _error(error, 400)
    return _write(BACKSTAGE_UPDATE_ROUTE, params, '已更新資料庫路線。')


def delete_route(route_id):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    if not _valid_text(route_id, 50):
        return _error('路線編號不正確。', 400)
    return _write(BACKSTAGE_DELETE_ROUTE, {'routeId': route_id}, '已刪除資料庫路線。', delete=True)
