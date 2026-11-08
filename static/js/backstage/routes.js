// 真實路線資料庫操作；不使用或修改 localStorage 的示範路線。
let databaseRoutes = [], typeKeyword = '', typeLoaded = false, typeLoading = false;
let typeWriting = false, typeError = '', typeCsrf = '', editingType = null;
const typeSubmit = el('form').querySelector('button[type="submit"]');

function renderDatabaseRoutes() {
    el('add').disabled = !typeLoaded || typeLoading || typeWriting;
    el('type-reload').disabled = typeLoading || typeWriting;
    el('type-search').disabled = !typeLoaded || typeLoading;
    el('type-status').textContent = typeLoading ? '正在讀取資料庫路線…' : typeError;
    el('type-status').setAttribute('role', typeError ? 'alert' : 'status');
    if (typeLoading || !typeLoaded) {
        el('type-table').innerHTML = ''; el('type-total').textContent = ''; return;
    }
    const rows = databaseRoutes.filter(row => [row.routeId, row.routeName, row.origin, row.destination].some(value =>
        String(value).toLowerCase().includes(typeKeyword.toLowerCase())));
    el('type-table').innerHTML = `<table><thead><tr><th scope="col">路線編號</th><th scope="col">路線名稱</th><th scope="col">起點</th><th scope="col">終點</th><th scope="col">操作</th></tr></thead>
        <tbody>${rows.map(row => `<tr><td>${esc(row.routeId)}</td><td>${esc(row.routeName)}</td><td>${esc(row.origin)}</td><td>${esc(row.destination)}</td><td>
            <button data-type-edit="${esc(row.routeId)}" ${typeWriting ? 'disabled' : ''}>編輯</button>
            <button class="danger" data-type-delete="${esc(row.routeId)}" ${typeWriting ? 'disabled' : ''}>刪除</button></td></tr>`).join('')}</tbody></table>
        ${rows.length ? '' : `<div class="empty">${databaseRoutes.length ? '沒有符合條件的路線。' : '資料庫目前沒有路線，可點選「新增路線」。'}</div>`}`;
    el('type-total').textContent = `顯示 ${rows.length} 筆 / 共 ${databaseRoutes.length} 筆`;
}

async function requestRoutes(url, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal, cache: 'no-store',
            headers: { Accept: 'application/json', ...(options.headers || {}) } });
        const payload = await response.json();
        if (!response.ok || payload.status !== 'ok') throw new Error(payload.message || '路線資料操作失敗。');
        return payload;
    } catch (error) {
        if (error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError) {
            throw new Error(options.method ? '連線中斷，請重新載入確認資料是否已更新，再決定是否重試。' : '無法讀取路線，請確認 Flask 與資料庫連線後重新載入。');
        }
        throw error;
    } finally { clearTimeout(timer); }
}

async function loadDatabaseRoutes() {
    if (typeLoading || typeWriting) return;
    typeLoading = true; typeLoaded = false; typeError = ''; databaseRoutes = []; renderDatabaseRoutes();
    try {
        const payload = await requestRoutes(routesApiUrl);
        if (!Array.isArray(payload.routes) || typeof payload.csrfToken !== 'string' ||
            !payload.routes.every(row => ['routeId', 'routeName', 'origin', 'destination'].every(k => typeof row[k] === 'string'))) {
            throw new Error('路線資料格式不正確，請確認 API 欄位。');
        }
        databaseRoutes = payload.routes; typeCsrf = payload.csrfToken; typeLoaded = true;
    } catch (error) { typeError = error.message; }
    finally { typeLoading = false; renderDatabaseRoutes(); }
}

function editDatabaseRoute(name = null) {
    if (!typeLoaded || typeWriting || typeLoading) return;
    editingType = name;
    const row = name === null ? null : databaseRoutes.find(item => item.routeId === name);
    if (name !== null && !row) return;
    el('form-title').textContent = name === null ? '新增路線' : '編輯路線'; el('error').textContent = '';
    el('fields').innerHTML = `<label>路線編號<input name="routeId" value="${esc(row?.routeId || '')}" maxlength="50" required ${row ? 'readonly class="member-readonly"' : ''}></label>
        ${[['routeName','路線名稱'],['origin','起點'],['destination','終點']].map(([key,label]) => `<label>${label}<input name="${key}" value="${esc(row?.[key] || '')}" maxlength="100" required></label>`).join('')}`;
    el('editor').showModal();
}

el('section-name').textContent = configs.routes.group;
el('title').textContent = '路線管理';
el('description').textContent = '管理資料庫中的路線編號、名稱及起訖站。';
el('add').hidden = false; el('add').textContent = '＋ 新增路線'; el('add').disabled = true;
typeSubmit.textContent = '儲存至資料庫';
el('content').innerHTML = `<div class="panel"><div class="toolbar">
    <input id="type-search" type="search" aria-label="搜尋路線" placeholder="搜尋路線編號、名稱或起訖站…" disabled>
    <button id="type-reload" class="btn" type="button">重新載入</button></div>
    <p id="type-status" class="count" role="status" aria-live="polite"></p><div id="type-table" class="table-wrap"></div>
    <div class="foot"><span id="type-total"></span><span>PostgreSQL 路線資料</span></div></div>`;
el('add').onclick = () => editDatabaseRoute();
el('type-search').oninput = e => { typeKeyword = e.target.value.trim(); renderDatabaseRoutes(); };
el('type-reload').onclick = loadDatabaseRoutes;
el('cancel').onclick = () => { if (!typeWriting) el('editor').close(); };
el('editor').addEventListener('cancel', e => { if (typeWriting) e.preventDefault(); });

el('form').onsubmit = async e => {
    e.preventDefault(); if (typeWriting) return;
    const fields = new FormData(e.target), data = Object.fromEntries(['routeId', 'routeName', 'origin', 'destination'].map(k => [k, String(fields.get(k) || '').trim()]));
    if (Object.entries(data).some(([key,value]) => !value || [...value].length > (key === 'routeId' ? 50 : 100))) {
        el('error').textContent = '請填寫有效的路線編號、名稱、起點及終點。'; return;
    }
    const isNew = editingType === null;
    typeWriting = true; typeSubmit.disabled = true; el('cancel').disabled = true; el('error').textContent = ''; renderDatabaseRoutes();
    let updated = false;
    try {
        const payload = await requestRoutes(isNew ? routesApiUrl : `${routesApiUrl}/${encodeURIComponent(editingType)}`, {
            method: isNew ? 'POST' : 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': typeCsrf },
            body: JSON.stringify(data)
        });
        updated = true; el('editor').close(); toast(payload.message);
    } catch (error) { el('error').textContent = error.message; }
    finally { typeWriting = false; typeSubmit.disabled = false; el('cancel').disabled = false; renderDatabaseRoutes(); }
    if (updated) await loadDatabaseRoutes();
};

el('type-table').onclick = async e => {
    const button = e.target.closest('button'); if (!button || typeWriting || typeLoading) return;
    if (button.hasAttribute('data-type-edit')) { editDatabaseRoute(button.dataset.typeEdit); return; }
    if (!button.hasAttribute('data-type-delete')) return;
    const name = button.dataset.typeDelete;
    if (!confirm(`確定從資料庫刪除路線「${name}」？若仍被站序、班次或會員收藏使用，將無法刪除。`)) return;
    typeWriting = true; typeError = ''; renderDatabaseRoutes(); let deleted = false;
    try {
        const payload = await requestRoutes(`${routesApiUrl}/${encodeURIComponent(name)}`, {
            method: 'DELETE', headers: { 'X-CSRF-Token': typeCsrf }
        });
        deleted = true; toast(payload.message);
    } catch (error) { typeError = error.message; }
    finally { typeWriting = false; renderDatabaseRoutes(); }
    if (deleted) await loadDatabaseRoutes();
};
loadDatabaseRoutes();
