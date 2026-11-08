"""站點管理 API；SQL 統一引用 api/sql.py，不使用瀏覽器示範資料。"""
import hmac
import math
import secrets

import psycopg2
from flask import current_app, jsonify, request, session
from psycopg2.extras import RealDictCursor

from link import get_connection
from .sql import (BACKSTAGE_LIST_STATIONS, BACKSTAGE_INSERT_STATION,
                  BACKSTAGE_UPDATE_STATION, BACKSTAGE_LOCK_STATION, BACKSTAGE_DELETE_STATION)


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


def _coordinate(value, bound):
    return type(value) in (int, float) and math.isfinite(value) and -bound <= value <= bound


def _station_payload(station_id=None):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, '請以 JSON 傳送站點資料。'
    if station_id is None:
        station_id = payload.get('stationId')
    elif 'stationId' in payload and payload['stationId'] != station_id:
        return None, '編輯時不可變更站點編號。'
    if not _valid_text(station_id, 50):
        return None, '請填寫 1 至 50 字的站點編號。'
    if not _valid_text(payload.get('sName'), 100):
        return None, '請填寫 1 至 100 字的站點名稱。'
    if not _valid_text(payload.get('address'), 255):
        return None, '請填寫 1 至 255 字的站點地址。'
    if not _coordinate(payload.get('sLatitude'), 90):
        return None, '緯度必須是 -90 至 90 的有效數值。'
    if not _coordinate(payload.get('sLongitude'), 180):
        return None, '經度必須是 -180 至 180 的有效數值。'
    return {'stationId': station_id.strip(), 'sName': payload['sName'].strip(),
            'address': payload['address'].strip(), 'sLatitude': payload['sLatitude'],
            'sLongitude': payload['sLongitude']}, None


def list_stations():
    """GET /api/stations；管理用完整清單，可選填 keyword。"""
    keyword = request.args.get('keyword', '').strip()
    if len(keyword) > 200:
        return _error('搜尋關鍵字不得超過 200 字元。', 400)
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(BACKSTAGE_LIST_STATIONS, {'keyword': keyword or None})
            rows = [dict(row) for row in cur.fetchall()]
        return _response({'status': 'ok', 'stations': rows, 'count': len(rows), 'csrfToken': _csrf_token()})
    except Exception:
        current_app.logger.warning('Station list database query failed.')
        return _error('無法讀取站點資料，請確認資料庫連線後重試。', 503)
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
                cur.execute(BACKSTAGE_LOCK_STATION, params)
                if cur.fetchone() is None:
                    _rollback(conn)
                    return _error('此站點已不存在，請重新載入列表。', 404)
            cur.execute(query, params)
            row = cur.fetchone()
        if row is None:
            _rollback(conn)
            if delete:
                return _error('此站點仍被路線、班次時間或會員收藏使用，請先處理相關資料後再刪除。', 409)
            return _error('此站點已不存在，請重新載入列表。', 404)
        record = dict(row)
        conn.commit()
        return _response({'status': 'ok', 'station': record, 'message': message}, status)
    except psycopg2.IntegrityError as error:
        _rollback(conn)
        if error.pgcode == '23505':
            return _error('此站點編號已存在，請使用不同編號。', 409)
        if error.pgcode == '23503':
            return _error('此站點仍被其他資料使用，無法刪除。', 409)
        return _error('站點資料不符合資料庫限制，請確認欄位及經緯度。', 400)
    except Exception:
        _rollback(conn)
        current_app.logger.warning('Station database update failed.')
        return _error('資料庫操作失敗，請重新載入確認目前資料後再試。', 503)
    finally:
        if conn is not None:
            conn.close()


def create_station():
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    params, error = _station_payload()
    if error:
        return _error(error, 400)
    return _write(BACKSTAGE_INSERT_STATION, params, '已新增資料庫站點。', 201)


def update_station(station_id):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    params, error = _station_payload(station_id)
    if error:
        return _error(error, 400)
    return _write(BACKSTAGE_UPDATE_STATION, params, '已更新資料庫站點。')


def delete_station(station_id):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    if not _valid_text(station_id, 50):
        return _error('站點編號不正確。', 400)
    return _write(BACKSTAGE_DELETE_STATION, {'stationId': station_id}, '已刪除資料庫站點。', delete=True)
