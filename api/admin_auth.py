"""後台驗證共用邏輯；只保存會員編號，權限每次重新向資料庫確認。"""
import hmac
import posixpath
import secrets
import time
from urllib.parse import unquote, urlsplit
from flask import current_app, g, jsonify, request, session, url_for
from psycopg2.extras import RealDictCursor
from link import get_connection
from .sql import BACKSTAGE_VERIFY_ADMIN, BACKSTAGE_GET_ADMIN

ADMIN_SESSION_SECONDS = 8 * 60 * 60


class AdminDatabaseUnavailable(Exception):
    pass


def valid_token(expected, supplied):
    return isinstance(expected, str) and bool(expected) and isinstance(supplied, str) and hmac.compare_digest(expected.encode(), supplied.encode())


def _token_for(key):
    if not isinstance(session.get(key), str) or not session[key]:
        session[key] = secrets.token_urlsafe(32)
    return session[key]


def login_csrf_token():
    return _token_for('backstage_login_csrf')


def api_csrf_token():
    return _token_for('backstage_api_csrf')


def clear_admin_session():
    for key in ('backstage_admin_id', 'backstage_authenticated_at', 'backstage_api_csrf'):
        session.pop(key, None)
    g.backstage_admin = None


def begin_admin_session(member_id):
    # 前台登入狀態使用不同欄位；後台只以本次管理者驗證結果建立權限。
    session['backstage_admin_id'] = member_id
    session['backstage_authenticated_at'] = int(time.time())
    session['backstage_api_csrf'] = secrets.token_urlsafe(32)
    session.pop('backstage_login_csrf', None)


def _public_admin(record):
    if record is None:
        return None
    row = dict(record)
    if type(row.get('mId')) is not int or not 0 <= row['mId'] <= 2147483647 or row.get('admin') != 'admin' or not isinstance(row.get('userName'), str):
        return None
    return {key: row[key] for key in ('mId', 'userName', 'admin')}


def authenticate_admin(identifier, password):
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(BACKSTAGE_VERIFY_ADMIN, {'identifier': identifier, 'password': password})
            rows = cur.fetchall()
        return _public_admin(rows[0]) if len(rows) == 1 else None
    except Exception as error:
        current_app.logger.warning('Administrator credential query failed.')
        raise AdminDatabaseUnavailable() from error
    finally:
        if conn is not None:
            conn.close()


def current_admin():
    if hasattr(g, 'backstage_admin'):
        return g.backstage_admin
    member_id = session.get('backstage_admin_id')
    issued = session.get('backstage_authenticated_at')
    if type(member_id) is not int or not 0 <= member_id <= 2147483647 or type(issued) is not int or not 0 <= time.time() - issued < ADMIN_SESSION_SECONDS:
        clear_admin_session()
        return None
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(BACKSTAGE_GET_ADMIN, {'mId': member_id})
            admin = _public_admin(cur.fetchone())
        if admin is None or admin['mId'] != member_id:
            clear_admin_session()
            return None
        g.backstage_admin = admin
        return admin
    except Exception as error:
        current_app.logger.warning('Administrator permission query failed.')
        raise AdminDatabaseUnavailable() from error
    finally:
        if conn is not None:
            conn.close()


def safe_next(value):
    fallback = url_for('backstage.index')
    if not isinstance(value, str) or not value.startswith('/') or value.startswith('//'):
        return fallback
    decoded = unquote(value)
    if '\\' in decoded or any(ord(c) < 32 for c in decoded):
        return fallback
    try:
        parsed = urlsplit(value)
    except ValueError:
        return fallback
    path = posixpath.normpath(unquote(parsed.path))
    if parsed.scheme or parsed.netloc or not (path == '/backstage' or path.startswith('/backstage/')):
        return fallback
    if path.rstrip('/') in ('/backstage/login', '/backstage/logout'):
        return fallback
    return value


def guard_admin_api():
    if request.endpoint == 'api.health':
        return None
    try:
        if current_admin() is not None:
            return None
    except AdminDatabaseUnavailable:
        response = jsonify(status='error', message='暫時無法確認管理者權限，請稍後重新載入。')
        response.headers['Cache-Control'] = 'no-store'
        return response, 503
    response = jsonify(status='error', message='請先登入管理者帳號；若登入已逾時，請重新登入。',
                       loginUrl=url_for('backstage.login'))
    response.headers['Cache-Control'] = 'no-store'
    return response, 401
