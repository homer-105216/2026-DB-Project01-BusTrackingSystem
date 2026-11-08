#!/usr/bin/env python3
"""Generate and safely import synthetic Kaohsiung bus data into the EXISTING 12-table schema."""
import argparse
import csv
import os
from getpass import getpass
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

if __name__ == '__main__' and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import sql as queries

SEED = 20261103
START_DATE = date(2026, 10, 28)
DAYS = 5
OUT = Path(__file__).resolve().parent / 'csv_data'
SCHEMA = {
    'Member': ['mId','userName','email','password','registerDatetime','admin'],
    'Route': ['routeId','routeName','origin','destination'],
    'Station': ['stationId','sName','address','sLatitude','sLongitude'],
    'Bus_Type': ['busType','capacity'],
    'Bus': ['bId','busType'],
    'Trip': ['tId','routeId','departureTime','tDirection'],
    'Favorite_Route': ['mId','routeId'],
    'Favorite_Station': ['mId','stationId'],
    'Contain': ['routeId','stationId','rDirection','stopSequence'],
    'Daily_Trip_Implement': ['tId','date','driver','status','bId'],
    'Location_Log': ['tId','date','recordDatetime','lLatitude','lLongitude'],
    'Run': ['tId','stationId','expDepartureTime','expArrivalTime'],
}
ORDER = list(SCHEMA)
# Approximate reference locations only: NOT verified station coordinates.
ANCHORS = [
 ('高雄車站',22.6397,120.3026),('美麗島',22.6313,120.3015),
 ('中央公園',22.6245,120.3012),('三多商圈',22.6136,120.3047),
 ('文化中心',22.6277,120.3179),('凹子底',22.6574,120.3030),
 ('巨蛋',22.6660,120.3032),('左營高鐵站',22.6878,120.3095),
 ('蓮池潭',22.6837,120.2957),('駁二藝術特區',22.6204,120.2816),
 ('西子灣',22.6222,120.2646),('哈瑪星',22.6210,120.2741),
 ('夢時代',22.5954,120.3068),('瑞豐夜市',22.6664,120.2993),
 ('衛武營',22.6252,120.3416),('鳳山車站',22.6315,120.3578),
 ('五甲',22.5968,120.3373),('小港機場',22.5704,120.3440),
 ('草衙',22.5822,120.3290),('楠梓車站',22.7260,120.3245),
 ('後勁',22.7223,120.3162),('大東文化藝術中心',22.6257,120.3634),
 ('高雄市立美術館',22.6565,120.2866),('科工館',22.6404,120.3226),
 ('前鎮之星',22.6046,120.3128),('愛河之心',22.6516,120.3015),
 ]
ADDRESS_ROADS = ['高雄市三民區建國二路', '高雄市新興區中山一路', '高雄市前金區中華三路', '高雄市苓雅區三多四路', '高雄市苓雅區五福一路', '高雄市鼓山區博愛二路', '高雄市左營區博愛二路', '高雄市左營區高鐵路', '高雄市左營區蓮潭路', '高雄市鹽埕區大勇路', '高雄市鼓山區蓮海路', '高雄市鼓山區臨海二路', '高雄市前鎮區中華五路', '高雄市左營區裕誠路', '高雄市鳳山區三多一路', '高雄市鳳山區曹公路', '高雄市鳳山區五甲二路', '高雄市小港區中山四路', '高雄市前鎮區翠亨南路', '高雄市楠梓區建楠路', '高雄市楠梓區加昌路', '高雄市鳳山區光遠路', '高雄市鼓山區美術館路', '高雄市三民區九如一路', '高雄市前鎮區中山三路', '高雄市鼓山區博愛一路']
ROUTE_LABELS = ['紅28','橘12','60','168','紅30','橘7','88','99','205','301','紅10','橘20']
DRIVERS = ['陳志明','林建宏','黃俊傑','張家豪','李宗翰','王柏宇','吳承恩','劉冠廷','蔡明哲','許文豪','鄭宇翔','謝佳穎','郭怡君','何雅婷','蘇佩珊','楊子涵']

def fmt_dt(dt): return dt.strftime('%Y-%m-%d %H:%M:%S')
def fmt_coord(x): return f'{x:.7f}'

def write_csv(name, rows):
    path = OUT / (name + '.csv')
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(SCHEMA[name])
        writer.writerows(rows)
    return len(rows)

def generate():
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    data = {k: [] for k in ORDER}
    stations = {}
    # 65 synthetic stops clustered around recognizable real Kaohsiung landmarks.
    for i in range(65):
        name, lat, lon = ANCHORS[i % len(ANCHORS)]
        variant = i // len(ANCHORS)
        if variant == 0:
            label = name
            lat2, lon2 = lat, lon
        else:
            label = name + f'（{["東側", "西側"][variant - 1]}）'
            lat2 = lat + rng.uniform(-0.005, 0.005)
            lon2 = lon + rng.uniform(-0.005, 0.005)
        sid = f'S{i+1:03d}'
        stations[sid] = (lat2,lon2)
        data['Station'].append((sid,label,f'{ADDRESS_ROADS[i % len(ANCHORS)]}{30 + i * 3}號',fmt_coord(lat2),fmt_coord(lon2)))
    station_ids = list(stations)
    routes = {}
    for i, label in enumerate(ROUTE_LABELS):
        rid = f'R{i+1:03d}'
        # 9 stops, unique within each direction; adjacent routes overlap stops.
        ids = [station_ids[(i*5+j) % len(station_ids)] for j in range(9)]
        routes[rid] = ids
        origin = data['Station'][int(ids[0][1:])-1][1]
        dest = data['Station'][int(ids[-1][1:])-1][1]
        data['Route'].append((rid,label,origin,dest))
        for direction, seq in [('去程',ids),('回程',list(reversed(ids)))]:
            for idx,sid in enumerate(seq,1):
                data['Contain'].append((rid,sid,direction,idx))
    for typ, cap in [('一般公車',40),('低地板公車',35),('電動公車',35),('中型巴士',20)]:
        data['Bus_Type'].append((typ,cap))
    buses = []
    for i in range(24):
        bid = f'KAA-{1001+i}'
        buses.append(bid)
        data['Bus'].append((bid,data['Bus_Type'][i%4][0]))
    for i in range(40):
        mid = i+1
        words = ('Harbor', 'Lotus', 'Metro', 'Sunset', 'Pier', 'Breeze', 'River', 'Skyline')
        pw = f'{words[i % len(words)]}Bus!{26 + mid}'
        reg = datetime(2026, 7, 1) + timedelta(days=i*2, hours=i%10)
        data['Member'].append((mid,f'{DRIVERS[i % len(DRIVERS)]}{mid:02d}',f'kh.{mid:03d}@example.invalid',pw,fmt_dt(reg),'admin' if mid == 1 else 'user'))
    for mid in range(1,41):
        for rid in rng.sample(list(routes),rng.randint(1,3)):
            data['Favorite_Route'].append((mid,rid))
        for sid in rng.sample(station_ids,rng.randint(1,3)):
            data['Favorite_Station'].append((mid,sid))
    # 120 daily schedules (12 routes x 2 directions x 5 departures).
    trips = []
    for ri,rid in enumerate(routes):
        for di,direction in enumerate(['去程','回程']):
            ids = routes[rid] if di == 0 else list(reversed(routes[rid]))
            for k in range(5):
                # 06:00 - 19:15 departures, staggered across route/direction.
                dep_min = 6*60 + k*180 + (ri%4)*10 + di*15
                tid = f'T{len(trips)+1:04d}'
                dep_dt = datetime.combine(START_DATE,datetime.min.time())+timedelta(minutes=dep_min)
                data['Trip'].append((tid,rid,dep_dt.strftime('%H:%M:%S'),direction))
                trips.append((tid,rid,direction,ids,dep_min))
                for j,sid in enumerate(ids):
                    arr = dep_dt + timedelta(minutes=j*5)
                    leave = arr + timedelta(minutes=1)
                    data['Run'].append((tid,sid,fmt_dt(leave),fmt_dt(arr)))
    # Allocate vehicles and drivers without overlapping assignments on any day.
    drivers = DRIVERS + '邱正宏 曾國源 廖文彬 賴信宏 方啟文 葉家銘 洪志賢 彭美玲 蕭玉芬 江俊雄 高淑惠 朱柏勳 周世傑 簡麗華'.split()
    # Each trip takes 41 min (9 stops x 5 min), plus a 19 min turnaround buffer.
    for day_idx in range(DAYS):
        d = START_DATE+timedelta(days=day_idx)
        busy_until = {b:0 for b in buses}
        driver_until = {n:0 for n in drivers}
        for tid,rid,direction,ids,dep_min in sorted(trips,key=lambda x:x[4]):
            available_buses = [b for b in buses if busy_until[b] <= dep_min]
            available_drivers = [n for n in drivers if driver_until[n] <= dep_min]
            if not available_buses or not available_drivers:
                raise RuntimeError('Insufficient vehicle/driver capacity; adjust scheduling')
            bid = min(available_buses,key=lambda b:(busy_until[b],b))
            driver = min(available_drivers,key=lambda n:(driver_until[n],n))
            busy_until[bid] = dep_min + 60
            driver_until[driver] = dep_min + 60
            data['Daily_Trip_Implement'].append((tid,d.isoformat(),driver,'已完成',bid))
            # 5 timestamped location observations on actual trip date near route stops.
            start_dt = datetime.combine(d,datetime.min.time())+timedelta(minutes=dep_min)
            for idx in range(5):
                progress = idx*2 # stop indices 0,2,4,6,8
                sid = ids[progress]
                lat,lon = stations[sid]
                # Very small positional jitter; location stays close to route stop.
                lat += rng.uniform(-0.00008,0.00008)
                lon += rng.uniform(-0.00008,0.00008)
                ts = start_dt+timedelta(minutes=progress*5)
                data['Location_Log'].append((tid,d.isoformat(),fmt_dt(ts),fmt_coord(lat),fmt_coord(lon)))
    counts = {name:write_csv(name,data[name]) for name in ORDER}
    print('已產生 CSV：',OUT)
    for name in ORDER: print(f'  {name:24s} {counts[name]:>5} 筆')
    print('總計：',sum(counts.values()),'筆')
    return counts

def connect():
    try: import psycopg2
    except ImportError: raise SystemExit('缺少 psycopg2-binary，請先執行：pip install psycopg2-binary')
    database = os.getenv('PGDATABASE')
    if not database:
        raise SystemExit('請先設定 PGDATABASE 為你要操作的資料庫名稱')
    params = dict(host=os.getenv('PGHOST', 'localhost'),
                  port=os.getenv('PGPORT', '5432'), dbname=database,
                  user=os.getenv('PGUSER', 'postgres'))
    try:
        return psycopg2.connect(**params)
    except psycopg2.OperationalError as exc:
        if 'no password supplied' not in str(exc):
            raise
        return psycopg2.connect(**params, password=getpass('PostgreSQL 登入密碼：'))


def q(s): return '"'+s.replace('"','""')+'"'

def import_data(initialize=False):
    for name in ORDER:
        if not (OUT/(name+'.csv')).exists(): raise SystemExit(f'找不到 {name}.csv，請先 --generate')
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(queries.PUBLIC_SEARCH_PATH)
            if initialize:
                cur.execute(queries.HAS_PUBLIC_RELATIONS)
                if cur.fetchone()[0]:
                    raise RuntimeError('初始化需要空白資料庫，請改用新資料庫')
                sql = Path(__file__).with_name('create_tables.sql').read_text(encoding='utf-8-sig')
                ddl = sql.split('BEGIN;', 1)[1].rsplit('COMMIT;', 1)[0]
                cur.execute(ddl)
            tables = ', '.join('public.' + q(name) for name in ORDER)
            cur.execute(queries.LOCK_IMPORT_TABLES.format(tables=tables))
            # Check exact columns and existence; reject any unexpected schema differences.
            for name, expected in SCHEMA.items():
                cur.execute(queries.LIST_TABLE_COLUMNS,('public',name))
                found = [x[0] for x in cur.fetchall()]
                if found != expected: raise RuntimeError(f'{name} 欄位不符合原始規格：{found} != {expected}')
                cur.execute(queries.COUNT_TABLE_ROWS.format(table=q(name)))
                count = cur.fetchone()[0]
                if count: raise RuntimeError(f'安全中止：{name} 已有 {count} 筆資料，不會清空或重複匯入')
            for name, cols in SCHEMA.items():
                path = OUT/(name+'.csv')
                with path.open('r',encoding='utf-8-sig',newline='') as f:
                    cur.copy_expert(queries.COPY_TABLE_ROWS.format(table=q(name), columns=", ".join(map(q, cols))),f)
                print('匯入：',name)
        conn.commit()
        print('全部匯入成功，已 COMMIT。')
    except Exception:
        conn.rollback()
        print('匯入失敗，已 ROLLBACK：資料不會只匯入一半。')
        raise
    finally: conn.close()

def check():
    conn = connect()
    try:
        with conn.cursor() as cur:
            for name in ORDER:
                cur.execute(queries.COUNT_TABLE_ROWS.format(table=q(name)))
                print(f'{name:24s} {cur.fetchone()[0]:>5} 筆')
    finally: conn.close()

def main():
    p=argparse.ArgumentParser(description='高雄公車 12 表模擬資料：只新增資料，不修改資料表')
    p.add_argument('action',choices=['generate','import','all','check','init-import'])
    a=p.parse_args().action
    if a in ('generate','all'):generate()
    if a in ('import','all'):import_data()
    if a == 'init-import': import_data(initialize=True)
    if a=='check':check()
if __name__=='__main__': main()
