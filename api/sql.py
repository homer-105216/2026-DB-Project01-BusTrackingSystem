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



# ============================================================================
# BACKSTAGE: CMS / SCHEDULE / ANALYSIS
# 依 2026-11-08 實際 public schema 與後台需求新增；保留上方前台／工具 SQL。
# 使用方式：cur.execute(BACKSTAGE_..., params_dict)，不要自行拼接使用者輸入。
# keyword 可傳 None／空字串；ILIKE 支援部分比對（%／_ 仍為 SQL 萬用字元）。
# 所有異動由呼叫端 commit／rollback；RETURNING 回傳 0 筆時須區分不存在、
# 衝突或關聯限制。不要將「0 筆」一律當成功。
# 實際角色 enum: user / admin；rDirection、tDirection: 去程 / 回程。
# UI 的「返程」須由 API 映射為「回程」，SQL 保留資料庫原值。
# 所有 ID 目前均手動提供；Member.mId 為 int，非畫面示範的 M001。
# 管理者登入暫不啟用；本區不新增或回傳 password。
# ============================================================================

# --- CMS: 一般會員 -----------------------------------------------------------

# Input: keyword。Output: mId, userName, email, registerDatetime, admin。
BACKSTAGE_LIST_MEMBERS = """
SELECT "mId", "userName", "email", "registerDatetime", "admin"::text AS "admin"
FROM public."Member"
WHERE "admin"::text = 'user'
  AND (COALESCE(%(keyword)s::text, '') = ''
       OR "mId"::text ILIKE '%%' || %(keyword)s || '%%'
       OR "userName" ILIKE '%%' || %(keyword)s || '%%'
       OR "email" ILIKE '%%' || %(keyword)s || '%%')
ORDER BY "mId"
"""

# Input: mId (int)。Output: 同列表；管理者或不存在則 0 筆。
BACKSTAGE_GET_MEMBER = """
SELECT "mId", "userName", "email", "registerDatetime", "admin"::text AS "admin"
FROM public."Member" WHERE "mId" = %(mId)s AND "admin"::text = 'user'
"""

# Input: mId。Output: routeId, routeName；僅一般會員的有效收藏。
BACKSTAGE_MEMBER_FAVORITE_ROUTES = """
SELECT r."routeId", r."routeName"
FROM public."Favorite_Route" f
JOIN public."Member" m USING ("mId")
JOIN public."Route" r USING ("routeId")
WHERE f."mId" = %(mId)s AND m."admin"::text = 'user'
ORDER BY r."routeId"
"""

# Input: mId。Output: stationId, sName。
BACKSTAGE_MEMBER_FAVORITE_STATIONS = """
SELECT s."stationId", s."sName"
FROM public."Favorite_Station" f
JOIN public."Member" m USING ("mId")
JOIN public."Station" s USING ("stationId")
WHERE f."mId" = %(mId)s AND m."admin"::text = 'user'
ORDER BY s."stationId"
"""

# Input: mId (新增檢查可 None), userName, email。Output: 衝突帳號的 mId。
# 現有 DB 僅限制 email 完全相同；無 userName 唯一／lower(email) 唯一限制。
# 本查詢不能取代全組一致的註冊驗證或真正的唯一索引；需與沛芳確認。
BACKSTAGE_MEMBER_IDENTITY_CONFLICT = """
SELECT "mId" FROM public."Member"
WHERE (%(mId)s::integer IS NULL OR "mId" <> %(mId)s)
  AND ("userName" = %(userName)s OR lower("email") = lower(%(email)s))
ORDER BY "mId"
"""

# 編輯交易若需序列化身分衝突檢查，可先執行此鎖，再查衝突／UPDATE。
# 不可在 autocommit 下使用；前台註冊的唯一性規則仍須共同確認。
BACKSTAGE_LOCK_MEMBER_IDENTITIES = 'LOCK TABLE public."Member" IN SHARE ROW EXCLUSIVE MODE'

# Input: mId, userName, email。Output: 更新後公開欄位；不修改角色／時間。
# 空白／衝突／非一般會員均回傳 0 筆，由 API 明確辨識原因。
BACKSTAGE_UPDATE_MEMBER = """
UPDATE public."Member" AS m
SET "userName" = %(userName)s, "email" = %(email)s
WHERE m."mId" = %(mId)s AND m."admin"::text = 'user'
  AND btrim(%(userName)s::text) <> '' AND btrim(%(email)s::text) <> ''
  AND NOT EXISTS (
      SELECT 1 FROM public."Member" other
      WHERE other."mId" <> m."mId"
        AND (other."userName" = %(userName)s OR lower(other."email") = lower(%(email)s))
  )
RETURNING m."mId", m."userName", m."email", m."registerDatetime", m."admin"::text AS "admin"
"""

# Input: mId。Output: 刪除的 mId。
# 已確認兩個 Favorite 表對 Member 均 ON DELETE CASCADE：單一語句原子清理收藏。
# 不會刪 Route／Station，也不允許用此語句刪管理者。
BACKSTAGE_DELETE_MEMBER = """
DELETE FROM public."Member"
WHERE "mId" = %(mId)s AND "admin"::text = 'user'
RETURNING "mId"
"""

# Input: 無。Output: userCount, favoriteMemberCount，無資料仍回傳一列 0。
BACKSTAGE_MEMBER_SUMMARY = """
SELECT count(*) AS "userCount",
       count(*) FILTER (WHERE
           EXISTS (SELECT 1 FROM public."Favorite_Route" f
                   JOIN public."Route" r USING ("routeId") WHERE f."mId" = m."mId")
           OR EXISTS (SELECT 1 FROM public."Favorite_Station" f
                      JOIN public."Station" s USING ("stationId") WHERE f."mId" = m."mId")
       ) AS "favoriteMemberCount"
FROM public."Member" m WHERE m."admin"::text = 'user'
"""

# --- CMS: 路線 ---------------------------------------------------------------

# 既有 LIST_ROUTES 可繼續共用；本語句在 DB 支援 keyword。
# Input: keyword。Output: routeId, routeName, origin, destination。
BACKSTAGE_LIST_ROUTES = """
SELECT "routeId", "routeName", "origin", "destination" FROM public."Route"
WHERE COALESCE(%(keyword)s::text, '') = ''
   OR "routeId" ILIKE '%%' || %(keyword)s || '%%'
   OR "routeName" ILIKE '%%' || %(keyword)s || '%%'
   OR "origin" ILIKE '%%' || %(keyword)s || '%%'
   OR "destination" ILIKE '%%' || %(keyword)s || '%%'
ORDER BY "routeId"
"""

# Input: routeId, routeName, origin, destination。Output: 新增後四個欄位。
BACKSTAGE_INSERT_ROUTE = """
INSERT INTO public."Route" ("routeId", "routeName", "origin", "destination")
VALUES (%(routeId)s, %(routeName)s, %(origin)s, %(destination)s)
RETURNING "routeId", "routeName", "origin", "destination"
"""

# Input: routeId (不變), routeName, origin, destination。Output: 更新後資料。
BACKSTAGE_UPDATE_ROUTE = """
UPDATE public."Route"
SET "routeName" = %(routeName)s, "origin" = %(origin)s, "destination" = %(destination)s
WHERE "routeId" = %(routeId)s
RETURNING "routeId", "routeName", "origin", "destination"
"""

# Input: routeId。刪除前在同一交易先鎖目標，再查引用／DELETE。
# 兩個語句分開執行，READ COMMITTED 下可在鎖取得後使用新的查詢快照。
BACKSTAGE_LOCK_ROUTE = 'SELECT "routeId" FROM public."Route" WHERE "routeId" = %(routeId)s FOR UPDATE'

# Input: routeId。Output: 3 類引用筆數；可用於 UI 說明禁止刪除原因。
BACKSTAGE_ROUTE_REFERENCES = """
SELECT (SELECT count(*) FROM public."Contain" WHERE "routeId" = %(routeId)s) AS "stopCount",
       (SELECT count(*) FROM public."Trip" WHERE "routeId" = %(routeId)s) AS "tripCount",
       (SELECT count(*) FROM public."Favorite_Route" WHERE "routeId" = %(routeId)s) AS "favoriteCount"
"""

# Input: routeId。Output: 被刪除的 routeId。引用存在則 0 筆。
# 現有收藏 FK 是 CASCADE，故這裡顯式阻擋，以符合後台「被引用禁止刪除」。
# 必須先 BACKSTAGE_LOCK_ROUTE，避免與並行新增收藏形成競態。
BACKSTAGE_DELETE_ROUTE = """
DELETE FROM public."Route" r WHERE r."routeId" = %(routeId)s
  AND NOT EXISTS (SELECT 1 FROM public."Contain" c WHERE c."routeId" = r."routeId")
  AND NOT EXISTS (SELECT 1 FROM public."Trip" t WHERE t."routeId" = r."routeId")
  AND NOT EXISTS (SELECT 1 FROM public."Favorite_Route" f WHERE f."routeId" = r."routeId")
RETURNING r."routeId"
"""

# --- CMS: 站點 ---------------------------------------------------------------

# Input: keyword。Output: stationId, sName, address, sLatitude, sLongitude。
BACKSTAGE_LIST_STATIONS = """
SELECT "stationId", "sName", "address", "sLatitude"::float8 AS "sLatitude",
       "sLongitude"::float8 AS "sLongitude" FROM public."Station"
WHERE COALESCE(%(keyword)s::text, '') = ''
   OR "stationId" ILIKE '%%' || %(keyword)s || '%%'
   OR "sName" ILIKE '%%' || %(keyword)s || '%%'
   OR "address" ILIKE '%%' || %(keyword)s || '%%'
ORDER BY "stationId"
"""

# Input: stationId, sName, address, sLatitude, sLongitude。Output: 新增後資料。
# DB 已有經緯度範圍 CHECK；API 仍須檢查有限數值與必填。
BACKSTAGE_INSERT_STATION = """
INSERT INTO public."Station" ("stationId", "sName", "address", "sLatitude", "sLongitude")
VALUES (%(stationId)s, %(sName)s, %(address)s, %(sLatitude)s, %(sLongitude)s)
RETURNING "stationId", "sName", "address", "sLatitude"::float8 AS "sLatitude", "sLongitude"::float8 AS "sLongitude"
"""

# Input: stationId (不變), sName, address, sLatitude, sLongitude。Output: 更新後資料。
BACKSTAGE_UPDATE_STATION = """
UPDATE public."Station"
SET "sName" = %(sName)s, "address" = %(address)s,
    "sLatitude" = %(sLatitude)s, "sLongitude" = %(sLongitude)s
WHERE "stationId" = %(stationId)s
RETURNING "stationId", "sName", "address", "sLatitude"::float8 AS "sLatitude", "sLongitude"::float8 AS "sLongitude"
"""

# Input: stationId。同路線刪除規則，先鎖定再執行刪除／引用查詢。
BACKSTAGE_LOCK_STATION = 'SELECT "stationId" FROM public."Station" WHERE "stationId" = %(stationId)s FOR UPDATE'

# Input: stationId。Output: 3 類引用筆數。
BACKSTAGE_STATION_REFERENCES = """
SELECT (SELECT count(*) FROM public."Contain" WHERE "stationId" = %(stationId)s) AS "stopCount",
       (SELECT count(*) FROM public."Run" WHERE "stationId" = %(stationId)s) AS "runCount",
       (SELECT count(*) FROM public."Favorite_Station" WHERE "stationId" = %(stationId)s) AS "favoriteCount"
"""

# Input: stationId。Output: 被刪除的 stationId；引用存在則 0 筆。
BACKSTAGE_DELETE_STATION = """
DELETE FROM public."Station" s WHERE s."stationId" = %(stationId)s
  AND NOT EXISTS (SELECT 1 FROM public."Contain" c WHERE c."stationId" = s."stationId")
  AND NOT EXISTS (SELECT 1 FROM public."Run" r WHERE r."stationId" = s."stationId")
  AND NOT EXISTS (SELECT 1 FROM public."Favorite_Station" f WHERE f."stationId" = s."stationId")
RETURNING s."stationId"
"""

# --- CMS: 車型、車輛 ---------------------------------------------------------

# Input: keyword。Output: busType, capacity；同時可作車型選單。
BACKSTAGE_LIST_BUS_TYPES = """
SELECT "busType", "capacity" FROM public."Bus_Type"
WHERE COALESCE(%(keyword)s::text, '') = '' OR "busType" ILIKE '%%' || %(keyword)s || '%%'
ORDER BY "busType"
"""

# Input: busType, capacity。Output: 新增後資料；DB CHECK capacity > 0。
BACKSTAGE_INSERT_BUS_TYPE = """
INSERT INTO public."Bus_Type" ("busType", "capacity") VALUES (%(busType)s, %(capacity)s)
RETURNING "busType", "capacity"
"""

# Input: busType (不變), capacity。Output: 更新後資料。
BACKSTAGE_UPDATE_BUS_TYPE = """
UPDATE public."Bus_Type" SET "capacity" = %(capacity)s WHERE "busType" = %(busType)s
RETURNING "busType", "capacity"
"""

# Input: busType。Output: 刪除的 busType；被車輛引用時由 RESTRICT FK 拒絕。
BACKSTAGE_DELETE_BUS_TYPE = 'DELETE FROM public."Bus_Type" WHERE "busType" = %(busType)s RETURNING "busType"'

# Input: keyword。Output: bId, busType, capacity；空 keyword 也作車輛選單。
BACKSTAGE_LIST_BUSES = """
SELECT b."bId", b."busType", bt."capacity"
FROM public."Bus" b JOIN public."Bus_Type" bt USING ("busType")
WHERE COALESCE(%(keyword)s::text, '') = ''
   OR b."bId" ILIKE '%%' || %(keyword)s || '%%'
   OR b."busType" ILIKE '%%' || %(keyword)s || '%%'
ORDER BY b."bId"
"""

# Input: bId, busType。Output: 新增後 bId, busType, capacity。
BACKSTAGE_INSERT_BUS = """
WITH changed AS (
    INSERT INTO public."Bus" ("bId", "busType") VALUES (%(bId)s, %(busType)s)
    RETURNING "bId", "busType"
)
SELECT c."bId", c."busType", bt."capacity" FROM changed c
JOIN public."Bus_Type" bt USING ("busType")
"""

# Input: bId (不變), busType。Output: 更新後 bId, busType, capacity。
BACKSTAGE_UPDATE_BUS = """
WITH changed AS (
    UPDATE public."Bus" SET "busType" = %(busType)s WHERE "bId" = %(bId)s
    RETURNING "bId", "busType"
)
SELECT c."bId", c."busType", bt."capacity" FROM changed c
JOIN public."Bus_Type" bt USING ("busType")
"""

# Input: bId。Output: 刪除的 bId；已派車則由 RESTRICT FK 拒絕。
BACKSTAGE_DELETE_BUS = 'DELETE FROM public."Bus" WHERE "bId" = %(bId)s RETURNING "bId"'

# --- SCHEDULE: 路線站序 ------------------------------------------------------

# Contain 與 Run 沒有相互參照的外鍵。API 在站序新增／修改／刪除、Trip 修改
# 或 Run upsert 的交易最前面執行此鎖，避免站序異動與寫入時間同時發生。
# 必須關閉 autocommit，完成檢查與異動後 commit／rollback；不要跨請求持鎖。
BACKSTAGE_LOCK_SCHEDULE = 'LOCK TABLE public."Trip", public."Contain", public."Run" IN SHARE ROW EXCLUSIVE MODE'

# Input: routeId, rDirection (DB enum: 去程/回程)。Output: 路線站點及站序。
BACKSTAGE_LIST_ROUTE_STOPS = """
SELECT c."routeId", c."stationId", s."sName", s."address",
       c."rDirection"::text AS "rDirection", c."stopSequence"
FROM public."Contain" c JOIN public."Station" s USING ("stationId")
WHERE c."routeId" = %(routeId)s AND c."rDirection"::text = %(rDirection)s
ORDER BY c."stopSequence"
"""

# Input: routeId, stationId, rDirection, stopSequence。Output: 新增後站序。
# 現有 DB 已有 UNIQUE(routeId,rDirection,stopSequence)、stopSequence > 0。
BACKSTAGE_INSERT_ROUTE_STOP = """
INSERT INTO public."Contain" ("routeId", "stationId", "rDirection", "stopSequence")
VALUES (%(routeId)s, %(stationId)s, %(rDirection)s::public.route_direction_enum, %(stopSequence)s)
RETURNING "routeId", "stationId", "rDirection"::text AS "rDirection", "stopSequence"
"""

# Input: routeId, old_stationId, old_rDirection, stationId, rDirection, stopSequence。
# Output: 更新後站序。已有對應 Run 時只允許調站序，不允許換站／方向。
# Run 沒有直接 FK 指向 Contain，API 必須共同協調與 Run/Trip 異動的交易鎖。
BACKSTAGE_UPDATE_ROUTE_STOP = """
UPDATE public."Contain" c
SET "stationId" = %(stationId)s,
    "rDirection" = %(rDirection)s::public.route_direction_enum,
    "stopSequence" = %(stopSequence)s
WHERE c."routeId" = %(routeId)s AND c."stationId" = %(old_stationId)s
  AND c."rDirection"::text = %(old_rDirection)s
  AND ((c."stationId" = %(stationId)s AND c."rDirection"::text = %(rDirection)s)
       OR NOT EXISTS (
           SELECT 1 FROM public."Run" run JOIN public."Trip" t USING ("tId")
           WHERE t."routeId" = c."routeId" AND t."tDirection"::text = c."rDirection"::text
             AND run."stationId" = c."stationId"
       ))
RETURNING c."routeId", c."stationId", c."rDirection"::text AS "rDirection", c."stopSequence"
"""

# Input: routeId, stationId, rDirection。Output: 刪除的站序鍵。
# 該方向班次仍有本站時間時回傳 0 筆，須先清理相關 Run。
BACKSTAGE_DELETE_ROUTE_STOP = """
DELETE FROM public."Contain" c
WHERE c."routeId" = %(routeId)s AND c."stationId" = %(stationId)s
  AND c."rDirection"::text = %(rDirection)s
  AND NOT EXISTS (
      SELECT 1 FROM public."Run" run JOIN public."Trip" t USING ("tId")
      WHERE t."routeId" = c."routeId" AND t."tDirection"::text = c."rDirection"::text
        AND run."stationId" = c."stationId"
  )
RETURNING c."routeId", c."stationId", c."rDirection"::text AS "rDirection"
"""

# --- SCHEDULE: 固定班次（同時作班次選單） -------------------------------------

# Input: routeId (None=全部), tDirection (None=全部), keyword。
# Output: tId, routeId, routeName, departureTime (HH:MM:SS), tDirection。
# 不使用前台查詢的「最近一次派車」，此處僅回傳固定 Trip。
BACKSTAGE_LIST_TRIPS = """
SELECT t."tId", t."routeId", r."routeName", t."departureTime"::text AS "departureTime",
       t."tDirection"::text AS "tDirection"
FROM public."Trip" t JOIN public."Route" r USING ("routeId")
WHERE (%(routeId)s::text IS NULL OR t."routeId" = %(routeId)s)
  AND (%(tDirection)s::text IS NULL OR t."tDirection"::text = %(tDirection)s)
  AND (COALESCE(%(keyword)s::text, '') = ''
       OR t."tId" ILIKE '%%' || %(keyword)s || '%%'
       OR t."departureTime"::text ILIKE '%%' || %(keyword)s || '%%')
ORDER BY t."routeId", t."tDirection", t."departureTime", t."tId"
"""

# Input: tId, routeId, departureTime (time), tDirection。Output: 新增後班次。
BACKSTAGE_INSERT_TRIP = """
INSERT INTO public."Trip" ("tId", "routeId", "departureTime", "tDirection")
VALUES (%(tId)s, %(routeId)s, %(departureTime)s::time, %(tDirection)s::public.trip_direction_enum)
RETURNING "tId", "routeId", "departureTime"::text AS "departureTime", "tDirection"::text AS "tDirection"
"""

# Input: tId (不變), routeId, departureTime, tDirection。Output: 更新後班次。
# 保守限制：存在 Run 或每日派車時不能改班表內容（相同值可原樣回傳）。
# 若要開放修改，需先共同確認歷史派車／各站時間的調整規則。
BACKSTAGE_UPDATE_TRIP = """
UPDATE public."Trip" t
SET "routeId" = %(routeId)s, "departureTime" = %(departureTime)s::time,
    "tDirection" = %(tDirection)s::public.trip_direction_enum
WHERE t."tId" = %(tId)s
  AND ((t."routeId" = %(routeId)s AND t."departureTime" = %(departureTime)s::time
        AND t."tDirection"::text = %(tDirection)s)
       OR (NOT EXISTS (SELECT 1 FROM public."Run" run WHERE run."tId" = t."tId")
           AND NOT EXISTS (SELECT 1 FROM public."Daily_Trip_Implement" d WHERE d."tId" = t."tId")))
RETURNING t."tId", t."routeId", t."departureTime"::text AS "departureTime", t."tDirection"::text AS "tDirection"
"""

# Input: tId。Output: 刪除的 tId；被 Run／派車引用時由 RESTRICT FK 拒絕。
BACKSTAGE_DELETE_TRIP = 'DELETE FROM public."Trip" WHERE "tId" = %(tId)s RETURNING "tId"'

# --- SCHEDULE: 各站預計到離站（整合在站序頁） ---------------------------------

# Input: tId。Output: 所有停靠站（含未填時間者），完整保留 timestamp。
BACKSTAGE_LIST_TRIP_STOP_TIMES = """
SELECT t."tId", c."stationId", s."sName", c."stopSequence",
       run."expArrivalTime", run."expDepartureTime"
FROM public."Trip" t
JOIN public."Contain" c ON c."routeId" = t."routeId"
 AND c."rDirection"::text = t."tDirection"::text
JOIN public."Station" s USING ("stationId")
LEFT JOIN public."Run" run ON run."tId" = t."tId" AND run."stationId" = c."stationId"
WHERE t."tId" = %(tId)s ORDER BY c."stopSequence"
"""

# Input: tId, stationId, expArrivalTime, expDepartureTime（完整 datetime/timestamp）。
# Output: 儲存後 tId, stationId, 兩個 timestamp；站不屬於班次則 0 筆。
# ON CONFLICT 同時處理新增／修改；DB CHECK 到站 <= 離站。
# 不把 HH:MM 任意補成今天；固定班表基準日期／跨日映射仍須與沛芳確認。
BACKSTAGE_UPSERT_TRIP_STOP_TIME = """
INSERT INTO public."Run" ("tId", "stationId", "expArrivalTime", "expDepartureTime")
SELECT t."tId", c."stationId", %(expArrivalTime)s::timestamp, %(expDepartureTime)s::timestamp
FROM public."Trip" t JOIN public."Contain" c ON c."routeId" = t."routeId"
 AND c."rDirection"::text = t."tDirection"::text
WHERE t."tId" = %(tId)s AND c."stationId" = %(stationId)s
ON CONFLICT ("tId", "stationId") DO UPDATE
SET "expArrivalTime" = EXCLUDED."expArrivalTime", "expDepartureTime" = EXCLUDED."expDepartureTime"
RETURNING "tId", "stationId", "expArrivalTime", "expDepartureTime"
"""

# Input: tId, stationId。Output: 刪除的時間設定鍵；不動 Contain／Station。
BACKSTAGE_DELETE_TRIP_STOP_TIME = """
DELETE FROM public."Run" WHERE "tId" = %(tId)s AND "stationId" = %(stationId)s
RETURNING "tId", "stationId"
"""

# --- SCHEDULE: 每日派車 ------------------------------------------------------

# Input: date (None=全部), keyword。Output: 完整派車列表，日期與時間不格式化丟失。
BACKSTAGE_LIST_DISPATCHES = """
SELECT d."date", d."tId", t."routeId", r."routeName", t."tDirection"::text AS "tDirection",
       t."departureTime"::text AS "departureTime", d."bId", d."driver", d."status"
FROM public."Daily_Trip_Implement" d
JOIN public."Trip" t USING ("tId") JOIN public."Route" r USING ("routeId")
WHERE (%(date)s::date IS NULL OR d."date" = %(date)s::date)
  AND (COALESCE(%(keyword)s::text, '') = ''
       OR d."tId" ILIKE '%%' || %(keyword)s || '%%'
       OR r."routeName" ILIKE '%%' || %(keyword)s || '%%'
       OR d."bId" ILIKE '%%' || %(keyword)s || '%%'
       OR d."driver" ILIKE '%%' || %(keyword)s || '%%'
       OR d."status" ILIKE '%%' || %(keyword)s || '%%')
ORDER BY d."date", t."departureTime", d."tId"
"""

# Input: tId, date, bId, driver, status。Output: 新增後派車原始欄位。
# 現有 CHECK 只允許 status='已完成'／'延誤抵達'，不是 UI 原本四種狀態！
# 後續需先與沛芳確認；這裡不修改 schema 或自行擴充合法值。
BACKSTAGE_INSERT_DISPATCH = """
INSERT INTO public."Daily_Trip_Implement" ("tId", "date", "bId", "driver", "status")
VALUES (%(tId)s, %(date)s::date, %(bId)s, %(driver)s, %(status)s)
RETURNING "tId", "date", "bId", "driver", "status"
"""

# Input: tId, date (兩鍵不變), bId, driver, status。Output: 更新後派車。
# tId／date 已被 Location_Log 引用時，不自行移動歷史日期或班次。
BACKSTAGE_UPDATE_DISPATCH = """
UPDATE public."Daily_Trip_Implement"
SET "bId" = %(bId)s, "driver" = %(driver)s, "status" = %(status)s
WHERE "tId" = %(tId)s AND "date" = %(date)s::date
RETURNING "tId", "date", "bId", "driver", "status"
"""

# Input: tId, date。Output: 刪除的兩鍵；有 Location_Log 則由 RESTRICT FK 拒絕。
# 不自動刪位置紀錄；若要允許，另行約定明確交易。
BACKSTAGE_DELETE_DISPATCH = """
DELETE FROM public."Daily_Trip_Implement" WHERE "tId" = %(tId)s AND "date" = %(date)s::date
RETURNING "tId", "date"
"""

# --- ANALYSIS: 一般使用者成長 ------------------------------------------------

# Input: 無。Output: userCount（只含一般會員，0 也回傳一列）。
BACKSTAGE_USER_COUNT = """
SELECT count(*) AS "userCount" FROM public."Member" WHERE "admin"::text = 'user'
"""

# Input: startDate, endDate（含首尾日，API 先驗證 startDate <= endDate）。
# Output: newUserCount。registerDatetime 實際型別 timestamp without time zone，
# 這裡按資料儲存的當地日期計算；請確認全組皆以 Asia/Taipei 寫入。
# 已刪除會員不再計入；不宣稱為永久註冊歷史。
BACKSTAGE_NEW_USER_COUNT = """
SELECT count(*) AS "newUserCount" FROM public."Member"
WHERE "admin"::text = 'user'
  AND "registerDatetime" >= %(startDate)s::date::timestamp
  AND "registerDatetime" < (%(endDate)s::date + 1)::timestamp
"""

# Input: startDate, endDate。Output: registrationDate (date), newUserCount。
# 補齊 0 人日期；日期區間請由 API 限制（目前 UI 最多 90 天）。
BACKSTAGE_DAILY_NEW_USERS = """
WITH days AS (
    SELECT %(startDate)s::date + n AS day
    FROM generate_series(0, %(endDate)s::date - %(startDate)s::date) AS n
), counts AS (
    SELECT "registerDatetime"::date AS day, count(*) AS n
    FROM public."Member" WHERE "admin"::text = 'user'
      AND "registerDatetime" >= %(startDate)s::date::timestamp
      AND "registerDatetime" < (%(endDate)s::date + 1)::timestamp
    GROUP BY "registerDatetime"::date
)
SELECT days.day AS "registrationDate", COALESCE(counts.n, 0) AS "newUserCount"
FROM days LEFT JOIN counts USING (day) ORDER BY days.day
"""

# --- ANALYSIS: 各路線去回程固定班次比較 --------------------------------------

# Input: 無；排序由 API/UI 處理。Output: routeId, routeName, outboundCount,
# inboundCount, totalCount。LEFT JOIN 保留 0 班次路線；count(tId) 不把空列當 1。
BACKSTAGE_ROUTE_TRIP_COMPARISON = """
SELECT r."routeId", r."routeName",
       count(t."tId") FILTER (WHERE t."tDirection"::text = '去程') AS "outboundCount",
       count(t."tId") FILTER (WHERE t."tDirection"::text = '回程') AS "inboundCount",
       count(t."tId") AS "totalCount"
FROM public."Route" r LEFT JOIN public."Trip" t USING ("routeId")
GROUP BY r."routeId", r."routeName" ORDER BY r."routeId"
"""

# --- ANALYSIS: 熱門收藏排行 --------------------------------------------------
# 現行需求為全部有效收藏，不擅自排除管理者。傳入 onlyUsers=True 可只計一般
# 會員，預設由 API 明確傳 False；是否改口徑請先確認。Member/Route/Station
# 均 INNER JOIN，忽略失效引用；limit=None=全部，否則 API 僅接受 5／10。

# Input: limit (None/5/10), onlyUsers (bool)。Output: routeId, routeName, favoriteCount。
BACKSTAGE_POPULAR_ROUTES = """
SELECT r."routeId", r."routeName", count(DISTINCT f."mId") AS "favoriteCount"
FROM public."Favorite_Route" f JOIN public."Route" r USING ("routeId")
JOIN public."Member" m USING ("mId")
WHERE NOT %(onlyUsers)s::boolean OR m."admin"::text = 'user'
GROUP BY r."routeId", r."routeName"
ORDER BY "favoriteCount" DESC, r."routeId" LIMIT %(limit)s
"""

# Input: limit (None/5/10), onlyUsers (bool)。Output: stationId, sName, favoriteCount。
BACKSTAGE_POPULAR_STATIONS = """
SELECT s."stationId", s."sName", count(DISTINCT f."mId") AS "favoriteCount"
FROM public."Favorite_Station" f JOIN public."Station" s USING ("stationId")
JOIN public."Member" m USING ("mId")
WHERE NOT %(onlyUsers)s::boolean OR m."admin"::text = 'user'
GROUP BY s."stationId", s."sName"
ORDER BY "favoriteCount" DESC, s."stationId" LIMIT %(limit)s
"""

# --- 站序頁 API 的單筆識別查詢（不異動資料） -------------------------------
# Input routeId:str。Output routeId, routeName, origin, destination；0 筆為不存在。
BACKSTAGE_GET_ROUTE = """
SELECT "routeId", "routeName", "origin", "destination"
FROM public."Route" WHERE "routeId" = %(routeId)s
"""
# Input routeId, stationId, rDirection（去程/回程）。Output 完整 Contain；0 筆不存在。
# 寫入前須先取得 BACKSTAGE_LOCK_SCHEDULE，在同一交易判斷 404 與受 Run 限制的 409。
BACKSTAGE_GET_ROUTE_STOP = """
SELECT "routeId", "stationId", "rDirection"::text AS "rDirection", "stopSequence"
FROM public."Contain" WHERE "routeId" = %(routeId)s AND "stationId" = %(stationId)s
AND "rDirection"::text = %(rDirection)s
"""

# --- 預定班次 API：存在性與交易協調 ---------------------------------------
# Input tId:str；Output 原 Trip（時間字串 HH:MM:SS，可含小數秒）；0 筆代表不存在。
BACKSTAGE_GET_TRIP = """
SELECT "tId", "routeId", "departureTime"::text AS "departureTime",
       "tDirection"::text AS "tDirection"
FROM public."Trip" WHERE "tId" = %(tId)s
"""
# 無參數／無資料回傳。寫入交易最先取得，與站序交易同序鎖 Trip/Contain/Run；
# 同時協調每日派車，避免檢查無引用後有新派車並行寫入。需 commit/rollback 釋放。
BACKSTAGE_LOCK_TRIPS = 'LOCK TABLE public."Trip", public."Contain", public."Run", public."Daily_Trip_Implement" IN SHARE ROW EXCLUSIVE MODE'
