"""SQL statements used by the Flask app and database tools."""

# link.py

SERVER_VERSION = 'SELECT version();'

# api/api.py

DATABASE_HEALTH = 'SELECT current_database(), version();'

# frontstage/views/frontstage.py - 首頁 (index.html)

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

LOCK_MEMBER = 'SELECT "mId" FROM public."Member" WHERE "mId" = %s FOR UPDATE'

DELETE_FAVORITE = 'DELETE FROM public.{} WHERE "mId" = %s AND {} = %s'

INSERT_FAVORITE = 'INSERT INTO public.{} ("mId", {}) VALUES (%s, %s)'

COUNT_FAVORITES = 'SELECT count(*) FROM public.{} WHERE "mId" = %s'

# frontstage/views/frontstage.py - 會員登入 (login.html)

VERIFY_MEMBER = """
SELECT "mId", "userName", "email",
       to_char("registerDatetime", 'YYYY-MM-DD HH24:MI:SS') AS "registerDatetime",
       "admin"
FROM public."Member"
WHERE (lower("email") = lower(%s) OR "userName" = %s) AND "password" = %s
LIMIT 2
"""

# frontstage/views/frontstage.py - 會員註冊 (register.html)

CHECK_MEMBER_EXISTS = """
SELECT "mId", "userName", "email"
FROM public."Member"
WHERE lower("email") = lower(%s) OR "userName" = %s
LIMIT 1
"""

REGISTER_MEMBER = """
INSERT INTO public."Member" ("mId", "userName", "email", "password", "registerDatetime", "admin")
VALUES (
    COALESCE((SELECT max("mId") FROM public."Member"), 0) + 1,
    %s, %s, %s, CURRENT_TIMESTAMP, 'user'
)
RETURNING "mId", "userName", "email",
          to_char("registerDatetime", 'YYYY-MM-DD HH24:MI:SS') AS "registerDatetime",
          "admin"
"""

# frontstage/views/frontstage.py - 個人資料與密碼設定 (profile.html)

GET_MEMBER_BY_ID = """
SELECT "mId", "userName", "email",
       to_char("registerDatetime", 'YYYY-MM-DD HH24:MI:SS') AS "registerDatetime",
       "admin"
FROM public."Member"
WHERE "mId" = %s
"""

CHECK_MEMBER_CONFLICT = """
SELECT "mId" FROM public."Member"
WHERE (lower("email") = lower(%s) OR "userName" = %s) AND "mId" <> %s
LIMIT 1
"""

VERIFY_MEMBER_PASSWORD = """
SELECT "mId" FROM public."Member"
WHERE "mId" = %s AND "password" = %s
"""

UPDATE_MEMBER_PROFILE = """
UPDATE public."Member"
SET "userName" = %s, "email" = %s
WHERE "mId" = %s
RETURNING "mId", "userName", "email",
          to_char("registerDatetime", 'YYYY-MM-DD HH24:MI:SS') AS "registerDatetime",
          "admin"
"""

UPDATE_MEMBER_PROFILE_WITH_PASSWORD = """
UPDATE public."Member"
SET "userName" = %s, "email" = %s, "password" = %s
WHERE "mId" = %s
RETURNING "mId", "userName", "email",
          to_char("registerDatetime", 'YYYY-MM-DD HH24:MI:SS') AS "registerDatetime",
          "admin"
"""

COUNT_MEMBER_FAVORITE_ROUTES = 'SELECT count(*) FROM public."Favorite_Route" WHERE "mId" = %s'

COUNT_MEMBER_FAVORITE_STATIONS = 'SELECT count(*) FROM public."Favorite_Station" WHERE "mId" = %s'

# frontstage/views/frontstage.py - 我的收藏清單 (favorites.html)

LIST_MEMBER_FAVORITE_ROUTES = """
SELECT r."routeId", r."routeName", r."origin", r."destination"
FROM public."Favorite_Route" f
JOIN public."Route" r USING ("routeId")
WHERE f."mId" = %s
ORDER BY r."routeId"
"""

LIST_MEMBER_FAVORITE_STATIONS = """
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
FROM public."Favorite_Station" f
JOIN public."Station" s USING ("stationId")
WHERE f."mId" = %s
ORDER BY s."stationId"
"""

# frontstage/views/frontstage.py - 路線詳情 (route_detail.html)

GET_ROUTE_BY_ID = """
SELECT "routeId", "routeName", "origin", "destination"
FROM public."Route"
WHERE "routeId" = %s
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

LIST_ROUTE_LIVE_BUSES = """
SELECT d."bId", b."busType", d."status",
       l."lLatitude"::float8 AS "lLatitude",
       l."lLongitude"::float8 AS "lLongitude",
       to_char(l."recordDatetime", 'YYYY-MM-DD HH24:MI:SS') AS "recordDatetime",
       (
           SELECT s."stationId"
           FROM public."Contain" c
           JOIN public."Station" s USING ("stationId")
           WHERE c."routeId" = t."routeId" AND c."rDirection"::text = t."tDirection"::text
           ORDER BY ((s."sLatitude" - l."lLatitude")^2 + ((s."sLongitude" - l."lLongitude") * cos(radians(l."lLatitude")))^2)
           LIMIT 1
       ) AS "nearestStationId"
FROM public."Trip" t
JOIN public."Daily_Trip_Implement" d ON d."tId" = t."tId"
JOIN public."Bus" b ON b."bId" = d."bId"
JOIN LATERAL (
    SELECT "lLatitude", "lLongitude", "recordDatetime"
    FROM public."Location_Log"
    WHERE "tId" = d."tId" AND "date" = d."date"
    ORDER BY "recordDatetime" DESC LIMIT 1
) l ON true
WHERE t."routeId" = %s AND t."tDirection" = %s
  AND d."date" = (
      SELECT max("date") FROM public."Daily_Trip_Implement" WHERE "tId" = t."tId"
  )
ORDER BY l."recordDatetime" DESC
"""

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
