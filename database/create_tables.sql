-- 高雄公車專案：在空白資料庫執行。
BEGIN;

-- 文件指定 enum，並以「去程」「回程」為例；採用兩種獨立型別。
CREATE TYPE route_direction_enum AS ENUM ('去程', '回程');
CREATE TYPE trip_direction_enum AS ENUM ('去程', '回程');

CREATE TYPE member_admin_enum AS ENUM ('user', 'admin');

CREATE TABLE "Member" (
    "mId" INTEGER PRIMARY KEY,
    "userName" VARCHAR(50) NOT NULL CHECK (btrim("userName") <> ''),
    "email" VARCHAR(100) NOT NULL UNIQUE,
    "password" VARCHAR(255) NOT NULL CHECK (length("password") >= 8),
    "registerDatetime" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "admin" member_admin_enum NOT NULL DEFAULT 'user'
);

CREATE TABLE "Route" (
    "routeId" VARCHAR(50) PRIMARY KEY,
    "routeName" VARCHAR(100) NOT NULL,
    "origin" VARCHAR(100) NOT NULL,
    "destination" VARCHAR(100) NOT NULL
);

CREATE TABLE "Station" (
    "stationId" VARCHAR(50) PRIMARY KEY,
    "sName" VARCHAR(100) NOT NULL,
    "address" VARCHAR(255) NOT NULL,
    "sLatitude" DECIMAL(10,7) NOT NULL CHECK ("sLatitude" BETWEEN -90 AND 90),
    "sLongitude" DECIMAL(10,7) NOT NULL CHECK ("sLongitude" BETWEEN -180 AND 180)
);

CREATE TABLE "Bus_Type" (
    "busType" VARCHAR(50) PRIMARY KEY,
    "capacity" INTEGER NOT NULL CHECK ("capacity" > 0)
);

CREATE TABLE "Bus" (
    "bId" VARCHAR(50) PRIMARY KEY,
    "busType" VARCHAR(50) NOT NULL,
    FOREIGN KEY ("busType") REFERENCES "Bus_Type"("busType") ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE "Trip" (
    "tId" VARCHAR(50) PRIMARY KEY,
    "routeId" VARCHAR(50) NOT NULL,
    "departureTime" TIME NOT NULL,
    "tDirection" trip_direction_enum NOT NULL,
    FOREIGN KEY ("routeId") REFERENCES "Route"("routeId") ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE "Favorite_Route" (
    "mId" INTEGER,
    "routeId" VARCHAR(50) NOT NULL,
    PRIMARY KEY ("mId", "routeId"),
    FOREIGN KEY ("mId") REFERENCES "Member"("mId") ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY ("routeId") REFERENCES "Route"("routeId") ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "Favorite_Station" (
    "mId" INTEGER,
    "stationId" VARCHAR(50),
    PRIMARY KEY ("mId", "stationId"),
    FOREIGN KEY ("mId") REFERENCES "Member"("mId") ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY ("stationId") REFERENCES "Station"("stationId") ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "Contain" (
    "routeId" VARCHAR(50) NOT NULL,
    "stationId" VARCHAR(50),
    "rDirection" route_direction_enum,
    "stopSequence" INTEGER NOT NULL CHECK ("stopSequence" > 0),
    UNIQUE ("routeId", "rDirection", "stopSequence"),
    PRIMARY KEY ("routeId", "stationId", "rDirection"),
    FOREIGN KEY ("routeId") REFERENCES "Route"("routeId") ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY ("stationId") REFERENCES "Station"("stationId") ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE "Daily_Trip_Implement" (
    "tId" VARCHAR(50),
    "date" DATE,
    "driver" VARCHAR(100) NOT NULL,
    "status" VARCHAR(30) NOT NULL CHECK ("status" IN ('已完成', '延誤抵達')),
    "bId" VARCHAR(50) NOT NULL,
    PRIMARY KEY ("tId", "date"),
    FOREIGN KEY ("tId") REFERENCES "Trip"("tId") ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY ("bId") REFERENCES "Bus"("bId") ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE "Location_Log" (
    "tId" VARCHAR(50),
    "date" DATE,
    "recordDatetime" TIMESTAMP,
    "lLatitude" DECIMAL(10,7) NOT NULL CHECK ("lLatitude" BETWEEN -90 AND 90),
    "lLongitude" DECIMAL(10,7) NOT NULL CHECK ("lLongitude" BETWEEN -180 AND 180),
    PRIMARY KEY ("tId", "date", "recordDatetime"),
    CHECK ("recordDatetime"::date = "date"),
    FOREIGN KEY ("tId", "date") REFERENCES "Daily_Trip_Implement"("tId", "date") ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE "Run" (
    "tId" VARCHAR(50),
    "stationId" VARCHAR(50),
    "expDepartureTime" TIMESTAMP NOT NULL,
    "expArrivalTime" TIMESTAMP NOT NULL,
    CHECK ("expArrivalTime" <= "expDepartureTime"),
    PRIMARY KEY ("tId", "stationId"),
    FOREIGN KEY ("tId") REFERENCES "Trip"("tId") ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY ("stationId") REFERENCES "Station"("stationId") ON DELETE RESTRICT ON UPDATE CASCADE
);

COMMIT;
