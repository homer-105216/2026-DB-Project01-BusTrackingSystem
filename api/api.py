from flask import Blueprint, jsonify

from api import sql as queries
from link import get_connection

# API Blueprint，網址前綴為 /api，一律回傳 JSON
api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health():
    """檢查資料庫連線：GET /api/health"""
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(queries.DATABASE_HEALTH)
                database, version = cur.fetchone()
        finally:
            conn.close()
        return jsonify(status='ok', database=database, version=version)
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500
