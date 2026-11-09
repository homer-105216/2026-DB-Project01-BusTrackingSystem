from flask import Blueprint, abort, redirect, render_template, request, url_for, session, g
from api.admin_auth import (AdminDatabaseUnavailable, current_admin, authenticate_admin,
                            clear_admin_session, login_csrf_token, api_csrf_token,
                            valid_token, safe_next, begin_admin_session)


backstage_bp = Blueprint('backstage', __name__, template_folder='../templates')

PAGE_TEMPLATES = {
    'overview': 'index',
    'members': 'members',
    'routes': 'routes',
    'stations': 'stations',
    'stops': 'stops',
    'bus-types': 'bus_types',
    'buses': 'buses',
    'trips': 'trips',
    'dispatch': 'dispatch',
    'stop-times': 'stop_times',
    'analysis': 'analysis',
}


def _login_page(message=None, status=200, identifier='', next_path=None):
    return render_template('backstage/login.html', error_message=message, identifier=identifier,
                           login_csrf=login_csrf_token(), next_path=safe_next(next_path)), status


@backstage_bp.before_request
def require_admin():
    if request.endpoint in ('backstage.login', 'backstage.logout'):
        return None
    try:
        admin = current_admin()
    except AdminDatabaseUnavailable:
        return _login_page('暫時無法確認管理者權限，請確認資料庫連線後重試。', 503,
                           next_path=request.full_path)
    if admin is None:
        return redirect(url_for('backstage.login', next=safe_next(request.full_path)))


@backstage_bp.context_processor
def inject_admin_account():
    # guard 已在同一請求確認權限，current_admin 使用 g 快取，不重複查詢。
    if request.endpoint in ('backstage.login', 'backstage.logout'):
        return {}
    admin = getattr(g, 'backstage_admin', None)
    return {'backstage_admin': admin, 'backstage_csrf': api_csrf_token() if admin else None}


@backstage_bp.after_request
def prevent_admin_page_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@backstage_bp.route('/login', methods=['GET', 'POST'])
def login():
    target = safe_next(request.form.get('next') if request.method == 'POST' else request.args.get('next'))
    if request.method == 'GET':
        try:
            if current_admin() is not None:
                return redirect(target)
        except AdminDatabaseUnavailable:
            return _login_page('暫時無法連線至會員資料庫，請稍後重試。', 503, next_path=target)
        return _login_page(next_path=target)
    identifier = request.form.get('identifier', '').strip()
    password = request.form.get('password', '')
    if not valid_token(session.get('backstage_login_csrf'), request.form.get('csrf_token', '')):
        return _login_page('登入表單已失效，請重新載入後再試。', 403, identifier, target)
    if not identifier or len(identifier) > 100 or '\x00' in identifier or not password or len(password) > 255 or '\x00' in password:
        return _login_page('請填寫有效的使用者名稱或 Email 與密碼。', 400, identifier, target)
    clear_admin_session()
    try:
        admin = authenticate_admin(identifier, password)
    except AdminDatabaseUnavailable:
        return _login_page('暫時無法連線至會員資料庫，請稍後重試。', 503, identifier, target)
    if admin is None:
        return _login_page('帳號、密碼不正確，或此帳號沒有管理者權限。', 403, identifier, target)
    begin_admin_session(admin['mId'])
    return redirect(target)


@backstage_bp.route('/logout', methods=['POST'])
def logout():
    if not valid_token(session.get('backstage_api_csrf'), request.form.get('csrf_token', '')):
        abort(403)
    clear_admin_session()
    session.pop('backstage_login_csrf', None)
    return redirect(url_for('backstage.login'))


@backstage_bp.route('/')
def index():
    return render_template('backstage/index.html', page='overview')


@backstage_bp.route('/<page>')
def console(page):
    if page == 'stop-times':
        return redirect(url_for('backstage.console', page='stops'))
    if page not in PAGE_TEMPLATES or page == 'overview':
        abort(404)
    return render_template(f'backstage/{PAGE_TEMPLATES[page]}.html', page=page)
