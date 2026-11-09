// 真實車輛資料庫操作；不使用或修改 localStorage 的示範車輛。
let databaseBuses = [], typeKeyword = '', typeLoaded = false, typeLoading = false;
let availableBusTypes = [];
let typeWriting = false, typeError = '', typeCsrf = '', editingType = null;
const typeSubmit = el('form').querySelector('button[type="submit"]');

function renderDatabaseBuses() {
    el('add').disabled = !typeLoaded || typeLoading || typeWriting;
    el('type-reload').disabled = typeLoading || typeWriting;
    el('type-search').disabled = !typeLoaded || typeLoading;
    el('type-status').textContent = typeLoading ? '正在讀取資料庫車輛…' : typeError;
    el('type-status').setAttribute('role', typeError ? 'alert' : 'status');
    if (typeLoading || !typeLoaded) {
        el('type-table').innerHTML = ''; el('type-total').textContent = ''; return;
    }
    const rows = databaseBuses.filter(row => [row.bId, row.busType, row.capacity].some(value =>
        String(value).toLowerCase().includes(typeKeyword.toLowerCase())));
    el('type-table').innerHTML = `<table><thead><tr><th scope="col">車牌號碼</th><th scope="col">車型</th><th scope="col">容載人數</th><th scope="col">操作</th></tr></thead>
        <tbody>${rows.map(row => `<tr><td>${esc(row.bId)}</td><td>${esc(row.busType)}</td><td>${esc(row.capacity)} 人</td><td>
            <button data-type-edit="${esc(row.bId)}" ${typeWriting ? 'disabled' : ''}>編輯</button>
            <button class="danger" data-type-delete="${esc(row.bId)}" ${typeWriting ? 'disabled' : ''}>刪除</button></td></tr>`).join('')}</tbody></table>
        ${rows.length ? '' : `<div class="empty">${databaseBuses.length ? '沒有符合條件的車輛。' : '資料庫目前沒有車輛，可點選「新增車輛」。'}</div>`}`;
    el('type-total').textContent = `顯示 ${rows.length} 筆 / 共 ${databaseBuses.length} 筆`;
}

async function requestBuses(url, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal, cache: 'no-store',
            headers: { Accept: 'application/json', ...(options.headers || {}) } });
        const payload = await response.json();
        if (!response.ok || payload.status !== 'ok') throw new Error(payload.message || '車輛資料操作失敗。');
        return payload;
    } catch (error) {
        if (error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError) {
            throw new Error(options.method ? '連線中斷，請重新載入確認資料是否已更新，再決定是否重試。' : '無法讀取車輛，請確認 Flask 與資料庫連線後重新載入。');
        }
        throw error;
    } finally { clearTimeout(timer); }
}

async function loadDatabaseBuses() {
    if (typeLoading || typeWriting) return;
    typeLoading = true; typeLoaded = false; typeError = ''; databaseBuses = []; renderDatabaseBuses();
    try {
        const payload = await requestBuses(busesApiUrl);
        const types = await requestBuses(busTypesApiUrl);
        if (!Array.isArray(types.busTypes) || !types.busTypes.every(t => typeof t.busType === 'string' && Number.isInteger(t.capacity))) throw new Error('車型選單資料格式不正確。');
        availableBusTypes = types.busTypes;
        if (!Array.isArray(payload.buses) || typeof payload.csrfToken !== 'string' ||
            !payload.buses.every(row => typeof row.bId === 'string' && typeof row.busType === 'string' && Number.isInteger(row.capacity))) {
            throw new Error('車輛資料格式不正確，請確認 API 欄位。');
        }
        databaseBuses = payload.buses; typeCsrf = payload.csrfToken; typeLoaded = true;
    } catch (error) { typeError = error.message; }
    finally { typeLoading = false; renderDatabaseBuses(); }
}

function editDatabaseBus(name = null) {
    if (!typeLoaded || typeWriting || typeLoading) return;
    editingType = name;
    const row = name === null ? null : databaseBuses.find(item => item.bId === name);
    if (name !== null && !row) return;
    el('form-title').textContent = name === null ? '新增車輛' : '編輯車輛'; el('error').textContent = '';
    el('fields').innerHTML = `<label>車牌號碼<input name="bId" value="${esc(row?.bId || '')}" placeholder="例如 EAA-1234" maxlength="50" required ${row ? 'readonly class="member-readonly"' : ''}></label>
        <label>車型<select name="busType" required><option value="">請選擇車型</option>${availableBusTypes.map(t => `<option value="${esc(t.busType)}" ${t.busType === row?.busType ? 'selected' : ''}>${esc(t.busType)}</option>`).join('')}</select></label>
        <label>容載人數<input id="bus-capacity" class="member-readonly" readonly value=""></label>`;
    const select = el('fields').querySelector('select');
    select.onchange = () => { const type = availableBusTypes.find(t => t.busType === select.value); el('bus-capacity').value = type ? `${type.capacity} 人` : ''; };
    select.onchange();
    el('editor').showModal();
}

el('section-name').textContent = configs['buses'].group;
el('title').textContent = '車輛管理';
el('description').textContent = '以車牌識別車輛，每輛車選擇一種車型，容載人數由車型帶入。';
el('add').hidden = false; el('add').textContent = '＋ 新增車輛'; el('add').disabled = true;
typeSubmit.textContent = '儲存至資料庫';
el('content').innerHTML = `<div class="panel"><div class="toolbar">
    <input id="type-search" type="search" aria-label="搜尋車輛" placeholder="搜尋車牌號碼、車型或容載人數…" disabled>
    <button id="type-reload" class="btn" type="button">重新載入</button></div>
    <p id="type-status" class="count" role="status" aria-live="polite"></p><div id="type-table" class="table-wrap"></div>
    <div class="foot"><span id="type-total"></span><span>PostgreSQL 車輛資料</span></div></div>`;
el('add').onclick = () => editDatabaseBus();
el('type-search').oninput = e => { typeKeyword = e.target.value.trim(); renderDatabaseBuses(); };
el('type-reload').onclick = loadDatabaseBuses;
el('cancel').onclick = () => { if (!typeWriting) el('editor').close(); };
el('editor').addEventListener('cancel', e => { if (typeWriting) e.preventDefault(); });

el('form').onsubmit = async e => {
    e.preventDefault(); if (typeWriting) return;
    const fields = new FormData(e.target), plate = String(fields.get('bId') || '').trim(), busType = String(fields.get('busType') || '').trim();
    if (!plate || [...plate].length > 50 || !availableBusTypes.some(t => t.busType === busType)) {
        el('error').textContent = '請填寫有效車牌號碼，並選擇車型。'; return;
    }
    const isNew = editingType === null;
    typeWriting = true; typeSubmit.disabled = true; el('cancel').disabled = true; el('error').textContent = ''; renderDatabaseBuses();
    let updated = false;
    try {
        const payload = await requestBuses(isNew ? busesApiUrl : `${busesApiUrl}/${encodeURIComponent(editingType)}`, {
            method: isNew ? 'POST' : 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': typeCsrf },
            body: JSON.stringify(isNew ? { bId: plate, busType } : { busType })
        });
        updated = true; el('editor').close(); toast(payload.message);
    } catch (error) { el('error').textContent = error.message; }
    finally { typeWriting = false; typeSubmit.disabled = false; el('cancel').disabled = false; renderDatabaseBuses(); }
    if (updated) await loadDatabaseBuses();
};

el('type-table').onclick = async e => {
    const button = e.target.closest('button'); if (!button || typeWriting || typeLoading) return;
    if (button.hasAttribute('data-type-edit')) { editDatabaseBus(button.dataset.typeEdit); return; }
    if (!button.hasAttribute('data-type-delete')) return;
    const name = button.dataset.typeDelete;
    if (!confirm(`確定從資料庫刪除車輛「${name}」？若已有派車紀錄，資料庫會拒絕刪除。`)) return;
    typeWriting = true; typeError = ''; renderDatabaseBuses(); let deleted = false;
    try {
        const payload = await requestBuses(`${busesApiUrl}/${encodeURIComponent(name)}`, {
            method: 'DELETE', headers: { 'X-CSRF-Token': typeCsrf }
        });
        deleted = true; toast(payload.message);
    } catch (error) { typeError = error.message; }
    finally { typeWriting = false; renderDatabaseBuses(); }
    if (deleted) await loadDatabaseBuses();
};
loadDatabaseBuses();
