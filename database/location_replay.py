"""Replay the T0001 bus position while the Flask server is running."""

from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from threading import Event, Thread

from api import sql as queries
from link import get_connection

TRIP_ID = 'T0001'
INTERVAL_SECONDS = 15
STEP = timedelta(seconds=INTERVAL_SECONDS)


def position_at(stops, elapsed):
    """Interpolate along the scheduled stops, restarting after the terminal."""
    duration = stops[-1][0] - stops[0][0]
    if duration <= 0:
        return stops[0][1:]
    offset = stops[0][0] + elapsed % duration
    for (start, lat, lon), (end, next_lat, next_lon) in zip(stops, stops[1:]):
        if start <= offset < end:
            fraction = (offset - start) / (end - start)
            return (lat + (next_lat - lat) * fraction,
                    lon + (next_lon - lon) * fraction)
    return stops[-1][1:]


def update_position():
    with closing(get_connection()) as conn, conn, conn.cursor() as cur:
        cur.execute(queries.REPLAY_TIMEOUT)
        cur.execute(queries.LATEST_TRIP_LOCATION, (TRIP_ID, TRIP_ID))
        latest = cur.fetchone()
        if latest is None:
            return 'T0001 最新班次缺少位置紀錄'

        service_date, previous, departure = latest
        cur.execute(queries.REPLAY_STOPS, (TRIP_ID,))
        rows = cur.fetchall()
        if not rows:
            return 'T0001 缺少站點時刻'

        first_arrival = rows[0][0]
        stops = [((arrival - first_arrival).total_seconds(), float(lat), float(lon))
                 for arrival, lat, lon in rows]
        start = datetime.combine(service_date, departure)
        end = start + timedelta(seconds=max(stops[-1][0] - stops[0][0], 0))

        timestamp = previous + STEP
        if not start <= timestamp < end:
            # 跑完一趟（或時間不在班次範圍內）就回到發車時間重新循環，
            # 模擬時鐘永遠停在班次時間內，不會再跑到午夜而停止寫入。
            timestamp = start
            # 模擬只維護一筆位置紀錄；回到發車時間前先清掉同日其他舊紀錄，避免主鍵重複。
            cur.execute(queries.REPLAY_CLEAR_OTHER_LOCATIONS, (TRIP_ID, service_date, previous))
        elapsed = (timestamp - start).total_seconds()
        latitude, longitude = position_at(stops, elapsed)

        cur.execute(queries.UPDATE_TRIP_LOCATION, (timestamp, latitude, longitude, TRIP_ID, service_date, previous))
        if cur.rowcount != 1:
            raise RuntimeError('T0001 的位置紀錄已變更，將於下一輪重試')
    return None


def run(stop, logger):
    last_reason = None
    while not stop.wait(INTERVAL_SECONDS):
        try:
            reason = update_position()
            if reason and reason != last_reason:
                logger.warning('%s，暫停寫入', reason)
            last_reason = reason
        except Exception:
            logger.exception('T0001 位置更新失敗，將於下一輪重試')


@contextmanager
def location_replay(logger, enabled=True):
    if not enabled:
        yield
        return

    stop = Event()
    worker = Thread(target=run, args=(stop, logger), name='bus-location-replay', daemon=True)
    worker.start()
    try:
        yield
    finally:
        stop.set()
        worker.join(timeout=6)
