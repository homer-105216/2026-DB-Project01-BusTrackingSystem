from flask import Blueprint, jsonify

from link import get_connection
from .routes import list_routes, create_route, update_route, delete_route
from .buses import list_buses, create_bus, update_bus, delete_bus
from .members import list_members, member_details, update_member, delete_member
from .stations import list_stations, create_station, update_station, delete_station
from .bus_types import list_bus_types, create_bus_type, update_bus_type, delete_bus_type

# API Blueprint，網址前綴為 /api，一律回傳 JSON
api_bp = Blueprint('api', __name__)
api_bp.add_url_rule('/routes', endpoint='list_routes', view_func=list_routes, methods=['GET'])

api_bp.add_url_rule('/members', endpoint='list_members', view_func=list_members, methods=['GET'])
api_bp.add_url_rule('/members/<int:member_id>', endpoint='member_details', view_func=member_details, methods=['GET'])
api_bp.add_url_rule('/members/<int:member_id>', endpoint='update_member', view_func=update_member, methods=['PATCH'])
api_bp.add_url_rule('/members/<int:member_id>', endpoint='delete_member', view_func=delete_member, methods=['DELETE'])


api_bp.add_url_rule('/stations', endpoint='list_stations', view_func=list_stations, methods=['GET'])
api_bp.add_url_rule('/stations', endpoint='create_station', view_func=create_station, methods=['POST'])
api_bp.add_url_rule('/stations/<path:station_id>', endpoint='update_station', view_func=update_station, methods=['PATCH'])
api_bp.add_url_rule('/stations/<path:station_id>', endpoint='delete_station', view_func=delete_station, methods=['DELETE'])


api_bp.add_url_rule('/bus-types', endpoint='list_bus_types', view_func=list_bus_types, methods=['GET'])
api_bp.add_url_rule('/bus-types', endpoint='create_bus_type', view_func=create_bus_type, methods=['POST'])
api_bp.add_url_rule('/bus-types/<path:bus_type>', endpoint='update_bus_type', view_func=update_bus_type, methods=['PATCH'])
api_bp.add_url_rule('/bus-types/<path:bus_type>', endpoint='delete_bus_type', view_func=delete_bus_type, methods=['DELETE'])



api_bp.add_url_rule('/buses', endpoint='list_buses', view_func=list_buses, methods=['GET'])
api_bp.add_url_rule('/buses', endpoint='create_bus', view_func=create_bus, methods=['POST'])
api_bp.add_url_rule('/buses/<path:bus_id>', endpoint='update_bus', view_func=update_bus, methods=['PATCH'])
api_bp.add_url_rule('/buses/<path:bus_id>', endpoint='delete_bus', view_func=delete_bus, methods=['DELETE'])

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

api_bp.add_url_rule('/routes', endpoint='create_route', view_func=create_route, methods=['POST'])
api_bp.add_url_rule('/routes/<path:route_id>', endpoint='update_route', view_func=update_route, methods=['PATCH'])
api_bp.add_url_rule('/routes/<path:route_id>', endpoint='delete_route', view_func=delete_route, methods=['DELETE'])

from .schedule_stops import (stop_options, route_stops, create_route_stop,
                             update_route_stop, delete_route_stop, save_stop_time, delete_stop_time)
api_bp.add_url_rule('/schedule/options', endpoint='stop_options', view_func=stop_options, methods=['GET'])
api_bp.add_url_rule('/schedule/stops', endpoint='route_stops', view_func=route_stops, methods=['GET'])
api_bp.add_url_rule('/schedule/stops', endpoint='create_route_stop', view_func=create_route_stop, methods=['POST'])
api_bp.add_url_rule('/schedule/stops', endpoint='update_route_stop', view_func=update_route_stop, methods=['PATCH'])
api_bp.add_url_rule('/schedule/stops', endpoint='delete_route_stop', view_func=delete_route_stop, methods=['DELETE'])
api_bp.add_url_rule('/schedule/stop-times', endpoint='save_stop_time', view_func=save_stop_time, methods=['PUT'])
api_bp.add_url_rule('/schedule/stop-times', endpoint='delete_stop_time', view_func=delete_stop_time, methods=['DELETE'])

from .trips import list_trips, create_trip, update_trip, delete_trip
api_bp.add_url_rule('/schedule/trips', endpoint='list_trips', view_func=list_trips, methods=['GET'])
api_bp.add_url_rule('/schedule/trips', endpoint='create_trip', view_func=create_trip, methods=['POST'])
api_bp.add_url_rule('/schedule/trips/<path:trip_id>', endpoint='update_trip', view_func=update_trip, methods=['PATCH'])
api_bp.add_url_rule('/schedule/trips/<path:trip_id>', endpoint='delete_trip', view_func=delete_trip, methods=['DELETE'])

from .dispatch import list_dispatches, dispatch_options, create_dispatch, update_dispatch, delete_dispatch
api_bp.add_url_rule('/schedule/dispatch', endpoint='list_dispatches', view_func=list_dispatches, methods=['GET'])
api_bp.add_url_rule('/schedule/dispatch/options', endpoint='dispatch_options', view_func=dispatch_options, methods=['GET'])
api_bp.add_url_rule('/schedule/dispatch', endpoint='create_dispatch', view_func=create_dispatch, methods=['POST'])
api_bp.add_url_rule('/schedule/dispatch/<path:trip_id>/<dispatch_date>', endpoint='update_dispatch', view_func=update_dispatch, methods=['PATCH'])
api_bp.add_url_rule('/schedule/dispatch/<path:trip_id>/<dispatch_date>', endpoint='delete_dispatch', view_func=delete_dispatch, methods=['DELETE'])

from .analysis import operation_analysis
api_bp.add_url_rule('/schedule/analysis', endpoint='operation_analysis', view_func=operation_analysis, methods=['GET'])
