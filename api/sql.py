"""SQL statements used by the Flask app and database tools."""

# link.py

SERVER_VERSION = 'SELECT version();'

# api/api.py

DATABASE_HEALTH = 'SELECT current_database(), version();'

# frontstage/views/frontstage.py

LIST_ROUTES = """
SELECT "routeId", "routeName", "origin", "destination"
FROM public."Route" ORDER BY "routeId"
"""

LIST_STATIONS = """
SELECT s."stationId", s."sName", s."address",
       COALESCE((
           SELECT json_agg(r ORDER BY r."routeId")
           FROM (
               SELECT DISTINCT r."routeId", r."routeName"
               FROM public."Contain" c
               JOIN public."Route" r USING ("routeId")
               WHERE c."stationId" = s."stationId"
           ) r
       ), '[]'::json) AS routes
FROM public."Station" s
WHERE (%(ids)s::varchar[] IS NULL OR s."stationId" = ANY(%(ids)s))
ORDER BY ((s."sLatitude" - %(lat)s)^2
          + ((s."sLongitude" - %(lng)s) * cos(radians(%(lat)s)))^2)
          NULLS LAST, s."stationId"
LIMIT %(limit)s
"""

LIST_MEMBER_FAVORITES = """
SELECT 'routes' AS kind, "routeId" AS id FROM public."Favorite_Route" WHERE "mId" = %s
UNION ALL
SELECT 'stations', "stationId" FROM public."Favorite_Station" WHERE "mId" = %s
"""

LIST_ROUTE_STOPS = """
SELECT s."stationId", s."sName", s."address", c."stopSequence",
       s."sLatitude"::float8 AS "sLatitude", s."sLongitude"::float8 AS "sLongitude"
FROM public."Contain" c JOIN public."Station" s USING ("stationId")
WHERE c."routeId" = %s AND c."rDirection" = %s ORDER BY c."stopSequence"
"""

LIST_ROUTE_TRIPS = """
SELECT t."tId", to_char(t."departureTime"::interval, 'HH24:MI') AS "departureTime",
       COALESCE(d."bId", '-') AS "bId", COALESCE(b."busType", '-') AS "busType",
       COALESCE(d."status", '未派車') AS status
FROM public."Trip" t
LEFT JOIN LATERAL (
    SELECT "bId", "status" FROM public."Daily_Trip_Implement"
    WHERE "tId" = t."tId" ORDER BY "date" DESC LIMIT 1
) d ON true
LEFT JOIN public."Bus" b ON b."bId" = d."bId"
WHERE t."routeId" = %s AND t."tDirection" = %s ORDER BY t."departureTime"
"""

LOCK_MEMBER = 'SELECT "mId" FROM public."Member" WHERE "mId" = %s FOR UPDATE'

DELETE_FAVORITE = 'DELETE FROM public.{} WHERE "mId" = %s AND {} = %s'

INSERT_FAVORITE = 'INSERT INTO public.{} ("mId", {}) VALUES (%s, %s)'

COUNT_FAVORITES = 'SELECT count(*) FROM public.{} WHERE "mId" = %s'

VERIFY_MEMBER = """
SELECT "mId", "userName", "email", "registerDatetime", "admin"
FROM public."Member"
WHERE (lower("email") = lower(%s) OR "userName" = %s) AND "password" = %s
LIMIT 2
"""

REGISTER_MEMBER = 'INSERT INTO member (userName, email, password) VALUES (%s, %s, %s) RETURNING mId'

# database/location_replay.py

REPLAY_TIMEOUT = "SET LOCAL statement_timeout = '5s'"

LATEST_TRIP_LOCATION = """
SELECT log."date", log."recordDatetime", trip."departureTime"
FROM public."Location_Log" AS log
JOIN public."Trip" AS trip USING ("tId")
WHERE log."tId" = %s AND log."date" = (
    SELECT max("date") FROM public."Daily_Trip_Implement" WHERE "tId" = %s
)
ORDER BY log."recordDatetime" DESC
LIMIT 1
FOR UPDATE OF log
"""

REPLAY_STOPS = """
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
"""

UPDATE_TRIP_LOCATION = """
UPDATE public."Location_Log"
SET "recordDatetime" = %s, "lLatitude" = %s, "lLongitude" = %s
WHERE "tId" = %s AND "date" = %s AND "recordDatetime" = %s
"""

# database/bus_data.py

PUBLIC_SEARCH_PATH = 'SET LOCAL search_path TO public'

HAS_PUBLIC_RELATIONS = """
SELECT EXISTS (
    SELECT FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'f', 'v', 'm')
)
"""

LOCK_IMPORT_TABLES = 'LOCK TABLE {tables} IN SHARE ROW EXCLUSIVE MODE'

LIST_TABLE_COLUMNS = 'SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position'

COUNT_TABLE_ROWS = 'SELECT COUNT(*) FROM public.{table}'

COPY_TABLE_ROWS = 'COPY public.{table} ({columns}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)'
