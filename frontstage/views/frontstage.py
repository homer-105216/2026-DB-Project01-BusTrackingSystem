from contextlib import closing
from datetime import datetime
from math import isfinite
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, abort, current_app
from psycopg2 import Error, sql
from psycopg2.extras import RealDictCursor

from api import sql as queries
from database.location_replay import TRIP_ID as REPLAY_TRIP_ID
from link import get_connection

# 前台 Blueprint，網址前綴為 /
# 模板放在 frontstage/templates/ 底下，render 時直接寫 'xxx.html'
frontstage_bp = Blueprint('frontstage', __name__, template_folder='../templates')

def fetch_rows(query, params=()):
    with closing(get_connection()) as conn, conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def get_routes():
    return fetch_rows(queries.LIST_ROUTES)


def get_stations(latitude=None, longitude=None, station_ids=None):
    return fetch_rows(queries.LIST_STATIONS, dict(lat=latitude, lng=longitude, ids=station_ids,
              limit=6 if station_ids is None else None))


def member_id():
    return session.get('authenticated_member_id')


def get_user_favorites():
    if member_id() is None:
        return dict(routes=[], stations=[])
    rows = fetch_rows(queries.LIST_MEMBER_FAVORITES, (member_id(), member_id()))
    favorites = dict(routes=[], stations=[])
    for row in rows:
        favorites[row['kind']].append(row['id'])
    return favorites


@frontstage_bp.context_processor
def inject_global_data():
    return dict(current_user=session.get('user'))


@frontstage_bp.route('/')
def index():
    keyword = request.args.get('keyword', '').strip()
    routes = []
    stations = []
    favorites = dict(routes=[], stations=[])
    status = 200
    try:
        routes = get_routes()
        if keyword:
            exact = next((r for r in routes if keyword.casefold() in
                          (r['routeId'].casefold(), r['routeName'].casefold())), None)
            if exact:
                return redirect(url_for('frontstage.route_detail', route_id=exact['routeId']))
            routes = [r for r in routes if any(keyword.casefold() in r[key].casefold()
                      for key in ('routeName', 'origin', 'destination'))]
            if len(routes) == 1:
                return redirect(url_for('frontstage.route_detail', route_id=routes[0]['routeId']))
        stations = get_stations(22.6397, 120.3026)
        favorites = get_user_favorites()
    except (Error, RuntimeError):
        current_app.logger.exception('首頁資料查詢失敗')
        flash('暫時無法讀取公車資料，請稍後再試。', 'danger')
        status = 503
    return render_template(
        'index.html', routes=routes, nearby_stations=stations, keyword=keyword,
        favorite_route_ids=favorites['routes'], favorite_station_ids=favorites['stations'],
        all_kaohsiung_routes=routes,
    ), status


@frontstage_bp.route('/api/nearby')
def nearby():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    if (lat is None or lng is None or not isfinite(lat) or not isfinite(lng)
            or not -90 <= lat <= 90 or not -180 <= lng <= 180):
        return jsonify(success=False, message='定位座標無效'), 400
    try:
        stations = get_stations(lat, lng)
        favorites = get_user_favorites()['stations']
    except (Error, RuntimeError):
        current_app.logger.exception('附近站牌查詢失敗')
        return jsonify(success=False, message='暫時無法讀取附近站牌'), 503
    for station in stations:
        station['favorite'] = station['stationId'] in favorites
    return jsonify(success=True, stations=stations)


@frontstage_bp.route('/route/<route_id>')
def route_detail(route_id):
    direction = int(request.args.get('direction', type=int) == 1)
    direction_str = '回程' if direction else '去程'
    try:
        route_rows = fetch_rows(queries.GET_ROUTE_BY_ID, (route_id,))
        if not route_rows:
            abort(404)
        route = route_rows[0]
        stations = fetch_rows(queries.LIST_ROUTE_STOPS, (route_id, direction_str))
        trips = fetch_rows(queries.LIST_ROUTE_TRIPS, (route_id, direction_str))
        buses = fetch_rows(queries.LIST_ROUTE_LIVE_BUSES, (route_id, direction_str, REPLAY_TRIP_ID))
        routes = get_routes()
        favorites = get_user_favorites()
    except (Error, RuntimeError):
        current_app.logger.exception('路線詳情查詢失敗')
        abort(503)

    return render_template(
        'route_detail.html', route=route, route_id=route_id, direction=direction,
        stations=stations, buses=buses, trips=trips, all_kaohsiung_routes=routes,
        is_fav_route=route_id in favorites['routes'], favorite_station_ids=favorites['stations'],
    )


@frontstage_bp.route('/api/bus/live/<route_id>')
def api_route_live(route_id):
    direction = int(request.args.get('direction', type=int) == 1)
    direction_str = '回程' if direction else '去程'
    try:
        buses = fetch_rows(queries.LIST_ROUTE_LIVE_BUSES, (route_id, direction_str, REPLAY_TRIP_ID))
        return jsonify(success=True, buses=buses)
    except (Error, RuntimeError):
        current_app.logger.exception('即時公車動態查詢失敗')
        return jsonify(success=False, message='暫時無法讀取公車動態', buses=[]), 503


@frontstage_bp.route('/favorites')
def favorites():
    mid = member_id()
    if mid is None:
        flash('查看或管理我的收藏清單前，請先登入帳號。', 'warning')
        return redirect(url_for('frontstage.login', next=url_for('frontstage.favorites')))
    try:
        fav_routes = fetch_rows(queries.LIST_MEMBER_FAVORITE_ROUTES, (mid,))
        fav_stations = fetch_rows(queries.LIST_MEMBER_FAVORITE_STATIONS, (mid,))
        all_routes = get_routes()
    except (Error, RuntimeError):
        current_app.logger.exception('收藏清單載入失敗')
        flash('暫時無法讀取收藏清單，請稍後再試。', 'danger')
        fav_routes, fav_stations, all_routes = [], [], []

    return render_template(
        'favorites.html', all_kaohsiung_routes=all_routes,
        fav_routes=fav_routes,
        fav_stations=fav_stations,
    )


@frontstage_bp.route('/api/favorite/<fav_type>/<fav_id>', methods=['POST'])
def api_toggle_favorite(fav_type, fav_id):
    mid = member_id()
    if mid is None:
        return jsonify(success=False, require_login=True, message='請先登入帳號後再進行收藏操作！'), 401
    targets = {'route': ('Favorite_Route', 'routeId'), 'station': ('Favorite_Station', 'stationId')}
    if fav_type not in targets:
        return jsonify(success=False, message='無效的收藏類型'), 400
    table, column = map(sql.Identifier, targets[fav_type])
    try:
        with closing(get_connection()) as conn, conn, conn.cursor() as cur:
            cur.execute(queries.LOCK_MEMBER, (mid,))
            if cur.fetchone() is None:
                session.clear()
                return jsonify(success=False, require_login=True, message='請重新登入'), 401
            cur.execute(sql.SQL(queries.DELETE_FAVORITE).format(
                table, column), (mid, fav_id))
            removed = cur.rowcount > 0
            if not removed:
                cur.execute(sql.SQL(queries.INSERT_FAVORITE).format(
                    table, column), (mid, fav_id))
            cur.execute(sql.SQL(queries.COUNT_FAVORITES).format(table), (mid,))
            count = cur.fetchone()[0]
    except Error as exc:
        if exc.pgcode == '23503':
            return jsonify(success=False, message='找不到指定的路線或站牌'), 404
        current_app.logger.exception('收藏更新失敗')
        return jsonify(success=False, message='暫時無法更新收藏'), 503
    except RuntimeError:
        current_app.logger.exception('收藏連線失敗')
        return jsonify(success=False, message='暫時無法更新收藏'), 503
    return jsonify(success=True, action='removed' if removed else 'added',
                   message='已取消收藏' if removed else '已加入收藏',
                   fav_type=fav_type, fav_id=fav_id, total_count=count)


@frontstage_bp.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next') or ''
    if not next_url.startswith('/') or next_url.startswith('//') or chr(92) in next_url or any(ord(c) < 32 for c in next_url):
        next_url = url_for('frontstage.index')

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        if not identifier or not password:
            flash('請輸入帳號與密碼。', 'danger')
            return render_template('login.html', next=next_url)

        try:
            rows = fetch_rows(queries.VERIFY_MEMBER, (identifier, identifier, password))
        except (Error, RuntimeError):
            current_app.logger.exception('會員登入查詢失敗')
            flash('暫時無法連線至會員資料庫，請稍後再試。', 'danger')
            return render_template('login.html', next=next_url), 503
        if len(rows) != 1:
            flash('帳號或密碼不正確。若有同名會員，請改用 Email。', 'danger')
            return render_template('login.html', next=next_url)

        user = dict(rows[0])
        session.clear()
        session['user'] = user
        session['authenticated_member_id'] = user['mId']
        flash(f'登入成功！歡迎回來，{user["userName"]}。', 'success')
        return redirect(next_url)

    return render_template('login.html', next=next_url)


@frontstage_bp.route('/register', methods=['GET', 'POST'])
def register():
    """新會員註冊處理"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or len(username) < 3 or len(username) > 20:
            flash('使用者名稱長度需介於 3 至 20 個字元！', 'danger')
            return render_template('register.html')

        if not email or '@' not in email:
            flash('請輸入正確的電子郵件格式！', 'danger')
            return render_template('register.html')

        if not password or len(password) < 8:
            flash('密碼長度需至少 8 個字元！', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('兩次輸入的密碼不一致！', 'danger')
            return render_template('register.html')

        try:
            existing = fetch_rows(queries.CHECK_MEMBER_EXISTS, (email, username))
            if existing:
                flash('該使用者名稱或電子郵件已被註冊，請更換後再試！', 'danger')
                return render_template('register.html')

            new_members = fetch_rows(queries.REGISTER_MEMBER, (username, email, password))
            if not new_members:
                flash('註冊失敗，請稍後再試。', 'danger')
                return render_template('register.html')
            user = dict(new_members[0])
        except Error as exc:
            current_app.logger.exception('註冊寫入資料庫失敗: %s', exc)
            flash('註冊失敗，資料庫發生錯誤，請稍後再試。', 'danger')
            return render_template('register.html'), 503
        except RuntimeError:
            current_app.logger.exception('註冊連線失敗')
            flash('暫時無法連線至會員資料庫，請稍後再試。', 'danger')
            return render_template('register.html'), 503

        session.clear()
        session['user'] = user
        session['authenticated_member_id'] = user['mId']

        flash('註冊成功！已自動登入，歡迎加入高雄公車動態追蹤系統。', 'success')
        return redirect(url_for('frontstage.index'))

    return render_template('register.html')


@frontstage_bp.route('/logout')
def logout():
    """會員登出"""
    session.clear()
    flash('您已成功登出系統。', 'info')
    return redirect(url_for('frontstage.index'))


@frontstage_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """會員帳號設定維護"""
    mid = member_id()
    if mid is None:
        flash('請先登入帳號以管理個人資料。', 'warning')
        return redirect(url_for('frontstage.login', next=url_for('frontstage.profile')))

    try:
        member_rows = fetch_rows(queries.GET_MEMBER_BY_ID, (mid,))
        if not member_rows:
            session.clear()
            flash('會員資料不存在，請重新登入。', 'warning')
            return redirect(url_for('frontstage.login'))
        user = dict(member_rows[0])
    except (Error, RuntimeError):
        current_app.logger.exception('讀取個人資料失敗')
        flash('暫時無法讀取會員資料，請稍後再試。', 'danger')
        return render_template('profile.html', member=session.get('user')), 503

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '').strip()
        confirm_new_password = request.form.get('confirm_new_password', '').strip()

        if not username or len(username) < 3 or len(username) > 20:
            flash('使用者名稱長度需介於 3 至 20 個字元！', 'danger')
            return render_template('profile.html', member=user)

        if not email or '@' not in email:
            flash('請輸入正確的電子郵件格式！', 'danger')
            return render_template('profile.html', member=user)

        try:
            conflict = fetch_rows(queries.CHECK_MEMBER_CONFLICT, (email, username, mid))
            if conflict:
                flash('該使用者名稱或電子郵件已被其他會員使用！', 'danger')
                return render_template('profile.html', member=user)

            if new_password:
                if not current_password:
                    flash('欲變更密碼時，請輸入目前密碼以供驗證！', 'danger')
                    return render_template('profile.html', member=user)
                if len(new_password) < 8:
                    flash('新密碼長度至少需 8 個字元！', 'danger')
                    return render_template('profile.html', member=user)
                if new_password != confirm_new_password:
                    flash('兩次輸入的新密碼不相符！', 'danger')
                    return render_template('profile.html', member=user)

                pwd_check = fetch_rows(queries.VERIFY_MEMBER_PASSWORD, (mid, current_password))
                if not pwd_check:
                    flash('目前密碼輸入錯誤，無法更新！', 'danger')
                    return render_template('profile.html', member=user)

                updated = fetch_rows(queries.UPDATE_MEMBER_PROFILE_WITH_PASSWORD, (username, email, new_password, mid))
                flash('個人資料與登入密碼已成功更新！', 'success')
            else:
                updated = fetch_rows(queries.UPDATE_MEMBER_PROFILE, (username, email, mid))
                flash('個人基本資料已成功更新！', 'success')

            if updated:
                user = dict(updated[0])
                session['user'] = user

        except (Error, RuntimeError) as exc:
            current_app.logger.exception('更新會員資料失敗: %s', exc)
            flash('更新失敗，資料庫發生錯誤，請稍後再試。', 'danger')
            return render_template('profile.html', member=user), 503

    try:
        route_count_row = fetch_rows(queries.COUNT_MEMBER_FAVORITE_ROUTES, (mid,))
        station_count_row = fetch_rows(queries.COUNT_MEMBER_FAVORITE_STATIONS, (mid,))
        fav_routes_count = route_count_row[0]['count'] if route_count_row else 0
        fav_stations_count = station_count_row[0]['count'] if station_count_row else 0
    except (Error, RuntimeError):
        fav_routes_count, fav_stations_count = 0, 0

    return render_template(
        'profile.html',
        member=user,
        fav_routes_count=fav_routes_count,
        fav_stations_count=fav_stations_count
    )
