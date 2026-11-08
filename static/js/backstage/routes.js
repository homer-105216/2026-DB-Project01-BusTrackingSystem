// 真實路線列表：由 Flask API 讀取，不使用或覆寫瀏覽器示範資料。
let liveRoutes = [], routeKeyword = '', routeLoading = false, routeLoaded = false, routeError = '';

function renderLiveRoutes() {
    const rows = liveRoutes.filter(row => !routeKeyword ||
        ['routeId', 'routeName', 'origin', 'destination'].some(key =>
            String(row[key] ?? '').toLowerCase().includes(routeKeyword.toLowerCase())));
    el('route-reload').disabled = routeLoading;
    el('route-search').disabled = !routeLoaded || routeLoading;
    el('route-load-status').textContent = routeLoading ? '正在讀取資料庫路線…' : routeError;
    el('route-load-status').setAttribute('role', routeError ? 'alert' : 'status');
    if (routeLoading || !routeLoaded) {
        el('route-table').innerHTML = '';
        el('route-total').textContent = '';
        return;
    }
    el('route-table').innerHTML = `<table><thead><tr>
        <th scope="col">路線編號</th><th scope="col">路線名稱</th><th scope="col">起點</th><th scope="col">終點</th><th scope="col">操作</th>
        </tr></thead><tbody>${rows.map(row => `<tr>
        <td>${esc(row.routeId)}</td><td>${esc(row.routeName)}</td><td>${esc(row.origin)}</td><td>${esc(row.destination)}</td>
        <td><button disabled title="編輯功能尚未串接資料庫">編輯</button><button disabled title="刪除功能尚未串接資料庫">刪除</button></td>
        </tr>`).join('')}</tbody></table>${rows.length ? '' : `<div class="empty">${liveRoutes.length ? '沒有符合條件的路線，請調整搜尋。' : '資料庫目前沒有路線資料。'}</div>`}`;
    el('route-total').textContent = `顯示 ${rows.length} 筆 / 共 ${liveRoutes.length} 筆`;
}

async function loadLiveRoutes() {
    if (routeLoading) return;
    routeLoading = true; routeLoaded = false; routeError = ''; liveRoutes = [];
    renderLiveRoutes();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(routesApiUrl, { signal: controller.signal, cache: 'no-store', headers: { Accept: 'application/json' } });
        const payload = await response.json();
        if (!response.ok || payload.status !== 'ok') throw new Error(payload.message || '無法取得路線資料，請重試。');
        if (!Array.isArray(payload.routes) || !payload.routes.every(row => row &&
            ['routeId', 'routeName', 'origin', 'destination'].every(key => Object.hasOwn(row, key)))) {
            throw new Error('路線資料格式不正確，請確認 API 回傳欄位。');
        }
        liveRoutes = payload.routes; routeLoaded = true;
    } catch (error) {
        routeError = error.name === 'AbortError' ? '讀取路線逾時，請重新載入。' :
            error instanceof TypeError || error instanceof SyntaxError ? '無法連接路線 API，請確認 Flask 正在執行後重試。' : error.message;
    } finally {
        clearTimeout(timeout); routeLoading = false; renderLiveRoutes();
    }
}

el('section-name').textContent = configs.routes.group;
el('title').textContent = configs.routes.title;
el('description').textContent = '查看資料庫中的路線編號、名稱及起訖站。';
el('add').hidden = false;
el('add').textContent = '＋ 新增路線';
el('add').disabled = true;
el('add').title = '新增功能尚未串接資料庫';
el('content').innerHTML = `<div class="panel"><div class="toolbar">
    <input id="route-search" type="search" aria-label="搜尋路線" placeholder="搜尋路線編號、名稱或起訖站…" disabled>
    <button id="route-reload" class="btn" type="button">重新載入</button>
    </div><p id="route-load-status" class="count" role="status" aria-live="polite"></p>
    <div id="route-table" class="table-wrap"></div><div class="foot"><span id="route-total"></span><span>PostgreSQL 路線資料</span></div></div>`;
el('route-search').oninput = e => { routeKeyword = e.target.value.trim(); renderLiveRoutes(); };
el('route-reload').onclick = loadLiveRoutes;
loadLiveRoutes();
