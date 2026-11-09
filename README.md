# 公車追蹤系統（2026-DB-Project01-BusTrackingSystem）

資料庫系統 專案一。一套使用 Flask 開發的高雄公車查詢系統，後端使用 PostgreSQL 資料庫，提供路線查詢、班次資訊、即時公車位置，以及管理者後台。

> 協作流程（分支、commit、PR）請看 [CONTRIBUTING.md](CONTRIBUTING.md)，**開始寫程式前請先讀完**。

## 功能

**前台（乘客）**
- 首頁：搜尋公車路線、依目前位置查詢附近站牌
- 路線詳細資訊：去返程站序、今日班次、地圖與即時公車位置（每 15 秒更新）
- 收藏：收藏路線與站牌（需登入）
- 會員：註冊、登入、修改個人資料與密碼

**後台（管理者，需以管理者帳號登入）**
- 營運總覽：路線、站點、車輛、班次總數
- CMS 資料管理：會員、路線、站點、車型、車輛的新增、查詢、修改、刪除
- 班表調度：路線站序與到離站時間、預定班次（去返程）、每日派車與司機安排
- 營運統計分析：會員註冊成長、熱門收藏路線與站點排行、各路線班次比較

## 技術

| 層級 | 工具 |
|---|---|
| 後端 | Python 3.10、Flask 2.1（Blueprint 架構）、psycopg2、python-dotenv |
| 資料庫 | PostgreSQL（12 張資料表，原生 SQL，未使用 ORM） |
| 前端 | Jinja2、Bootstrap 5、Bootstrap Icons、Leaflet + OpenStreetMap、原生 JavaScript（fetch） |
| 即時位置 | Flask 啟動時以背景執行緒模擬公車 GPS，每 15 秒寫入 `Location_Log` |

## 專案結構

```
2026-DB-Project01-BusTrackingSystem/
├── app.py                      # 程式進入點：註冊 Blueprint、啟動即時位置模擬
├── link.py                     # 資料庫連線：get_connection()；可直接執行測試連線
├── requirements.txt            # Python 套件
├── .env.example                # 連線資訊範本（複製成 .env 使用）
├── api/                        # API Blueprint（/api），回傳 JSON
│   ├── api.py                  #   註冊所有 API 路由
│   ├── sql.py                  #   全專案共用的 SQL 語句
│   ├── admin_auth.py           #   後台管理者登入與權限驗證
│   └── routes.py、stations.py、members.py、buses.py、bus_types.py、
│       trips.py、schedule_stops.py、dispatch.py、overview.py、analysis.py
│                               #   後台各管理頁面的 CRUD 與統計 API
├── frontstage/                 # 前台 Blueprint（/）
│   ├── templates/              #   前台頁面
│   └── views/frontstage.py     #   前台路由
├── backstage/                  # 後台 Blueprint（/backstage）
│   ├── templates/backstage/    #   後台頁面（一頁一個模板）
│   └── views/backstage.py      #   後台路由與登入驗證
├── database/
│   ├── create_tables.sql       #   建立 12 張資料表
│   ├── bus_data.py             #   產生模擬資料、匯入 CSV、檢查筆數
│   ├── location_replay.py      #   即時位置模擬（由 app.py 自動啟動）
│   └── csv_data/               #   12 張資料表的模擬資料
├── static/
│   ├── css/                    #   前台與後台樣式
│   └── js/                     #   main.js（前台）、backstage/（後台各頁）
└── templates/base.html         # 共用版型，所有頁面都繼承它
```

## 安裝

### 0. 進入終端機

Windows 請開啟 **Anaconda Prompt**；macOS 請開啟「終端機」。

### 1. 取得原始碼

```bash
git clone https://github.com/homer-105216/2026-DB-Project01-BusTrackingSystem.git
cd 2026-DB-Project01-BusTrackingSystem
```

### 2. 建立環境

請先安裝 [Anaconda](https://www.anaconda.com/download)。

```bash
# Python 請用 3.10，3.11 以上會有套件版本衝突
conda create -n db-bus python=3.10

# 啟動環境（每次開新的終端機都要執行）
conda activate db-bus
```

啟動後，終端機開頭會出現 `(db-bus)`。

### 3. 安裝套件

```bash
# 請確認已啟動 conda 環境，且目前位置在專案資料夾
pip install -r requirements.txt
```

### 4. 設定連線資訊

把 `.env.example` 複製一份，改名為 `.env`：

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

打開 `.env`，填入組別的 PostgreSQL 連線資訊。

> 連線資訊在網路大學：分組學習 ➔ 專案分組 ➔ 進入小組 ➔ 討論 ➔ 組內討論 ➔ 資料庫連線資訊

```
DB_USER=...
DB_PASSWORD=...
DB_NAME=...
DB_HOST=...
DB_PORT=5432
SECRET_KEY=...   # 任意一串隨機字串，用於登入狀態加密
```

⚠️ `.env` 含有帳號密碼，已列在 `.gitignore`，**絕對不要 commit**。

### 5. 測試資料庫連線

```bash
python link.py
```

看到 `連線成功：PostgreSQL ...` 代表設定正確。

### 6. 建立資料表與匯入資料

> **組員共用的資料庫已經建好資料表並匯入資料，直接跳到步驟 7。**
> 只有在全新、空白的資料庫上重建時，才需要做這一步。

`bus_data.py` 使用 PostgreSQL 的標準環境變數（`PG` 開頭），**不會讀取 `.env`**，請先在終端機設定：

```bash
# Windows（PowerShell）
$env:PGHOST="資料庫主機"; $env:PGPORT="5432"; $env:PGDATABASE="資料庫名稱"; $env:PGUSER="帳號"

# Windows（Anaconda Prompt / 命令提示字元）
set PGHOST=資料庫主機
set PGPORT=5432
set PGDATABASE=資料庫名稱
set PGUSER=帳號

# macOS / Linux
export PGHOST=資料庫主機 PGPORT=5432 PGDATABASE=資料庫名稱 PGUSER=帳號
```

接著執行（會詢問資料庫密碼）：

```bash
# 在空白資料庫上建立 12 張資料表，並匯入 database/csv_data/ 的資料
python database/bus_data.py init-import

# 確認各資料表的筆數
python database/bus_data.py check
```

| 指令 | 用途 |
|---|---|
| `init-import` | 建表＋匯入。資料庫必須是空的，否則會中止 |
| `import` | 資料表已存在且是空的，只匯入資料 |
| `check` | 顯示 12 張資料表各有幾筆資料 |
| `generate` | ⚠️ 重新隨機產生 CSV，會**覆蓋** `csv_data/` 現有的資料，一般不需要執行 |

匯入過程使用交易：任何一步失敗都會整批 ROLLBACK，不會只匯入一半。若資料表已有資料，程式會安全中止，不會清空或重複匯入。

### 7. 啟動程式

```bash
python app.py
```

打開瀏覽器：

| 網址 | 內容 |
|---|---|
| http://127.0.0.1:5000/ | 前台首頁 |
| http://127.0.0.1:5000/route/R001 | 路線詳細範例（紅28，有即時公車） |
| http://127.0.0.1:5000/login | 會員登入 |
| http://127.0.0.1:5000/backstage/login | 後台管理者登入 |
| http://127.0.0.1:5000/api/health | 資料庫連線狀態（JSON） |

按 `Ctrl + C` 停止程式。

**即時位置**：`python app.py` 啟動後，背景會每 15 秒更新班次 `T0001`（紅28 去程）在 `Location_Log` 的位置。打開 `/route/R001` 就能看到公車在地圖上移動。

**後台登入**：只有 `Member` 資料表中 `admin` 欄位為 `admin` 的會員可以登入後台，一般會員會被拒絕。Demo 用的帳號密碼請見專案報告。

## 對外開放（ngrok）

需要讓其他人從網路連進來時（例如助教批改），可以用 [ngrok](https://ngrok.com/) 建立通道。

1. 先照上面的步驟執行 `python app.py`。
2. 另開一個終端機，在專案資料夾執行：

```bash
ngrok http 127.0.0.1:5000 --traffic-policy-file=tp.yml
```

`tp.yml` 是 ngrok 的設定檔，用來加上 basic auth（訪客要先輸入帳號密碼）。它含有帳密，已列在 `.gitignore`，不會出現在 repo 裡，需要時請向負責環境的組員索取，或自行建立：

```yaml
on_http_request:
  - actions:
      - type: basic-auth
        config:
          credentials:
            - "帳號:至少8碼的密碼"
```

## 常見問題

**`ModuleNotFoundError: No module named 'flask'`**
沒有啟動 conda 環境。先執行 `conda activate db-bus`，再重新執行。

**`.env 缺少連線設定：...`**
`.env` 不存在，或錯誤訊息列出的欄位沒有填。

**連線逾時（timeout expired）**
檢查 `DB_HOST`、`DB_PORT` 是否正確，以及目前的網路能否連到學校的資料庫伺服器。

**打開後台一直被導回登入頁**
後台需要管理者帳號。請確認登入的會員在 `Member` 資料表的 `admin` 欄位是 `admin`。

**地圖上的公車沒有移動**
- 即時位置只模擬班次 `T0001`，請查看紅28（`/route/R001`）去程。
- 必須用 `python app.py` 啟動，模擬才會執行；請看執行 `app.py` 的終端機是否出現位置更新的錯誤訊息。
- 頁面每 15 秒才更新一次，請稍等。

**`請先設定 PGDATABASE 為你要操作的資料庫名稱`**
執行 `bus_data.py` 前沒有設定 `PG` 開頭的環境變數，請見步驟 6。

**`Address already in use`（5000 port 被佔用）**
有另一個程式正在執行。先關掉其他終端機裡的 `python app.py`；找不到的話：

```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS / Linux
lsof -i :5000
kill -9 <PID>
```
