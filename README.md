# 公車追蹤系統（2026-DB-Project01-BusTrackingSystem）

資料庫系統 專案一。一套使用 Flask 開發的公車查詢系統，後端使用 PostgreSQL 資料庫，提供路線查詢、班次資訊與即時公車位置。

> 協作流程（分支、commit、PR）請看 [CONTRIBUTING.md](CONTRIBUTING.md)，**開始寫程式前請先讀完**。

## 功能規劃

**前台（乘客）**
- 首頁：瀏覽附近公車路線、搜尋路線
- 公車詳細資訊：路線站點、班次、即時位置
- 收藏：查看自己收藏的路線／站點（需登入）
- 登入、註冊、使用者設定

**後台（管理者）**
- CMS：新增、修改、刪除路線、站點、車型
- 班表設定：路線發車時間表、配班（司機、車輛）
- 統計分析

## 技術

- Python 3.10、Flask（Blueprint 架構）
- PostgreSQL（psycopg2）
- python-dotenv 管理連線資訊

## 專案結構

```
2026-DB-Project01-BusTrackingSystem/
├── app.py                  # 程式進入點，註冊所有 Blueprint
├── link.py                 # 資料庫連線：get_connection()
├── requirements.txt        # Python 套件
├── .env.example            # 連線資訊範本（複製成 .env 使用）
├── api/                    # API Blueprint（/api），回傳 JSON；SQL 查詢依實體分檔放這裡
├── frontstage/             # 前台 Blueprint（/）
│   ├── templates/frontstage/   # 前台頁面
│   └── views/                  # 前台路由
├── backstage/              # 後台 Blueprint（/backstage）
│   ├── templates/backstage/    # 後台頁面
│   └── views/                  # 後台路由
├── database/               # 建表、假資料等 SQL 檔
├── static/                 # CSS、圖片
└── templates/base.html     # 共用版型，所有頁面都繼承它
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
DB_HOST=...
DB_PORT=...
DB_NAME=...
SECRET_KEY=...   # 任意一串隨機字串
```

⚠️ `.env` 含有帳號密碼，已列在 `.gitignore`，**絕對不要 commit**。

### 5. 測試資料庫連線

```bash
python link.py
```

看到 `連線成功：PostgreSQL ...` 代表設定正確。

### 6. 啟動程式

```bash
python app.py
```

打開瀏覽器：

| 網址 | 內容 |
|---|---|
| http://127.0.0.1:5000/ | 前台首頁 |
| http://127.0.0.1:5000/backstage/ | 後台首頁 |
| http://127.0.0.1:5000/api/health | 資料庫連線狀態（JSON） |

按 `Ctrl + C` 停止程式。

## 常見問題

**`ModuleNotFoundError: No module named 'flask'`**
沒有啟動 conda 環境。先執行 `conda activate db-bus`，再重新執行。

**`.env 缺少連線設定：...`**
`.env` 不存在，或錯誤訊息列出的欄位沒有填。

**連線逾時（timeout expired）**
檢查 `DB_HOST`、`DB_PORT` 是否正確，以及目前的網路能否連到學校的資料庫伺服器（部分校外網路需要 VPN）。

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
