"""營運統計：同一唯讀快照，成長、班次、收藏各自維持統計範圍。"""
import re
from datetime import date, datetime, timedelta, timezone
from flask import current_app, request
from psycopg2.extras import RealDictCursor
from link import get_connection
from .stations import _response, _error
from . import sql


def _today_taipei():
    # 現行台北時間 UTC+8，Windows 不需額外安裝 tzdata。
    return datetime.now(timezone(timedelta(hours=8), 'Asia/Taipei')).date()


def _parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError()
    return date.fromisoformat(value)


def _period():
    start, end = request.args.get('startDate'), request.args.get('endDate')
    if start is not None or end is not None:
        if 'days' in request.args:
            raise ValueError()
        start, end = _parse_date(start), _parse_date(end)
        days = (end - start).days + 1
        if not 1 <= days <= 90:
            raise ValueError()
    else:
        value = request.args.get('days', '30')
        if value not in ('7', '30', '90'):
            raise ValueError()
        days = int(value)
        end = _today_taipei()
        start = end - timedelta(days=days - 1)
    return start, end, days


def operation_analysis():
    """GET /api/schedule/analysis?days=7|30|90&limit=5|10|all&order=least|most|id。

    亦可用 startDate+endDate 代替 days（含首尾、最多 90 天）。日期僅影響會員成長；
    收藏固定 onlyUsers=False，明示全體有效會員，包含管理者。所有 SQL 在 api/sql.py。
    """
    try:
        start, end, days = _period()
    except (ValueError, OverflowError, TypeError):
        return _error('請選近 7／30／90 天，或提供有效的起訖日期（最多 90 天，含首尾日）。', 400)
    raw_limit = request.args.get('limit', '5')
    order = request.args.get('order', 'least')
    if raw_limit not in ('5', '10', 'all') or order not in ('least', 'most', 'id'):
        return _error('排行僅接受 5／10／all；班次排序僅接受 least／most／id。', 400)
    limit = None if raw_limit == 'all' else int(raw_limit)
    conn = None
    try:
        conn = get_connection()
        # 同一統計回應使用一致快照，避免查詢中途註冊／刪除造成總數與每日圖不一致。
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql.BACKSTAGE_USER_COUNT)
            user_count = cur.fetchone()['userCount']
            params = {'startDate': start, 'endDate': end}
            cur.execute(sql.BACKSTAGE_NEW_USER_COUNT, params)
            new_count = cur.fetchone()['newUserCount']
            cur.execute(sql.BACKSTAGE_DAILY_NEW_USERS, params)
            daily = [{'registrationDate': row['registrationDate'].isoformat(), 'newUserCount': row['newUserCount']}
                     for row in cur.fetchall()]
            cur.execute(sql.BACKSTAGE_ROUTE_TRIP_COMPARISON)
            comparison = [dict(row) for row in cur.fetchall()]
            if any(row['totalCount'] != row['outboundCount'] + row['inboundCount'] for row in comparison):
                raise ValueError('Unexpected trip direction; do not silently drop it')
            favorites_params = {'limit': limit, 'onlyUsers': False}
            cur.execute(sql.BACKSTAGE_POPULAR_ROUTES, favorites_params)
            routes = [dict(row) for row in cur.fetchall()]
            cur.execute(sql.BACKSTAGE_POPULAR_STATIONS, favorites_params)
            stations = [dict(row) for row in cur.fetchall()]
        comparison.sort(key=lambda r: ((-r['totalCount'] if order == 'most' else r['totalCount'] if order == 'least' else 0), r['routeId']))
        return _response({'status': 'ok', 'timezone': 'Asia/Taipei',
                          'userGrowth': {'userCount': user_count, 'newUserCount': new_count, 'days': days,
                                         'startDate': start.isoformat(), 'endDate': end.isoformat(), 'daily': daily},
                          'tripComparison': comparison,
                          'favorites': {'scope': 'all-valid-members', 'limit': limit, 'routes': routes, 'stations': stations}})
    except Exception:
        current_app.logger.warning('Operation analysis query failed.')
        return _error('無法讀取營運統計，請確認資料庫連線與資料定義後重新載入。', 503)
    finally:
        if conn is not None:
            conn.close()
