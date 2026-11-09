"""營運總覽；使用同一唯讀快照查詢真實總數與路線班次。"""
from flask import current_app
from psycopg2.extras import RealDictCursor
from link import get_connection
from .stations import _response, _error
from .sql import BACKSTAGE_OVERVIEW_COUNTS, BACKSTAGE_ROUTE_TRIP_COMPARISON


def operation_overview():
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(BACKSTAGE_OVERVIEW_COUNTS)
            summary = dict(cur.fetchone())
            cur.execute(BACKSTAGE_ROUTE_TRIP_COMPARISON)
            rows = [dict(row) for row in cur.fetchall()]
        return _response({'status': 'ok', 'summary': summary, 'routeTrips': rows})
    except Exception:
        current_app.logger.warning('Operation overview query failed.')
        return _error('無法讀取營運總覽，請確認資料庫連線後重新載入。', 503)
    finally:
        if conn is not None:
            conn.close()
