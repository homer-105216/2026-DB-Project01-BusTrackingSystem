from flask import Blueprint, jsonify

from link import get_connection
from .routes import list_routes
from .stations import list_stations, create_station, update_station, delete_station
from .bus_types import list_bus_types, create_bus_type, update_bus_type, delete_bus_type

# API Blueprint，網址前綴為 /api，一律回傳 JSON
api_bp = Blueprint('api', __name__)
api_bp.add_url_rule('/routes', endpoint='list_routes', view_func=list_routes, methods=['GET'])

api_bp.add_url_rule('/stations', endpoint='list_stations', view_func=list_stations, methods=['GET'])
api_bp.add_url_rule('/stations', endpoint='create_station', view_func=create_station, methods=['POST'])
api_bp.add_url_rule('/stations/<path:station_id>', endpoint='update_station', view_func=update_station, methods=['PATCH'])
api_bp.add_url_rule('/stations/<path:station_id>', endpoint='delete_station', view_func=delete_station, methods=['DELETE'])


api_bp.add_url_rule('/bus-types', endpoint='list_bus_types', view_func=list_bus_types, methods=['GET'])
api_bp.add_url_rule('/bus-types', endpoint='create_bus_type', view_func=create_bus_type, methods=['POST'])
api_bp.add_url_rule('/bus-types/<path:bus_type>', endpoint='update_bus_type', view_func=update_bus_type, methods=['PATCH'])
api_bp.add_url_rule('/bus-types/<path:bus_type>', endpoint='delete_bus_type', view_func=delete_bus_type, methods=['DELETE'])



@api_bp.route('/health')
def health():
    """檢查資料庫連線：GET /api/health"""
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT current_database(), version();')
                database, version = cur.fetchone()
        finally:
            conn.close()
        return jsonify(status='ok', database=database, version=version)
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500
