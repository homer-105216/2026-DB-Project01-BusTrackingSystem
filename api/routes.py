"""路線查詢 API；SQL 統一引用資料庫組的 api/sql.py。"""

from flask import current_app, jsonify, request
from psycopg2.extras import RealDictCursor

from link import get_connection
from .sql import LIST_ROUTES


def list_routes():
    """GET /api/routes，可選填 keyword；僅查詢、不異動資料。"""
    keyword = request.args.get('keyword', '').strip().casefold()
    if len(keyword) > 200:
        return jsonify(status='error', message='搜尋關鍵字不得超過 200 字元。'), 400
    try:
        conn = get_connection()
        try:
            conn.set_session(readonly=True, autocommit=True)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(LIST_ROUTES)
                rows = [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
    except Exception:
        current_app.logger.warning('Route list database query failed.')
        return jsonify(status='error', message='無法讀取路線資料，請確認資料庫連線及 Route 資料表後重試。'), 503

    # 共用 LIST_ROUTES 無搜尋參數；先以回傳資料篩選，不另外撰寫 SQL。
    if keyword:
        rows = [row for row in rows if any(keyword in str(row.get(key) or '').casefold()
                for key in ('routeId', 'routeName', 'origin', 'destination'))]
    response = jsonify(status='ok', routes=rows, count=len(rows))
    response.headers['Cache-Control'] = 'no-store'
    return response
