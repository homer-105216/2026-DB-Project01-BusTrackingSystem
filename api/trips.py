"""固定 Trip 管理；不混用前台的最近一次派車查詢。SQL 集中於 api/sql.py。"""
import re
from datetime import time
import psycopg2
from flask import current_app, request
from psycopg2.extras import RealDictCursor
from link import get_connection
from .stations import _response, _error, _csrf_token, _valid_csrf, _rollback, _valid_text
from .schedule_stops import _direction
from . import sql


def list_trips():
    route_id = request.args.get('routeId')
    direction = request.args.get('tDirection')
    keyword = request.args.get('keyword', '').strip()
    if (route_id is not None and not _valid_text(route_id, 50)) or len(keyword) > 200:
        return _error('路線編號或搜尋關鍵字不正確。', 400)
    if direction is not None:
        direction = _direction(direction)
        if direction is None:
            return _error('請選擇有效的去／返程。', 400)
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            route = None
            if route_id is not None:
                cur.execute(sql.BACKSTAGE_GET_ROUTE, {'routeId': route_id})
                record = cur.fetchone()
                if record is None:
                    return _error('此路線已不存在，請重新載入路線清單。', 404)
                route = dict(record)
            cur.execute(sql.BACKSTAGE_LIST_TRIPS, {'routeId': route_id, 'tDirection': direction, 'keyword': keyword or None})
            rows = [dict(row) for row in cur.fetchall()]
        return _response({'status': 'ok', 'trips': rows, 'route': route, 'count': len(rows), 'csrfToken': _csrf_token()})
    except Exception:
        current_app.logger.warning('Scheduled trip query failed.')
        return _error('無法讀取預定班次，請確認資料庫連線後重試。', 503)
    finally:
        if conn is not None:
            conn.close()


def _payload(trip_id=None):
    p = request.get_json(silent=True)
    if not isinstance(p, dict):
        return None
    required = {'routeId', 'departureTime', 'tDirection'}
    if trip_id is None:
        required.add('tId')
        trip_id = p.get('tId')
    elif 'tId' in p:
        required.add('tId')
        if p['tId'] != trip_id:
            return None
    if set(p) != required or not _valid_text(trip_id, 50) or not _valid_text(p.get('routeId'), 50):
        return None
    direction = _direction(p.get('tDirection'))
    value = p.get('departureTime')
    if direction is None or not isinstance(value, str) or not re.fullmatch(r'\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?', value):
        return None
    try:
        parsed = time.fromisoformat(value)
    except ValueError:
        return None
    return {'tId': trip_id, 'routeId': p['routeId'], 'departureTime': parsed.isoformat(), 'tDirection': direction}


def _write(statement, params, mode):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql.BACKSTAGE_LOCK_TRIPS)
            if mode != 'create':
                cur.execute(sql.BACKSTAGE_GET_TRIP, {'tId': params['tId']})
                if cur.fetchone() is None:
                    _rollback(conn)
                    return _error('此班次已不存在，請重新載入。', 404)
            cur.execute(statement, params)
            row = cur.fetchone()
            if row is None:
                _rollback(conn)
                return _error('此班次已有各站到離站時間或每日派車，無法修改班表；請先處理相關資料。', 409)
            record = dict(row)
        conn.commit()
        message = {'create': '已新增資料庫預定班次。', 'update': '已更新資料庫預定班次。', 'delete': '已刪除資料庫預定班次。'}[mode]
        return _response({'status': 'ok', 'trip': record, 'message': message}, 201 if mode == 'create' else 200)
    except psycopg2.IntegrityError as error:
        _rollback(conn)
        if error.pgcode == '23505':
            return _error('班次編號已存在，請使用不同編號。', 409)
        if error.pgcode == '23503':
            return _error('路線已不存在，或班次仍被各站時間／每日派車引用，請重新載入並確認。', 409)
        return _error('班次資料不符合資料庫限制，請確認編號、時間及方向。', 400)
    except Exception:
        _rollback(conn)
        current_app.logger.warning('Scheduled trip write failed.')
        return _error('資料庫操作失敗，請重新載入確認資料是否已更新。', 503)
    finally:
        if conn is not None:
            conn.close()


def create_trip():
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面。', 403)
    params = _payload()
    if params is None:
        return _error('請填寫班次編號、路線、有效發車時間及方向。', 400)
    return _write(sql.BACKSTAGE_INSERT_TRIP, params, 'create')


def update_trip(trip_id):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面。', 403)
    params = _payload(trip_id)
    if params is None:
        return _error('請填寫有效班次資料；編輯時不可變更班次編號。', 400)
    return _write(sql.BACKSTAGE_UPDATE_TRIP, params, 'update')


def delete_trip(trip_id):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面。', 403)
    if not _valid_text(trip_id, 50):
        return _error('班次編號不正確。', 400)
    return _write(sql.BACKSTAGE_DELETE_TRIP, {'tId': trip_id}, 'delete')
