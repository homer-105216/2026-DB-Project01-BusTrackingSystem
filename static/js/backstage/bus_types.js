// 真實車型資料庫操作；不使用或修改 localStorage 的示範車型。
let databaseBusTypes = [], typeKeyword = '', typeLoaded = false, typeLoading = false;
let typeWriting = false, typeError = '', typeCsrf = '', editingType = null;
const typeSubmit = el('form').querySelector('button[type="submit"]');

function renderDatabaseBusTypes() {
    el('add').disabled = !typeLoaded || typeLoading || typeWriting;
    el('type-reload').disabled = typeLoading || typeWriting;
    el('type-search').disabled = !typeLoaded || typeLoading;
    el('type-status').textContent = typeLoading ? '正在讀取資料庫車型…' : typeError;
    el('type-status').setAttribute('role', typeError ? 'alert' : 'status');
    if (typeLoading || !typeLoaded) {
        el('type-table').innerHTML = ''; el('type-total').textContent = ''; return;
    }
    const rows = databaseBusTypes.filter(row => [row.busType, row.capacity].some(value =>
        String(value).toLowerCase().includes(typeKeyword.toLowerCase())));
    el('type-table').innerHTML = `<table><thead><tr><th scope="col">車型名稱</th><th scope="col">容載人數</th><th scope="col">操作</th></tr></thead>
        <tbody>${rows.map(row => `<tr><td>${esc(row.busType)}</td><td>${esc(row.capacity)} 人</td><td>
            <button data-type-edit="${esc(row.busType)}" ${typeWriting ? 'disabled' : ''}>編輯</button>
            <button class="danger" data-type-delete="${esc(row.busType)}" ${typeWriting ? 'disabled' : ''}>刪除</button></td></tr>`).join('')}</tbody></table>
        ${rows.length ? '' : `<div class="empty">${databaseBusTypes.length ? '沒有符合條件的車型。' : '資料庫目前沒有車型，可點選「新增車型」。'}</div>`}`;
    el('type-total').textContent = `顯示 ${rows.length} 筆 / 共 ${databaseBusTypes.length} 筆`;
}

async function requestBusTypes(url, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal, cache: 'no-store',
            headers: { Accept: 'application/json', ...(options.headers || {}) } });
        const payload = await response.json();
        if (!response.ok || payload.status !== 'ok') throw new Error(payload.message || '車型資料操作失敗。');
        return payload;
    } catch (error) {
        if (error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError) {
            throw new Error(options.method ? '連線中斷，請重新載入確認資料是否已更新，再決定是否重試。' : '無法讀取車型，請確認 Flask 與資料庫連線後重新載入。');
        }
        throw error;
    } finally { clearTimeout(timer); }
}

async function loadDatabaseBusTypes() {
    if (typeLoading || typeWriting) return;
    typeLoading = true; typeLoaded = false; typeError = ''; databaseBusTypes = []; renderDatabaseBusTypes();
    try {
        const payload = await requestBusTypes(busTypesApiUrl);
        if (!Array.isArray(payload.busTypes) || typeof payload.csrfToken !== 'string' ||
            !payload.busTypes.every(row => typeof row.busType === 'string' && Number.isInteger(row.capacity))) {
            throw new Error('車型資料格式不正確，請確認 API 欄位。');
        }
        databaseBusTypes = payload.busTypes; typeCsrf = payload.csrfToken; typeLoaded = true;
    } catch (error) { typeError = error.message; }
    finally { typeLoading = false; renderDatabaseBusTypes(); }
}

function editDatabaseBusType(name = null) {
    if (!typeLoaded || typeWriting || typeLoading) return;
    editingType = name;
    const row = name === null ? null : databaseBusTypes.find(item => item.busType === name);
    if (name !== null && !row) return;
    el('form-title').textContent = name === null ? '新增車型' : '編輯車型'; el('error').textContent = '';
    el('fields').innerHTML = `<label>車型名稱<input name="busType" value="${esc(row?.busType || '')}" maxlength="50" required ${row ? 'readonly class="member-readonly"' : ''}></label>
        <label>容載人數<input name="capacity" type="number" min="1" max="2147483647" step="1" value="${esc(row?.capacity || '')}" required></label>`;
    el('editor').showModal();
}

el('section-name').textContent = configs['bus-types'].group;
el('title').textContent = '車型管理';
el('description').textContent = '管理資料庫的車型與容載人數，供車輛資料選用。';
el('add').hidden = false; el('add').textContent = '＋ 新增車型'; el('add').disabled = true;
typeSubmit.textContent = '儲存至資料庫';
el('content').innerHTML = `<div class="panel"><div class="toolbar">
    <input id="type-search" type="search" aria-label="搜尋車型" placeholder="搜尋車型名稱或容載人數…" disabled>
    <button id="type-reload" class="btn" type="button">重新載入</button></div>
    <p id="type-status" class="count" role="status" aria-live="polite"></p><div id="type-table" class="table-wrap"></div>
    <div class="foot"><span id="type-total"></span><span>PostgreSQL 車型資料</span></div></div>`;
el('add').onclick = () => editDatabaseBusType();
el('type-search').oninput = e => { typeKeyword = e.target.value.trim(); renderDatabaseBusTypes(); };
el('type-reload').onclick = loadDatabaseBusTypes;
el('cancel').onclick = () => { if (!typeWriting) el('editor').close(); };
el('editor').addEventListener('cancel', e => { if (typeWriting) e.preventDefault(); });

el('form').onsubmit = async e => {
    e.preventDefault(); if (typeWriting) return;
    const fields = new FormData(e.target), name = String(fields.get('busType') || '').trim();
    const capacity = Number(fields.get('capacity'));
    if (!name || [...name].length > 50 || !Number.isInteger(capacity) || capacity <= 0 || capacity > 2147483647) {
        el('error').textContent = '請填寫有效車型名稱及正整數容載人數。'; return;
    }
    const isNew = editingType === null;
    typeWriting = true; typeSubmit.disabled = true; el('cancel').disabled = true; el('error').textContent = ''; renderDatabaseBusTypes();
    let updated = false;
    try {
        const payload = await requestBusTypes(isNew ? busTypesApiUrl : `${busTypesApiUrl}/${encodeURIComponent(editingType)}`, {
            method: isNew ? 'POST' : 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': typeCsrf },
            body: JSON.stringify(isNew ? { busType: name, capacity } : { capacity })
        });
        updated = true; el('editor').close(); toast(payload.message);
    } catch (error) { el('error').textContent = error.message; }
    finally { typeWriting = false; typeSubmit.disabled = false; el('cancel').disabled = false; renderDatabaseBusTypes(); }
    if (updated) await loadDatabaseBusTypes();
};

el('type-table').onclick = async e => {
    const button = e.target.closest('button'); if (!button || typeWriting || typeLoading) return;
    if (button.hasAttribute('data-type-edit')) { editDatabaseBusType(button.dataset.typeEdit); return; }
    if (!button.hasAttribute('data-type-delete')) return;
    const name = button.dataset.typeDelete;
    if (!confirm(`確定從資料庫刪除車型「${name}」？若仍有車輛使用，資料庫會拒絕刪除。`)) return;
    typeWriting = true; typeError = ''; renderDatabaseBusTypes(); let deleted = false;
    try {
        const payload = await requestBusTypes(`${busTypesApiUrl}/${encodeURIComponent(name)}`, {
            method: 'DELETE', headers: { 'X-CSRF-Token': typeCsrf }
        });
        deleted = true; toast(payload.message);
    } catch (error) { typeError = error.message; }
    finally { typeWriting = false; renderDatabaseBusTypes(); }
    if (deleted) await loadDatabaseBusTypes();
};
loadDatabaseBusTypes();
