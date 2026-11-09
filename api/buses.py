"""車輛資料庫 API。SQL 定義統一引用 api/sql.py。"""

import hmac
import secrets

import psycopg2
from flask import current_app, jsonify, request, session
from psycopg2.extras import RealDictCursor

from link import get_connection
from .sql import (BACKSTAGE_LIST_BUSES, BACKSTAGE_INSERT_BUS,
                  BACKSTAGE_UPDATE_BUS, BACKSTAGE_DELETE_BUS)


def _response(payload, status=200):
    response = jsonify(payload)
    response.headers['Cache-Control'] = 'no-store'
    return response, status


def _error(message, status):
    return _response({'status': 'error', 'message': message}, status)


def _csrf_token():
    if 'backstage_api_csrf' not in session:
        session['backstage_api_csrf'] = secrets.token_urlsafe(32)
    return session['backstage_api_csrf']


def _valid_csrf():
    expected = session.get('backstage_api_csrf')
    supplied = request.headers.get('X-CSRF-Token', '')
    return isinstance(expected, str) and hmac.compare_digest(expected.encode(), supplied.encode())


def _valid_name(value):
    return isinstance(value, str) and bool(value.strip()) and len(value.strip()) <= 50 and '\x00' not in value


def _rollback(conn):
    if conn is not None:
        try:
            conn.rollback()
        except Exception:
            # 連線已中斷時仍須回傳明確錯誤，不能因 rollback 再次失敗而蓋掉。
            pass


def list_buses():
    """GET /api/buses；keyword 可空。"""
    keyword = request.args.get('keyword', '').strip()
    if len(keyword) > 200:
        return _error('搜尋關鍵字不得超過 200 字元。', 400)
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(BACKSTAGE_LIST_BUSES, {'keyword': keyword or None})
            rows = [dict(row) for row in cur.fetchall()]
        return _response({'status': 'ok', 'buses': rows, 'count': len(rows), 'csrfToken': _csrf_token()})
    except Exception:
        current_app.logger.warning('Bus type list database query failed.')
        return _error('無法讀取車輛資料，請確認資料庫連線後重試。', 503)
    finally:
        if conn is not None:
            conn.close()


def _write(query, params, success_message, success_status=200):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        if row is None:
            _rollback(conn)
            return _error('此車輛已不存在，請重新載入列表。', 404)
        record = dict(row)
        conn.commit()
        return _response({'status': 'ok', 'bus': record, 'message': success_message}, success_status)
    except psycopg2.IntegrityError as error:
        _rollback(conn)
        if error.pgcode == '23505':
            return _error('此車牌號碼已存在，請確認是否重複新增。', 409)
        if error.pgcode == '23503':
            return _error('車型不存在，或此車輛仍有派車紀錄；請重新載入並確認相關資料。', 409)
        return _error('資料不符合資料庫限制，請確認車牌號碼與車型。', 400)
    except Exception:
        _rollback(conn)
        current_app.logger.warning('Bus type database update failed.')
        return _error('資料庫操作失敗，請重新載入確認目前資料後再試。', 503)
    finally:
        if conn is not None:
            conn.close()


def create_bus():
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {'bId', 'busType'} or not all(_valid_name(payload.get(k)) for k in ('bId', 'busType')):
        return _error('請填寫 1 至 50 字的車牌號碼，並選擇車型。', 400)
    return _write(BACKSTAGE_INSERT_BUS, {k: payload[k].strip() for k in ('bId', 'busType')}, '已新增資料庫車輛。', 201)


def update_bus(bus_id):
    # 車牌為既有 SQL 的主鍵；編輯只更新車型，避免變更派車識別。
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    payload = request.get_json(silent=True)
    if not _valid_name(bus_id) or not isinstance(payload, dict) or set(payload) != {'busType'} or not _valid_name(payload.get('busType')):
        return _error('請選擇有效車型；編輯時不可變更車牌號碼或容載人數。', 400)
    return _write(BACKSTAGE_UPDATE_BUS, {'bId': bus_id, 'busType': payload['busType'].strip()}, '已更新資料庫車輛。')


def delete_bus(bus_id):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    if not _valid_name(bus_id):
        return _error('車牌號碼不正確。', 400)
    return _write(BACKSTAGE_DELETE_BUS, {'bId': bus_id}, '已刪除資料庫車輛。')
