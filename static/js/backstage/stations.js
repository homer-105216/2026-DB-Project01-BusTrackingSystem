// 站點管理：從 API 讀寫 PostgreSQL，不改動其他頁面的瀏覽器示範資料。
let databaseStations = [], stationKeyword = '', stationLoaded = false, stationLoading = false;
let stationWriting = false, stationError = '', stationCsrf = '', editingStationId = null;
const stationSubmit = el('form').querySelector('button[type="submit"]');

function renderDatabaseStations() {
    el('add').disabled = !stationLoaded || stationLoading || stationWriting;
    el('station-reload').disabled = stationLoading || stationWriting;
    el('station-search').disabled = !stationLoaded || stationLoading;
    el('station-status').textContent = stationLoading ? '正在讀取資料庫站點…' : stationError;
    el('station-status').setAttribute('role', stationError ? 'alert' : 'status');
    if (stationLoading || !stationLoaded) { el('station-table').innerHTML = ''; el('station-total').textContent = ''; return; }
    const rows = databaseStations.filter(row => ['stationId', 'sName', 'address', 'sLatitude', 'sLongitude'].some(key =>
        String(row[key] ?? '').toLowerCase().includes(stationKeyword.toLowerCase())));
    el('station-table').innerHTML = `<table><thead><tr><th scope="col">站點編號</th><th scope="col">站點名稱</th><th scope="col">地址</th>
        <th scope="col">緯度</th><th scope="col">經度</th><th scope="col">操作</th></tr></thead><tbody>
        ${rows.map(row => `<tr><td>${esc(row.stationId)}</td><td>${esc(row.sName)}</td><td>${esc(row.address)}</td>
        <td>${esc(row.sLatitude)}</td><td>${esc(row.sLongitude)}</td><td>
            <button data-station-edit="${esc(row.stationId)}" ${stationWriting ? 'disabled' : ''}>編輯</button>
            <button class="danger" data-station-delete="${esc(row.stationId)}" ${stationWriting ? 'disabled' : ''}>刪除</button></td></tr>`).join('')}</tbody></table>
        ${rows.length ? '' : `<div class="empty">${databaseStations.length ? '沒有符合條件的站點。' : '資料庫目前沒有站點，可點選「新增站點」。'}</div>`}`;
    el('station-total').textContent = `顯示 ${rows.length} 筆 / 共 ${databaseStations.length} 筆`;
}

async function stationRequest(url, options = {}) {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal, cache: 'no-store',
            headers: { Accept: 'application/json', ...(options.headers || {}) } });
        const payload = await response.json();
        if (!response.ok || payload.status !== 'ok') throw new Error(payload.message || '站點資料操作失敗。');
        return payload;
    } catch (error) {
        if (error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError) {
            throw new Error(options.method ? '連線中斷，請重新載入確認資料是否已更新，再決定是否重試。' : '無法讀取站點，請確認 Flask 與資料庫連線後重新載入。');
        }
        throw error;
    } finally { clearTimeout(timer); }
}

async function loadDatabaseStations() {
    if (stationLoading || stationWriting) return;
    stationLoading = true; stationLoaded = false; stationError = ''; databaseStations = []; renderDatabaseStations();
    try {
        const payload = await stationRequest(stationsApiUrl);
        if (!Array.isArray(payload.stations) || typeof payload.csrfToken !== 'string' || !payload.stations.every(row =>
            typeof row.stationId === 'string' && typeof row.sName === 'string' && typeof row.address === 'string' &&
            Number.isFinite(row.sLatitude) && Number.isFinite(row.sLongitude))) throw new Error('站點資料格式不正確，請確認 API 欄位。');
        databaseStations = payload.stations; stationCsrf = payload.csrfToken; stationLoaded = true;
    } catch (error) { stationError = error.message; }
    finally { stationLoading = false; renderDatabaseStations(); }
}

function editDatabaseStation(id = null) {
    if (!stationLoaded || stationLoading || stationWriting) return;
    editingStationId = id;
    const row = id === null ? {} : databaseStations.find(item => item.stationId === id);
    if (!row) return;
    el('form-title').textContent = id === null ? '新增站點' : '編輯站點'; el('error').textContent = '';
    el('fields').innerHTML = `<label>站點編號<input name="stationId" value="${esc(row.stationId ?? '')}" maxlength="50" required ${id === null ? '' : 'readonly class="member-readonly"'}></label>
        <label>站點名稱<input name="sName" value="${esc(row.sName ?? '')}" maxlength="100" required></label>
        <label>地址<input name="address" value="${esc(row.address ?? '')}" maxlength="255" required></label>
        <label>緯度<input name="sLatitude" type="number" min="-90" max="90" step="any" value="${esc(row.sLatitude ?? '')}" required></label>
        <label>經度<input name="sLongitude" type="number" min="-180" max="180" step="any" value="${esc(row.sLongitude ?? '')}" required></label>`;
    el('editor').showModal();
}

el('section-name').textContent = configs.stations.group;
el('title').textContent = '站點管理';
el('description').textContent = '管理資料庫中的站點名稱、地址與地理座標。';
el('add').hidden = false; el('add').textContent = '＋ 新增站點'; el('add').disabled = true;
stationSubmit.textContent = '儲存至資料庫';
el('content').innerHTML = `<div class="panel"><div class="toolbar">
    <input id="station-search" type="search" aria-label="搜尋站點" placeholder="搜尋站點編號、名稱、地址或座標…" disabled>
    <button id="station-reload" class="btn" type="button">重新載入</button></div>
    <p id="station-status" class="count" role="status" aria-live="polite"></p><div id="station-table" class="table-wrap"></div>
    <div class="foot"><span id="station-total"></span><span>PostgreSQL 站點資料</span></div></div>`;
el('add').onclick = () => editDatabaseStation();
el('station-search').oninput = e => { stationKeyword = e.target.value.trim(); renderDatabaseStations(); };
el('station-reload').onclick = loadDatabaseStations;
el('cancel').onclick = () => { if (!stationWriting) el('editor').close(); };
el('editor').addEventListener('cancel', e => { if (stationWriting) e.preventDefault(); });

el('form').onsubmit = async e => {
    e.preventDefault(); if (stationWriting) return;
    const fields = new FormData(e.target), values = Object.fromEntries(fields);
    const payload = { stationId: String(values.stationId || '').trim(), sName: String(values.sName || '').trim(),
        address: String(values.address || '').trim(), sLatitude: Number(values.sLatitude), sLongitude: Number(values.sLongitude) };
    if (!payload.stationId || !payload.sName || !payload.address || !String(values.sLatitude ?? '').trim() || !String(values.sLongitude ?? '').trim() ||
        !Number.isFinite(payload.sLatitude) || Math.abs(payload.sLatitude) > 90 || !Number.isFinite(payload.sLongitude) || Math.abs(payload.sLongitude) > 180) {
        el('error').textContent = '請填寫完整站點資料；緯度需介於 -90～90，經度需介於 -180～180。'; return;
    }
    const isNew = editingStationId === null;
    stationWriting = true; stationSubmit.disabled = true; el('cancel').disabled = true; el('error').textContent = ''; renderDatabaseStations();
    let updated = false;
    try {
        const response = await stationRequest(isNew ? stationsApiUrl : `${stationsApiUrl}/${encodeURIComponent(editingStationId)}`, {
            method: isNew ? 'POST' : 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': stationCsrf }, body: JSON.stringify(payload)
        });
        updated = true; el('editor').close(); toast(response.message);
    } catch (error) { el('error').textContent = error.message; }
    finally { stationWriting = false; stationSubmit.disabled = false; el('cancel').disabled = false; renderDatabaseStations(); }
    if (updated) await loadDatabaseStations();
};

el('station-table').onclick = async e => {
    const button = e.target.closest('button'); if (!button || stationWriting || stationLoading) return;
    if (button.hasAttribute('data-station-edit')) { editDatabaseStation(button.dataset.stationEdit); return; }
    if (!button.hasAttribute('data-station-delete')) return;
    const id = button.dataset.stationDelete;
    const row = databaseStations.find(item => item.stationId === id);
    if (!confirm(`確定從資料庫刪除「${row?.sName ?? id}」（${id}）？仍被路線、班次時間或收藏使用的站點不可刪除。`)) return;
    stationWriting = true; stationError = ''; renderDatabaseStations(); let deleted = false;
    try {
        const response = await stationRequest(`${stationsApiUrl}/${encodeURIComponent(id)}`, {
            method: 'DELETE', headers: { 'X-CSRF-Token': stationCsrf }
        });
        deleted = true; toast(response.message);
    } catch (error) { stationError = error.message; }
    finally { stationWriting = false; renderDatabaseStations(); }
    if (deleted) await loadDatabaseStations();
};
loadDatabaseStations();
