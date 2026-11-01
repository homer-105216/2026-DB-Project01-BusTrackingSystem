# 協作流程

這份文件說明我們怎麼用 GitHub 一起開發。規則只有一條核心：**不要直接改 `main`，所有修改都透過分支和 Pull Request（PR）合併。**

---

## 1. 第一次設定（每人做一次）

1. 接受 GitHub 寄來的 collaborator 邀請。
2. 照 [README](README.md) 的「安裝」完成 clone、建立環境、設定 `.env`，確認 `python link.py` 連線成功。
3. 設定 Git 的名字和信箱（要跟 GitHub 帳號一致，commit 才會顯示你的頭像）：

```bash
git config --global user.name "你的 GitHub 名稱"
git config --global user.email "你的 GitHub 信箱"
```

---

## 2. 分工與負責的資料夾

各自主要改自己負責的資料夾，可以大幅減少衝突。

| 工作 | 內容 | 主要修改的位置 |
|---|---|---|
| 1. 資料庫 | 建表、查詢語法、假資料 | `database/`、`api/` 裡的 SQL 檔 |
| 2. 前端介面 | 頁面、輸入驗證、儀表板 | `frontstage/templates/`、`backstage/templates/`、`static/` |
| 3. 前後端整合 | API、CRUD 邏輯、呼叫 SQL | `frontstage/views/`、`backstage/views/`、`api/` |
| 4. 環境、文件、測試 | GitHub、連線、文件、測試 | `app.py`、`link.py`、`README.md`、`CONTRIBUTING.md` |

需要改別人負責的檔案時，先在群組說一聲。

---

## 3. 每次開發的流程

### 步驟 1：更新 main

開始新工作前，先讓本機的 `main` 跟 GitHub 同步：

```bash
git switch main
git pull
```

### 步驟 2：開一個新分支

```bash
git switch -c feature/route-search
```

分支命名格式：`類型/簡短說明`（英文小寫，用 `-` 連接）

| 類型 | 用途 | 範例 |
|---|---|---|
| `feature/` | 新功能、新頁面 | `feature/route-search` |
| `fix/` | 修 bug | `fix/login-redirect` |
| `db/` | 資料表、SQL、假資料 | `db/create-tables` |
| `docs/` | 文件 | `docs/readme-install` |

一個分支只做一件事。做完合併後就刪掉，下一件事再開新分支。

### 步驟 3：寫程式並 commit

```bash
git status                # 看改了哪些檔案
git add 檔案路徑           # 加入要 commit 的檔案
git commit -m "feat: 新增路線搜尋頁面"
```

建議做完一個小段落就 commit 一次，不要累積一整天。

**commit 訊息格式**：`類型: 說明`，說明用中文即可。

| 類型 | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `db` | 資料表、SQL |
| `style` | 只改畫面樣式（CSS、排版） |
| `refactor` | 重構，功能不變 |
| `docs` | 文件 |

⚠️ 不要用 `git add .` 一次加入全部，容易把 `.env` 或不相關的檔案一起送出。

### 步驟 4：推上 GitHub

```bash
git push -u origin feature/route-search   # 第一次推這個分支
git push                                  # 之後再推只要這樣
```

### 步驟 5：開 Pull Request

1. 到 GitHub repo 頁面，會看到黃色提示「Compare & pull request」，點下去。
2. 確認方向是 `你的分支 → main`。
3. 依照 PR 範本填寫說明、勾選自我檢查。
4. 右側 Reviewers 指定**至少一位組員**。

### 步驟 6：Review 與合併

- 被指定的 reviewer 看過沒問題後按 **Approve**。有問題就留言，作者修改後再 push 到同一個分支，PR 會自動更新。
- 通過後，由**作者自己**按 **Squash and merge**，再按 **Delete branch**。
- 合併後回到本機：

```bash
git switch main
git pull
git branch -d feature/route-search   # 刪除本機的舊分支
```

---

## 4. 分支落後 main 時

別人的 PR 合併後，你的分支會落後。PR 頁面出現衝突，或你需要用到別人的新功能時：

```bash
git switch feature/route-search
git pull origin main
```

如果沒有衝突，Git 會自動合併，接著 `git push` 即可。

---

## 5. 處理衝突

`git pull origin main` 出現 `CONFLICT` 時，代表你和別人改到同一段程式碼。

1. 用 VS Code 打開有衝突的檔案，會看到：

```
<<<<<<< HEAD
你的版本
=======
main 上的版本
>>>>>>> main
```

2. VS Code 上方有按鈕可以選 Accept Current（你的）、Accept Incoming（main 的）、Accept Both（兩個都留）。不確定時，**找改那段程式的組員一起看**。
3. 改完確認程式能跑，然後：

```bash
git add 有衝突的檔案
git commit -m "fix: 解決與 main 的衝突"
git push
```

---

## 6. 程式撰寫慣例

### 新增頁面（Blueprint）

前台路由寫在 `frontstage/views/frontstage.py`，後台寫在 `backstage/views/backstage.py`。路由會自動加上前綴，**不需要修改 `app.py`**。

```python
@frontstage_bp.route('/route/<route_id>')
def route_detail(route_id):
    return render_template('frontstage/route_detail.html', route_id=route_id)
```

### 模板（HTML）

- 檔案放在 Blueprint 底下**同名的子資料夾**，避免不同模組的同名檔案互相覆蓋：
  - 前台 → `frontstage/templates/frontstage/xxx.html`
  - 後台 → `backstage/templates/backstage/xxx.html`
- 每個頁面都繼承 `base.html`：

```html
{% extends 'base.html' %}

{% block title %}路線查詢{% endblock %}

{% block content %}
  <h1>路線查詢</h1>
{% endblock %}
```

- 產生網址要加 Blueprint 名稱：`url_for('frontstage.index')`、`url_for('backstage.index')`，只寫 `url_for('index')` 會出錯。

### SQL

- 連線一律使用 `link.py` 的 `get_connection()`，用完要 `close()`。
- **一律使用參數化查詢**，不要用 f-string 或 `+` 把使用者輸入拼進 SQL（會有 SQL injection）：

```python
# ✅ 正確
cur.execute('SELECT * FROM route WHERE routename LIKE %s', (f'%{keyword}%',))

# ❌ 錯誤
cur.execute(f"SELECT * FROM route WHERE routename LIKE '%{keyword}%'")
```

- 新增、修改、刪除資料後要 `conn.commit()`，否則不會寫入。
- 查詢依實體分檔放在 `api/`，例如 `api/route.py`、`api/station.py`、`api/bus.py`。

### 資料庫結構的修改

全組共用同一個資料庫，任何人改資料表都會影響所有人。

1. 建表或修改資料表的 SQL，寫成檔案放在 `database/`，走 PR 流程。
2. PR 合併後，**在群組通知**再到資料庫執行。
3. 不要直接在 pgAdmin 改資料表而不留下 SQL 檔。

---

## 7. 安全規則

- `.env` 不可以 commit。commit 前用 `git status` 確認清單裡沒有 `.env`。
- 如果不小心把密碼推上 GitHub：立刻在群組說，並請助教或負責人更換資料庫密碼。只刪掉檔案沒有用，歷史紀錄裡還看得到。

---

## 8. 常用指令速查

| 想做的事 | 指令 |
|---|---|
| 看目前狀態 | `git status` |
| 看目前在哪個分支 | `git branch` |
| 切換分支 | `git switch 分支名稱` |
| 開新分支 | `git switch -c 分支名稱` |
| 取得最新 main | `git switch main` → `git pull` |
| 看 commit 紀錄 | `git log --oneline` |
| 放棄某個檔案還沒 commit 的修改 | `git restore 檔案路徑` |
| 把已 add 的檔案移出暫存 | `git restore --staged 檔案路徑` |
