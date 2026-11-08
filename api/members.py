"""一般會員管理。僅使用公開會員欄位，SQL 集中於 api/sql.py。"""
import datetime
import hmac
import re
import secrets

import psycopg2
from flask import current_app, jsonify, request, session
from psycopg2.extras import RealDictCursor

from link import get_connection
from .sql import (BACKSTAGE_LIST_MEMBERS, BACKSTAGE_GET_MEMBER,
                  BACKSTAGE_MEMBER_FAVORITE_ROUTES, BACKSTAGE_MEMBER_FAVORITE_STATIONS,
                  BACKSTAGE_MEMBER_SUMMARY, BACKSTAGE_LOCK_MEMBER_IDENTITIES,
                  BACKSTAGE_MEMBER_IDENTITY_CONFLICT, BACKSTAGE_UPDATE_MEMBER,
                  BACKSTAGE_DELETE_MEMBER)


def _response(payload, status=200):
    response = jsonify(payload)
    response.headers['Cache-Control'] = 'no-store'
    return response, status


def _error(message, status):
    return _response({'status': 'error', 'message': message}, status)


def _csrf_token():
    if 'backstage_api_csrf' not in session:
        session['backstage_api_csrf'] = secrets.token_urlsafe(32)
    return session['backstage_api_csrf']


def _valid_csrf():
    expected = session.get('backstage_api_csrf')
    return isinstance(expected, str) and hmac.compare_digest(expected.encode(), request.headers.get('X-CSRF-Token', '').encode())


def _rollback(conn):
    if conn is not None:
        try:
            conn.rollback()
        except Exception:
            pass


def _valid_id(member_id):
    return type(member_id) is int and 0 <= member_id <= 2147483647


def _public_member(row):
    # 明確白名單；即使日後 SQL 多回傳欄位，也不把密碼帶到網頁。
    registered = row['registerDatetime']
    if isinstance(registered, datetime.datetime):
        registered = registered.isoformat(sep=' ', timespec='seconds')
    return {'mId': row['mId'], 'userName': row['userName'], 'email': row['email'],
            'registerDatetime': registered, 'admin': row['admin']}


def list_members():
    """GET /api/members；只列 user，summary 不受 keyword 篩選影響。"""
    keyword = request.args.get('keyword', '').strip()
    if len(keyword) > 200:
        return _error('搜尋關鍵字不得超過 200 字元。', 400)
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(BACKSTAGE_LIST_MEMBERS, {'keyword': keyword or None})
            members = [_public_member(row) for row in cur.fetchall()]
            cur.execute(BACKSTAGE_MEMBER_SUMMARY)
            summary = dict(cur.fetchone())
        return _response({'status': 'ok', 'members': members, 'summary': summary,
                          'count': len(members), 'csrfToken': _csrf_token()})
    except Exception:
        current_app.logger.warning('Member list database query failed.')
        return _error('無法讀取會員資料，請確認資料庫連線後重試。', 503)
    finally:
        if conn is not None:
            conn.close()


def member_details(member_id):
    """GET /api/members/<id>；一般會員基本資料與兩類有效收藏。"""
    if not _valid_id(member_id):
        return _error('會員編號不正確。', 400)
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            params = {'mId': member_id}
            cur.execute(BACKSTAGE_GET_MEMBER, params)
            row = cur.fetchone()
            if row is None:
                return _error('找不到此一般會員，請重新載入列表。', 404)
            member = _public_member(row)
            cur.execute(BACKSTAGE_MEMBER_FAVORITE_ROUTES, params)
            routes = [dict(row) for row in cur.fetchall()]
            cur.execute(BACKSTAGE_MEMBER_FAVORITE_STATIONS, params)
            stations = [dict(row) for row in cur.fetchall()]
        return _response({'status': 'ok', 'member': member, 'favoriteRoutes': routes, 'favoriteStations': stations})
    except Exception:
        current_app.logger.warning('Member details database query failed.')
        return _error('無法讀取會員詳細資料，請稍後重試。', 503)
    finally:
        if conn is not None:
            conn.close()


def update_member(member_id):
    """PATCH /api/members/<id>；只接受 userName、email。"""
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    if not _valid_id(member_id):
        return _error('會員編號不正確。', 400)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {'userName', 'email'}:
        return _error('只允許修改會員名稱與 Email，不可修改編號、角色、密碼或註冊時間。', 400)
    name, email = payload['userName'], payload['email']
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 50 or '\x00' in name:
        return _error('請填寫 1 至 50 字的會員名稱。', 400)
    if not isinstance(email, str) or len(email.strip()) > 100 or '\x00' in email or not re.fullmatch(r'[^@\s]+@[^@\s]+', email.strip()):
        return _error('請填寫有效的 Email，長度不得超過 100 字。', 400)
    params = {'mId': member_id, 'userName': name.strip(), 'email': email.strip()}
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 同交易內鎖定、檢查身分衝突，再更新；避免兩次後台更新互相覆蓋規則。
            cur.execute(BACKSTAGE_LOCK_MEMBER_IDENTITIES)
            cur.execute(BACKSTAGE_GET_MEMBER, {'mId': member_id})
            if cur.fetchone() is None:
                _rollback(conn)
                return _error('找不到此一般會員，請重新載入列表。', 404)
            cur.execute(BACKSTAGE_MEMBER_IDENTITY_CONFLICT, params)
            if cur.fetchone() is not None:
                _rollback(conn)
                return _error('會員名稱或 Email 已被其他帳號使用。', 409)
            cur.execute(BACKSTAGE_UPDATE_MEMBER, params)
            row = cur.fetchone()
        if row is None:
            _rollback(conn)
            return _error('無法更新此會員，請重新載入確認資料。', 409)
        member = _public_member(row)
        conn.commit()
        return _response({'status': 'ok', 'member': member, 'message': '已更新資料庫會員資料。'})
    except psycopg2.IntegrityError:
        _rollback(conn)
        return _error('會員資料重複或不符合資料庫限制，請確認名稱與 Email。', 409)
    except Exception:
        _rollback(conn)
        current_app.logger.warning('Member database update failed.')
        return _error('資料庫操作失敗，請重新載入確認目前資料後再試。', 503)
    finally:
        if conn is not None:
            conn.close()


def delete_member(member_id):
    """DELETE /api/members/<id>；僅刪 user，收藏由既有 FK 原子級聯清理。"""
    if not _valid_csrf():
        return _error('操作驗證已失效，請重新載入頁面後再試。', 403)
    if not _valid_id(member_id):
        return _error('會員編號不正確。', 400)
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(BACKSTAGE_DELETE_MEMBER, {'mId': member_id})
            row = cur.fetchone()
        if row is None:
            _rollback(conn)
            return _error('找不到此一般會員，管理者帳號不由此頁刪除。', 404)
        conn.commit()
        return _response({'status': 'ok', 'mId': row['mId'], 'message': '已刪除資料庫會員及其路線、站點收藏。'})
    except psycopg2.IntegrityError:
        _rollback(conn)
        return _error('此會員仍被其他資料引用，無法刪除。', 409)
    except Exception:
        _rollback(conn)
        current_app.logger.warning('Member database deletion failed.')
        return _error('資料庫操作失敗，請重新載入確認目前資料後再試。', 503)
    finally:
        if conn is not None:
            conn.close()
