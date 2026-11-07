import os

import psycopg2
from dotenv import load_dotenv

from api import sql as queries

load_dotenv()  # 從 .env 讀取連線資訊

DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'dbname': os.getenv('DB_NAME'),
}


def get_connection():
    """建立一條新的 PostgreSQL 連線，用完請記得 close()。"""
    missing = [key for key, value in DB_CONFIG.items() if not value]
    if missing:
        raise RuntimeError(f'.env 缺少連線設定：{", ".join(missing)}')
    return psycopg2.connect(connect_timeout=5, **DB_CONFIG)


if __name__ == '__main__':
    # 直接執行 python link.py 可以測試連線
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(queries.SERVER_VERSION)
            print('連線成功：', cur.fetchone()[0])
    finally:
        conn.close()
