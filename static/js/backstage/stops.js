// 真實 Route/Contain/Station/Trip/Run；不讀寫示範資料或 localStorage。
let stopRoutes = [], stopStations = [], stopRoute = '', stopDirection = '去程', stopQuery = '';
let stopDetail = null, stopReady = false, stopLoading = false, stopWriting = false, stopError = '', stopCsrf = '';
let stopRequestId = 0, stopEditing = null, timeEditing = null;
const stopSubmit = el('form').querySelector('button[type=submit]');
const timeSubmit = el('stop-time-form').querySelector('button[type=submit]');
const directionLabel = d => d === '回程' ? '返程' : d;
const timestampLabel = value => value ? value.replace('T', ' ') : '未設定';

async function stopRequest(url, options = {}) {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal, cache: 'no-store',
            headers: { Accept: 'application/json', ...(options.method ? { 'Content-Type': 'application/json', 'X-CSRF-Token': stopCsrf } : {}), ...(options.headers || {}) } });
        const data = await response.json();
        if (!response.ok || data.status !== 'ok') throw new Error(data.message || '站序操作失敗。');
        return data;
    } catch (error) {
        if (error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError)
            throw new Error(options.method ? '連線中斷，請重新載入確認資料是否已更新，再決定是否重試。' : '無法讀取站序資料，請確認 Flask 與資料庫連線後重試。');
        throw error;
    } finally { clearTimeout(timeout); }
}

function renderLiveStops() {
    el('add').hidden = !stopRoute;
    el('add').disabled = !stopDetail || stopLoading || stopWriting;
    el('stop-reload').disabled = stopLoading || stopWriting;
    el('search').disabled = !stopReady || stopLoading || stopWriting;
    el('search').placeholder = stopRoute ? '搜尋站點編號或名稱…' : '搜尋路線編號或名稱…';
    el('search').setAttribute('aria-label', stopRoute ? '搜尋站點' : '搜尋路線');
    el('stop-status').textContent = stopLoading ? '正在讀取資料庫站序與班次時間…' : stopError;
    el('stop-status').setAttribute('role', stopError ? 'alert' : 'status');
    el('total').textContent = '';
    if (!stopReady || stopLoading) { el('table').innerHTML = ''; return; }
    if (!stopRoute) {
        const rows = stopRoutes.filter(r => [r.routeId,r.routeName,r.origin,r.destination].some(v => String(v).toLowerCase().includes(stopQuery.toLowerCase())));
        el('table').innerHTML = '<div class="route-cards">' + rows.map(r => `<button class="route-choice" data-route="${esc(r.routeId)}"><span>${esc(r.routeId)}</span><strong>${esc(r.routeName)}</strong><span>${esc(r.origin)} → ${esc(r.destination)}</span><span>查看站點與順序 →</span></button>`).join('') + '</div>' + (rows.length ? '' : '<div class="empty">沒有符合條件的路線，請調整搜尋或先到路線管理新增路線。</div>');
        el('total').textContent = `共 ${rows.length} 條路線`; return;
    }
    const selected = stopDetail?.route || stopRoutes.find(r => r.routeId === stopRoute);
    const trips = stopDetail?.trips || [];
    const all = stopDetail?.stops || [];
    const rows = all.filter(r => [r.stationId,r.sName].some(v => String(v).toLowerCase().includes(stopQuery.toLowerCase())));
    const origin = stopDirection === '去程' ? selected?.origin : selected?.destination;
    const destination = stopDirection === '去程' ? selected?.destination : selected?.origin;
    el('table').innerHTML = `<button class="btn" data-back ${stopWriting ? 'disabled' : ''}>← 返回路線清單</button>
        <div class="route-detail-heading"><h2>${esc(selected?.routeName || stopRoute)}</h2><p>${esc(origin || '')} → ${esc(destination || '')}</p></div>
        <div class="direction-tabs" aria-label="行駛方向">${['去程','回程'].map(d => `<button class="btn ${stopDirection === d ? 'selected' : ''}" data-direction="${d}" aria-pressed="${stopDirection === d}" ${stopWriting ? 'disabled' : ''}>${directionLabel(d)}</button>`).join('')}</div>
        ${!stopDetail ? '<div class="empty">站序讀取失敗，請重新載入或返回路線清單。</div>' : `
        <div class="stop-trip-picker"><label>查看到離站時間的班次<select id="stop-trip" ${!trips.length || stopWriting ? 'disabled' : ''}>
            ${trips.length ? trips.map(t => `<option value="${esc(t.tId)}" ${stopDetail.selectedTripId === t.tId ? 'selected' : ''}>${esc(t.tId)} · ${esc(t.departureTime)} 發車</option>`).join('') : '<option value="">此方向尚無預定班次</option>'}</select></label>
            <p>${trips.length ? '以下日期時間僅屬於選定班次，切換班次可分別設定；請保留資料實際日期。' : '請先建立此方向的預定班次，即可設定時間；站序仍可編輯。'}</p></div>
        <ol class="stop-list">${rows.map(r => {
            const time = stopDetail.times.find(t => t.stationId === r.stationId);
            return `<li class="stop-item"><span class="stop-number" aria-label="站序 ${esc(r.stopSequence)}">${esc(r.stopSequence)}</span>
            <div class="stop-info"><strong>${esc(r.sName)}</strong><small>${esc(r.stationId)}</small><div class="stop-times"><span>預計到站<strong>${esc(timestampLabel(time?.expArrivalTime))}</strong></span><span>預計離站<strong>${esc(timestampLabel(time?.expDepartureTime))}</strong></span></div></div>
            <div class="stop-actions"><button class="btn" data-time-station="${esc(r.stationId)}" ${!stopDetail.selectedTripId || stopWriting ? 'disabled' : ''}>設定時間</button><button class="btn" data-stop-edit="${esc(r.stationId)}" ${stopWriting ? 'disabled' : ''}>編輯站序</button><button class="btn danger" data-stop-delete="${esc(r.stationId)}" ${stopWriting ? 'disabled' : ''}>刪除</button></div></li>`;
        }).join('')}</ol>${rows.length ? '' : `<div class="empty">${stopQuery ? '沒有符合條件的站點。' : '此方向尚未設定站點，請點右上角「新增站序」。'}</div>`}`}`;
    if (el('stop-trip')) el('stop-trip').onchange = e => loadStopDetail(e.target.value);
    el('total').textContent = stopDetail ? `${directionLabel(stopDirection)}：顯示 ${rows.length} 站 / 共 ${all.length} 站` : '';
}

async function loadStopOptions() {
    if (stopLoading || stopWriting) return;
    const id = ++stopRequestId;
    stopLoading = true; stopReady = false; stopError = ''; stopDetail = null; renderLiveStops();
    try {
        const data = await stopRequest(stopOptionsUrl);
        if (id !== stopRequestId) return;
        if (!Array.isArray(data.routes) || !Array.isArray(data.stations) || typeof data.csrfToken !== 'string') throw new Error('路線／站點選單格式不正確。');
        stopRoutes = data.routes; stopStations = data.stations; stopCsrf = data.csrfToken; stopReady = true;
        if (stopRoute && !stopRoutes.some(r => r.routeId === stopRoute)) stopRoute = '';
    } catch (error) { if (id === stopRequestId) stopError = error.message; }
    finally { if (id === stopRequestId) { stopLoading = false; renderLiveStops(); } }
    if (id === stopRequestId && stopReady && stopRoute) await loadStopDetail();
}

async function loadStopDetail(tripId) {
    if (!stopRoute || stopLoading || stopWriting) return;
    const id = ++stopRequestId;
    stopLoading = true; stopError = ''; stopDetail = null; renderLiveStops();
    const params = new URLSearchParams({routeId: stopRoute, rDirection: stopDirection});
    if (tripId) params.set('tId', tripId);
    try {
        const data = await stopRequest(`${routeStopsUrl}?${params}`);
        if (id !== stopRequestId) return;
        if (!data.route || !Array.isArray(data.stops) || !Array.isArray(data.trips) || !Array.isArray(data.times) || data.direction !== stopDirection) throw new Error('站序或時間資料格式不正確。');
        stopDetail = data;
    } catch (error) { if (id === stopRequestId) stopError = error.message; }
    finally { if (id === stopRequestId) { stopLoading = false; renderLiveStops(); } }
}

function openLiveStopEditor(stationId = null) {
    if (!stopDetail || stopWriting || stopLoading) return;
    const old = stationId === null ? null : stopDetail.stops.find(s => s.stationId === stationId);
    if (stationId !== null && !old) return;
    stopEditing = old ? {...old} : null;
    el('form-title').textContent = old ? '編輯站序' : '新增站序'; el('error').textContent = '';
    el('fields').innerHTML = `<label>路線<input class="member-readonly" value="${esc(stopDetail.route.routeId)} · ${esc(stopDetail.route.routeName)}" readonly></label>
        <label>站點<select name="stationId" required><option value="">請選擇站點</option>${stopStations.map(s => `<option value="${esc(s.stationId)}" ${old?.stationId === s.stationId ? 'selected' : ''}>${esc(s.stationId)} · ${esc(s.sName)}</option>`).join('')}</select></label>
        <label>行駛方向<select name="rDirection">${['去程','回程'].map(d => `<option value="${d}" ${(old?.rDirection || stopDirection) === d ? 'selected' : ''}>${directionLabel(d)}</option>`).join('')}</select></label>
        <label>站序<input name="stopSequence" type="number" min="1" max="2147483647" step="1" value="${old?.stopSequence || Math.max(0,...stopDetail.stops.map(s => s.stopSequence))+1}" required></label>`;
    el('editor').showModal();
}

function openLiveTimeEditor(stationId) {
    if (!stopDetail?.selectedTripId || stopWriting) return;
    const station = stopDetail.stops.find(s => s.stationId === stationId); if (!station) return;
    const time = stopDetail.times.find(t => t.stationId === stationId);
    timeEditing = {tId:stopDetail.selectedTripId,stationId};
    el('stop-time-title').textContent = `${station.sName} · 到離站時間`;
    el('stop-time-context').textContent = `${timeEditing.tId} · ${directionLabel(stopDirection)}；完整日期時間，跨日請選隔日日期。`;
    el('stop-arrival').value = time?.expArrivalTime || ''; el('stop-departure').value = time?.expDepartureTime || '';
    el('stop-time-error').textContent = ''; el('clear-stop-time').hidden = !time?.expArrivalTime;
    el('stop-time-editor').showModal();
}

function setStopWriting(writing) {
    stopWriting = writing;
    for (const id of ['form','stop-time-form']) for (const control of el(id).querySelectorAll('button')) control.disabled = writing;
    renderLiveStops();
}

async function writeLiveStop(url, method, data, dialogId, errorId) {
    if (stopWriting) return;
    const tripId = stopDetail?.selectedTripId;
    setStopWriting(true); stopError = ''; if (errorId) el(errorId).textContent = '';
    let success = false;
    try { const result = await stopRequest(url,{method,body:JSON.stringify(data)}); success = true; if(dialogId) el(dialogId).close(); toast(result.message); }
    catch(error) { if(errorId) el(errorId).textContent = error.message; else stopError = error.message; }
    finally { setStopWriting(false); }
    if (success) await loadStopDetail(tripId);
}

el('section-name').textContent = 'SCHEDULE / 班表調度'; el('title').textContent = '路線站序與去返程';
el('description').textContent = '先選擇路線，再查看與設定去程、返程的停靠站順序及各班次到離站時間。';
el('add').textContent = '＋ 新增站序'; stopSubmit.textContent = '儲存至資料庫';
el('content').innerHTML = `<div class="panel"><div class="toolbar"><input id="search" type="search" aria-label="搜尋路線" disabled><button class="btn" id="stop-reload" type="button">重新載入</button></div><p id="stop-status" class="count" role="status" aria-live="polite"></p><div id="table" class="table-wrap"></div><div class="foot"><span id="total"></span><span>PostgreSQL 站序與班次時間</span></div></div>`;
el('search').oninput = e => {stopQuery=e.target.value.trim();renderLiveStops();};
el('stop-reload').onclick = loadStopOptions; el('add').onclick = () => openLiveStopEditor();
el('cancel').onclick = () => {if(!stopWriting)el('editor').close();};
el('cancel-stop-time').onclick = () => {if(!stopWriting)el('stop-time-editor').close();};
for (const id of ['editor','stop-time-editor']) el(id).addEventListener('cancel',e=>{if(stopWriting)e.preventDefault();});
el('table').onclick = async e => {
    const b=e.target.closest('button'); if(!b || b.disabled || stopWriting || stopLoading)return;
    if(b.hasAttribute('data-route')){stopRoute=b.dataset.route;stopDirection='去程';stopQuery='';el('search').value='';await loadStopDetail();return;}
    if(b.hasAttribute('data-back')){stopRoute='';stopDetail=null;stopQuery='';el('search').value='';renderLiveStops();return;}
    if(b.hasAttribute('data-direction')){stopDirection=b.dataset.direction;stopQuery='';el('search').value='';await loadStopDetail();return;}
    if(b.hasAttribute('data-time-station')){openLiveTimeEditor(b.dataset.timeStation);return;}
    if(b.hasAttribute('data-stop-edit')){openLiveStopEditor(b.dataset.stopEdit);return;}
    if(b.hasAttribute('data-stop-delete') && confirm('確定刪除此方向的停靠站設定？若有班次時間，必須先清除相關時間；站點本身不會刪除。'))
        await writeLiveStop(routeStopsUrl,'DELETE',{routeId:stopRoute,stationId:b.dataset.stopDelete,rDirection:stopDirection});
};
el('form').onsubmit = async e => {
    e.preventDefault(); if(stopWriting || !stopDetail)return;
    const f=new FormData(e.target), sequence=Number(f.get('stopSequence')), stationId=String(f.get('stationId')), rDirection=String(f.get('rDirection'));
    if(!stopStations.some(s=>s.stationId===stationId) || !Number.isInteger(sequence) || sequence<1 || sequence>2147483647){el('error').textContent='請選擇站點並填寫正整數站序。';return;}
    const data={routeId:stopRoute,stationId,rDirection,stopSequence:sequence};
    if(stopEditing){data.old_stationId=stopEditing.stationId;data.old_rDirection=stopEditing.rDirection;}
    await writeLiveStop(routeStopsUrl,stopEditing?'PATCH':'POST',data,'editor','error');
};
el('stop-time-form').onsubmit = async e => {
    e.preventDefault();if(!timeEditing || stopWriting)return;
    const arrival=el('stop-arrival').value,departure=el('stop-departure').value;
    if(!arrival || !departure || new Date(departure)<new Date(arrival)){el('stop-time-error').textContent='請填寫完整日期時間，離站不得早於到站。';return;}
    await writeLiveStop(stopTimesUrl,'PUT',{...timeEditing,expArrivalTime:arrival,expDepartureTime:departure},'stop-time-editor','stop-time-error');
};
el('clear-stop-time').onclick = async () => {
    if(timeEditing && !stopWriting && confirm('確定清除此班次在本站的到離站時間？站序不會刪除。'))
        await writeLiveStop(stopTimesUrl,'DELETE',timeEditing,'stop-time-editor','stop-time-error');
};
loadStopOptions();
