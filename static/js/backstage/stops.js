// 停靠順序屬於路線／方向；到離站時間屬於班次／站點。
let selectedStopTrip = '';
let editingStopTime = null;

function currentStopTrips() {
    return db.trips.filter(t => t.routeId === route && t.tDirection === direction)
        .sort((a, b) => a.departureTime.localeCompare(b.departureTime) || a.tId.localeCompare(b.tId));
}

function renderStops() {
    el('add').hidden = !route;
    el('search').placeholder = route ? '搜尋站點編號或名稱…' : '搜尋路線編號或名稱…';
    el('search').setAttribute('aria-label', route ? '搜尋站點' : '搜尋路線');
    if (!route) {
        selectedStopTrip = '';
        const routes = db.routes.filter(r => [r.routeId, r.routeName, r.origin, r.destination]
            .some(v => String(v).toLowerCase().includes(query.toLowerCase())));
        el('table').innerHTML = '<div class="route-cards">' + routes.map(r => `
            <button class="route-choice" data-route="${esc(r.routeId)}">
                <span>${esc(r.routeId)}</span><strong>${esc(r.routeName)}</strong>
                <span>${esc(r.origin)} → ${esc(r.destination)}</span><span>查看站點與順序 →</span>
            </button>`).join('') + '</div>' + (routes.length ? '' :
            '<div class="empty">沒有符合條件的路線，請調整搜尋或先到路線管理新增路線。</div>');
        el('total').textContent = `共 ${routes.length} 條路線`;
        return;
    }

    const selected = db.routes.find(r => r.routeId === route);
    const trips = currentStopTrips();
    if (!trips.some(t => t.tId === selectedStopTrip)) selectedStopTrip = trips[0]?.tId || '';
    const all = db.stops.map((r, i) => ({ r, i }))
        .filter(({ r }) => r.routeId === route && r.rDirection === direction)
        .sort((a, b) => Number(a.r.stopSequence) - Number(b.r.stopSequence));
    const rows = all.filter(({ r }) => {
        const station = db.stations.find(s => s.stationId === r.stationId);
        return [r.stationId, station?.sName].some(v => String(v ?? '').toLowerCase().includes(query.toLowerCase()));
    });
    const origin = direction === '去程' ? selected?.origin : selected?.destination;
    const destination = direction === '去程' ? selected?.destination : selected?.origin;
    el('table').innerHTML = `
        <button class="btn" data-back>← 返回路線清單</button>
        <div class="route-detail-heading"><h2>${esc(selected?.routeName ?? route)}</h2>
            <p>${esc(origin)} → ${esc(destination)}</p></div>
        <div class="direction-tabs" aria-label="行駛方向">${['去程', '返程'].map(d => `
            <button class="btn ${direction === d ? 'selected' : ''}" aria-pressed="${direction === d}"
                data-direction="${d}">${d}</button>`).join('')}</div>
        <div class="stop-trip-picker">
            <label>查看到離站時間的班次
                <select id="stop-trip" ${trips.length ? '' : 'disabled'}>
                    ${trips.length ? trips.map(t => `<option value="${esc(t.tId)}"
                        ${t.tId === selectedStopTrip ? 'selected' : ''}>${esc(t.tId)} · ${esc(t.departureTime)} 發車</option>`).join('') :
                        '<option value="">此方向尚無預定班次</option>'}
                </select>
            </label>
            <p>${trips.length ? '以下時間僅屬於選定班次，切換班次可分別設定。' :
                '請先到「預定班次管理」新增此方向的班次，即可設定時間；站序仍可編輯。'}</p>
        </div>
        <ol class="stop-list">${rows.map(({ r, i }) => {
            const station = db.stations.find(s => s.stationId === r.stationId);
            const time = db['stop-times'].find(t => t.tId === selectedStopTrip && t.stationId === r.stationId);
            return `<li class="stop-item">
                <span class="stop-number" aria-label="站序 ${esc(r.stopSequence)}">${esc(r.stopSequence)}</span>
                <div class="stop-info"><strong>${esc(station?.sName ?? r.stationId)}</strong><small>${esc(r.stationId)}</small>
                    <div class="stop-times"><span>預計到站<strong>${esc(time?.expArrivalTime || '未設定')}</strong></span>
                        <span>預計離站<strong>${esc(time?.expDepartureTime || '未設定')}</strong></span></div>
                </div>
                <div class="stop-actions">
                    <button class="btn" data-time-station="${esc(r.stationId)}" ${selectedStopTrip ? '' : 'disabled'}>設定時間</button>
                    <button class="btn" data-edit="${i}">編輯站序</button>
                    <button class="btn danger" data-delete="${i}">刪除</button>
                </div>
            </li>`;
        }).join('')}</ol>
        ${rows.length ? '' : `<div class="empty">${query ? '沒有符合條件的站點。' :
            '此方向尚未設定站點，請點右上角「新增站序」。'}</div>`}`;
    el('stop-trip').onchange = e => { selectedStopTrip = e.target.value; renderStops(); };
    el('total').textContent = `${direction}：顯示 ${rows.length} 站 / 共 ${all.length} 站`;
}

function validStopTimeContext() {
    return editingStopTime && db.trips.some(t => t.tId === editingStopTime.tId &&
        t.routeId === route && t.tDirection === direction) &&
        db.stops.some(s => s.routeId === route && s.rDirection === direction && s.stationId === editingStopTime.stationId);
}

function openStopTimeEditor(stationId) {
    editingStopTime = { tId: selectedStopTrip, stationId };
    if (!validStopTimeContext()) { toast('請先選擇有效班次與站點。'); return; }
    const trip = db.trips.find(t => t.tId === selectedStopTrip);
    const station = db.stations.find(s => s.stationId === stationId);
    const time = db['stop-times'].find(t => t.tId === selectedStopTrip && t.stationId === stationId);
    el('stop-time-title').textContent = `${station?.sName ?? stationId} · 到離站時間`;
    el('stop-time-context').textContent = `${trip.tId} · ${trip.departureTime} 發車 · ${direction}`;
    el('stop-arrival').value = time?.expArrivalTime || '';
    el('stop-departure').value = time?.expDepartureTime || '';
    el('stop-time-error').textContent = '';
    el('clear-stop-time').hidden = !time;
    el('stop-time-editor').showModal();
}

initManagement();
el('table').addEventListener('click', e => {
    const button = e.target.closest('[data-time-station]');
    if (button && !button.disabled) openStopTimeEditor(button.dataset.timeStation);
});
el('cancel-stop-time').onclick = () => el('stop-time-editor').close();
el('stop-time-form').onsubmit = e => {
    e.preventDefault();
    if (!validStopTimeContext()) { el('stop-time-error').textContent = '班次或站點已變更，請關閉後重新選擇。'; return; }
    const arrival = el('stop-arrival').value, departure = el('stop-departure').value;
    if (!arrival || !departure) { el('stop-time-error').textContent = '請填寫到站與離站時間。'; return; }
    if (departure < arrival) { el('stop-time-error').textContent = '離站時間不可早於到站時間；目前示範模式不支援跨日時間。'; return; }
    const previous = db['stop-times'].slice();
    const index = db['stop-times'].findIndex(t => t.tId === editingStopTime.tId && t.stationId === editingStopTime.stationId);
    const record = { ...editingStopTime, expArrivalTime: arrival, expDepartureTime: departure };
    if (index < 0) db['stop-times'].push(record); else db['stop-times'][index] = record;
    if (!save()) { db['stop-times'] = previous; return; }
    el('stop-time-editor').close(); renderStops(); toast('已儲存此班次的到離站時間');
};
el('clear-stop-time').onclick = () => {
    if (!validStopTimeContext() || !confirm('確定清除此班次在本站的到離站時間？站序不會刪除。')) return;
    const previous = db['stop-times'];
    db['stop-times'] = previous.filter(t => !(t.tId === editingStopTime.tId && t.stationId === editingStopTime.stationId));
    if (!save()) { db['stop-times'] = previous; return; }
    el('stop-time-editor').close(); renderStops(); toast('已清除此班次在本站的時間');
};
