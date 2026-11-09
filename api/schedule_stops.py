"""路線站序／班次各站時間 API；SQL 一律定義於 api/sql.py。"""
from datetime import datetime
import psycopg2
from flask import current_app, request
from psycopg2.extras import RealDictCursor
from link import get_connection
from .stations import _response, _error, _csrf_token, _valid_csrf, _rollback, _valid_text
from . import sql


def _direction(value):
    return '回程' if value == '返程' else value if value in ('去程', '回程') else None


def _rows(cur):
    # timestamp without time zone：保留完整本地日期時間，不任意附加 UTC 或日期。
    return [{k: v.isoformat(timespec='seconds') if isinstance(v, datetime) else v
             for k, v in dict(row).items()} for row in cur.fetchall()]


def _select(cur, statement, params=None):
    cur.execute(statement, params)
    return _rows(cur)


def stop_options():
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            routes = _select(cur, sql.LIST_ROUTES)
            stations = _select(cur, sql.BACKSTAGE_LIST_STATIONS, {'keyword': None})
        return _response({'status': 'ok', 'routes': routes, 'stations': stations, 'csrfToken': _csrf_token()})
    except Exception:
        current_app.logger.warning('Schedule options query failed.')
        return _error('無法讀取路線與站點選單，請重新載入。', 503)
    finally:
        if conn is not None:
            conn.close()


def route_stops():
    route_id = request.args.get('routeId')
    direction = _direction(request.args.get('rDirection'))
    trip_id = request.args.get('tId')
    if not _valid_text(route_id, 50) or direction is None or (trip_id is not None and not _valid_text(trip_id, 50)):
        return _error('請提供有效路線、去／返程與班次編號。', 400)
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            routes = _select(cur, sql.BACKSTAGE_GET_ROUTE, {'routeId': route_id})
            if not routes:
                return _error('路線已不存在，請重新載入路線清單。', 404)
            stops = _select(cur, sql.BACKSTAGE_LIST_ROUTE_STOPS, {'routeId': route_id, 'rDirection': direction})
            trips = _select(cur, sql.BACKSTAGE_LIST_TRIPS, {'routeId': route_id, 'tDirection': direction, 'keyword': None})
            if trip_id is not None and not any(t['tId'] == trip_id for t in trips):
                return _error('班次不屬於目前路線與方向，請重新選擇。', 400)
            selected = trip_id if trip_id is not None else trips[0]['tId'] if trips else None
            times = _select(cur, sql.BACKSTAGE_LIST_TRIP_STOP_TIMES, {'tId': selected}) if selected else []
        return _response({'status': 'ok', 'route': routes[0], 'direction': direction,
                          'stops': stops, 'trips': trips, 'selectedTripId': selected, 'times': times})
    except Exception:
        current_app.logger.warning('Schedule stops query failed.')
        return _error('無法讀取站序與班次時間，請確認資料庫連線後重試。', 503)
    finally:
        if conn is not None:
            conn.close()


def _stop_payload(mode):
    p = request.get_json(silent=True)
    required = {'routeId', 'stationId', 'rDirection'}
    if mode != 'delete':
        required.add('stopSequence')
    if mode == 'update':
        required.update(('old_stationId', 'old_rDirection'))
    if not isinstance(p, dict) or set(p) != required:
        return None
    if not all(_valid_text(p.get(k), 50) for k in ('routeId', 'stationId')):
        return None
    p = dict(p)
    p['rDirection'] = _direction(p['rDirection'])
    if p['rDirection'] is None:
        return None
    if mode != 'delete' and (type(p['stopSequence']) is not int or not 0 < p['stopSequence'] <= 2147483647):
        return None
    if mode == 'update':
        p['old_rDirection'] = _direction(p['old_rDirection'])
        if not _valid_text(p['old_stationId'], 50) or p['old_rDirection'] is None:
            return None
    return p


def _write(statement, params, kind, message, mode=None, status=200):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Contain/Trip/Run 共同鎖，防止並行站序變更與 Run 寫入產生孤立時間。
            cur.execute(sql.BACKSTAGE_LOCK_SCHEDULE)
            if kind == 'stop' and mode != 'create':
                old = {'routeId': params['routeId'],
                       'stationId': params.get('old_stationId', params['stationId']),
                       'rDirection': params.get('old_rDirection', params['rDirection'])}
                cur.execute(sql.BACKSTAGE_GET_ROUTE_STOP, old)
                if cur.fetchone() is None:
                    _rollback(conn)
                    return _error('此停靠站設定已不存在，請重新載入。', 404)
            if kind == 'time':
                times = _select(cur, sql.BACKSTAGE_LIST_TRIP_STOP_TIMES, {'tId': params['tId']})
                if not any(t['stationId'] == params['stationId'] for t in times):
                    _rollback(conn)
                    return _error('站點不屬於此班次的路線與方向，請重新選擇。', 409)
            cur.execute(statement, params)
            row = cur.fetchone()
            if row is None:
                _rollback(conn)
                if kind == 'stop':
                    return _error('本站已有對應班次的到離站時間，請先清除相關時間再換站、換方向或刪除。', 409)
                return _error('此時間設定已不存在，請重新載入。', 404)
            record = {k: v.isoformat(timespec='seconds') if isinstance(v, datetime) else v for k, v in dict(row).items()}
        conn.commit()
        return _response({'status': 'ok', kind: record, 'message': message}, status)
    except psycopg2.IntegrityError as error:
        _rollback(conn)
        if error.pgcode == '23505':
            return _error('同一路線、同方向的站序或站點不可重複，請改用未使用的站序／站點。', 409)
        if error.pgcode == '23503':
            return _error('路線、站點或班次已不存在，或資料仍被引用，請重新載入。', 409)
        return _error('資料不符合資料庫限制，請確認站序與到離站時間。', 400)
    except Exception:
        _rollback(conn)
        current_app.logger.warning('Schedule stop/time update failed.')
        return _error('資料庫操作失敗，請重新載入確認資料是否已更新。', 503)
    finally:
        if conn is not None:
            conn.close()


def _stop_write(mode):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面。', 403)
    params = _stop_payload(mode)
    if params is None:
        return _error('請提供路線、站點、有效方向及正整數站序；編輯時須提供原站點與方向。', 400)
    statement = {'create': sql.BACKSTAGE_INSERT_ROUTE_STOP, 'update': sql.BACKSTAGE_UPDATE_ROUTE_STOP,
                 'delete': sql.BACKSTAGE_DELETE_ROUTE_STOP}[mode]
    return _write(statement, params, 'stop', '已更新資料庫停靠站設定。', mode, 201 if mode == 'create' else 200)


def create_route_stop():
    return _stop_write('create')


def update_route_stop():
    return _stop_write('update')


def delete_route_stop():
    return _stop_write('delete')


def _time_write(delete=False):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面。', 403)
    p = request.get_json(silent=True)
    required = {'tId', 'stationId'} | (set() if delete else {'expArrivalTime', 'expDepartureTime'})
    if not isinstance(p, dict) or set(p) != required or not all(_valid_text(p.get(k), 50) for k in ('tId', 'stationId')):
        return _error('請提供有效班次與站點，並填寫完整到離站日期時間。', 400)
    p = dict(p)
    if not delete:
        try:
            for key in ('expArrivalTime', 'expDepartureTime'):
                value = p[key]
                if not isinstance(value, str) or 'T' not in value or len(value) > 32:
                    raise ValueError()
                p[key] = datetime.fromisoformat(value)
                if p[key].tzinfo is not None:
                    raise ValueError()
            if p['expDepartureTime'] < p['expArrivalTime']:
                raise ValueError()
        except (ValueError, TypeError):
            return _error('請填寫完整本地日期時間，離站不得早於到站；跨日班次請填寫正確的隔日日期。', 400)
    return _write(sql.BACKSTAGE_DELETE_TRIP_STOP_TIME if delete else sql.BACKSTAGE_UPSERT_TRIP_STOP_TIME,
                  p, 'time', '已清除本站的班次時間，保留站序。' if delete else '已儲存本站的班次日期時間。')


def save_stop_time():
    return _time_write()


def delete_stop_time():
    return _time_write(delete=True)
