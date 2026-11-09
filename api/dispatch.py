"""每日派車與司機安排。精確日期查詢；SQL 統一置於 api/sql.py。"""
import re
from datetime import date
import psycopg2
from flask import current_app, request
from psycopg2.extras import RealDictCursor
from link import get_connection
from .stations import _response, _error, _csrf_token, _valid_csrf, _rollback, _valid_text
from . import sql

# 依現有 Daily_Trip_Implement.status CHECK；不擅自擴充 schema。
DISPATCH_STATUSES = ('已完成', '延誤抵達')


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _record(row):
    return {k: v.isoformat() if isinstance(v, date) else v for k, v in dict(row).items()}


def list_dispatches():
    day = request.args.get('date', '')
    parsed = _date(day) if day else None
    keyword = request.args.get('keyword', '').strip()
    if (day and parsed is None) or len(keyword) > 200:
        return _error('請提供 YYYY-MM-DD 日期，搜尋字數不得超過 200。', 400)
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql.BACKSTAGE_LIST_DISPATCHES, {'date': parsed, 'keyword': keyword or None})
            rows = [_record(row) for row in cur.fetchall()]
        return _response({'status': 'ok', 'dispatches': rows, 'count': len(rows), 'csrfToken': _csrf_token()})
    except Exception:
        current_app.logger.warning('Dispatch list query failed.')
        return _error('無法讀取每日派車，請確認資料庫連線後重試。', 503)
    finally:
        if conn is not None:
            conn.close()


def dispatch_options():
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql.LIST_ROUTES)
            routes = [dict(row) for row in cur.fetchall()]
            cur.execute(sql.BACKSTAGE_LIST_TRIPS, {'routeId': None, 'tDirection': None, 'keyword': None})
            trips = [dict(row) for row in cur.fetchall()]
            cur.execute(sql.BACKSTAGE_LIST_BUSES, {'keyword': None})
            buses = [dict(row) for row in cur.fetchall()]
        return _response({'status': 'ok', 'routes': routes, 'trips': trips, 'buses': buses,
                          'statuses': list(DISPATCH_STATUSES), 'csrfToken': _csrf_token()})
    except Exception:
        current_app.logger.warning('Dispatch options query failed.')
        return _error('無法讀取班次與車輛選單，請重新載入。', 503)
    finally:
        if conn is not None:
            conn.close()


def _payload(trip_id=None, dispatch_date=None):
    p = request.get_json(silent=True)
    if not isinstance(p, dict):
        return None
    required = {'bId', 'driver', 'status'}
    if trip_id is None:
        required.update(('tId', 'date'))
        trip_id, dispatch_date = p.get('tId'), p.get('date')
    else:
        for key, value in (('tId', trip_id), ('date', dispatch_date)):
            if key in p:
                required.add(key)
                if p[key] != value:
                    return None
    if set(p) != required or not _valid_text(trip_id, 50) or _date(dispatch_date) is None:
        return None
    if not _valid_text(p.get('bId'), 50) or not _valid_text(p.get('driver'), 100) or p.get('status') not in DISPATCH_STATUSES:
        return None
    return {'tId': trip_id, 'date': _date(dispatch_date), 'bId': p['bId'],
            'driver': p['driver'].strip(), 'status': p['status']}


def _write(statement, params, mode):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 與 Trip 編輯採相同鎖順序，避免班次引用檢查與新增派車競態。
            cur.execute(sql.BACKSTAGE_LOCK_TRIPS)
            if mode != 'create':
                cur.execute(sql.BACKSTAGE_GET_DISPATCH, {'tId': params['tId'], 'date': params['date']})
                if cur.fetchone() is None:
                    _rollback(conn)
                    return _error('此日期的派車安排已不存在，請重新載入。', 404)
            cur.execute(statement, params)
            row = cur.fetchone()
            if row is None:
                _rollback(conn)
                return _error('此派車安排已不存在，請重新載入。', 404)
            record = _record(row)
        conn.commit()
        message = {'create': '已新增資料庫派車安排。', 'update': '已更新資料庫派車安排。', 'delete': '已刪除資料庫派車安排。'}[mode]
        return _response({'status': 'ok', 'dispatch': record, 'message': message}, 201 if mode == 'create' else 200)
    except psycopg2.IntegrityError as error:
        _rollback(conn)
        if error.pgcode == '23505':
            return _error('同一班次在同一天已有派車安排，請編輯原紀錄或選擇其他班次／日期。', 409)
        if error.pgcode == '23503':
            return _error('此派車已有位置紀錄，無法刪除；位置紀錄會保留。' if mode == 'delete' else '班次或車輛已不存在，請重新載入選單。', 409)
        return _error('派車資料不符合資料庫限制，請確認司機、日期與合法狀態。', 400)
    except Exception:
        _rollback(conn)
        current_app.logger.warning('Dispatch write failed.')
        return _error('資料庫操作失敗，請重新載入確認資料是否已更新。', 503)
    finally:
        if conn is not None:
            conn.close()


def create_dispatch():
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面。', 403)
    p = _payload()
    if p is None:
        return _error('請填寫班次、有效日期、車輛、1 至 100 字司機姓名，以及已完成／延誤抵達狀態。', 400)
    return _write(sql.BACKSTAGE_INSERT_DISPATCH, p, 'create')


def update_dispatch(trip_id, dispatch_date):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面。', 403)
    p = _payload(trip_id, dispatch_date)
    if p is None:
        return _error('請提供有效派車資料；編輯時班次與日期不可變更，狀態僅允許已完成／延誤抵達。', 400)
    return _write(sql.BACKSTAGE_UPDATE_DISPATCH, p, 'update')


def delete_dispatch(trip_id, dispatch_date):
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面。', 403)
    if not _valid_text(trip_id, 50) or _date(dispatch_date) is None:
        return _error('班次編號或日期不正確。', 400)
    return _write(sql.BACKSTAGE_DELETE_DISPATCH, {'tId': trip_id, 'date': _date(dispatch_date)}, 'delete')
