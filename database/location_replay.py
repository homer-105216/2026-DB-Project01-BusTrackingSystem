"""Replay the T0001 bus position while the Flask server is running."""

from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from threading import Event, Thread

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
        cur.execute("SET LOCAL statement_timeout = '5s'")
        cur.execute("""
            SELECT log."date", log."recordDatetime", trip."departureTime"
            FROM public."Location_Log" AS log
            JOIN public."Trip" AS trip USING ("tId")
            WHERE log."tId" = %s AND log."date" = (
                SELECT max("date") FROM public."Daily_Trip_Implement" WHERE "tId" = %s
            )
            ORDER BY log."recordDatetime" DESC
            LIMIT 1
            FOR UPDATE OF log
        """, (TRIP_ID, TRIP_ID))
        latest = cur.fetchone()
        if latest is None:
            return 'T0001 最新班次缺少位置紀錄'

        service_date, previous, departure = latest
        timestamp = previous + STEP
        if timestamp.date() != service_date:
            return 'T0001 回放時間已到班次日期的午夜'

        cur.execute("""
            SELECT run."expArrivalTime", station."sLatitude", station."sLongitude"
            FROM public."Trip" AS trip
            JOIN public."Contain" AS stop
              ON stop."routeId" = trip."routeId"
             AND stop."rDirection"::text = trip."tDirection"::text
            JOIN public."Station" AS station USING ("stationId")
            JOIN public."Run" AS run
              ON run."tId" = trip."tId" AND run."stationId" = stop."stationId"
            WHERE trip."tId" = %s
            ORDER BY stop."stopSequence"
        """, (TRIP_ID,))
        rows = cur.fetchall()
        if not rows:
            return 'T0001 缺少站點時刻'

        first_arrival = rows[0][0]
        stops = [((arrival - first_arrival).total_seconds(), float(lat), float(lon))
                 for arrival, lat, lon in rows]
        elapsed = (timestamp - datetime.combine(service_date, departure)).total_seconds()
        latitude, longitude = position_at(stops, elapsed)

        cur.execute("""
            UPDATE public."Location_Log"
            SET "recordDatetime" = %s, "lLatitude" = %s, "lLongitude" = %s
            WHERE "tId" = %s AND "date" = %s AND "recordDatetime" = %s
        """, (timestamp, latitude, longitude, TRIP_ID, service_date, previous))
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
