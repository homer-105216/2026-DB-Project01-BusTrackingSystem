// 站序頁先選路線，再依方向顯示站點；保留原始索引供編輯與刪除。
function renderStops(){
    el('add').hidden=!route;
    const search=el('search');
    search.placeholder=route?'搜尋站點編號或名稱…':'搜尋路線編號或名稱…';
    search.setAttribute('aria-label',route?'搜尋站點':'搜尋路線');
    if(!route){
        const routes=db.routes.filter(r=>[r.routeId,r.routeName,r.origin,r.destination].some(v=>String(v).toLowerCase().includes(query.toLowerCase())));
        el('table').innerHTML='<div class="route-cards">'+routes.map(r=>`<button class="route-choice" data-route="${esc(r.routeId)}"><span>${esc(r.routeId)}</span><strong>${esc(r.routeName)}</strong><span>${esc(r.origin)} → ${esc(r.destination)}</span><span>查看站點與順序 →</span></button>`).join('')+'</div>'+(routes.length?'':'<div class="empty">沒有符合條件的路線，請調整搜尋或先到路線管理新增路線。</div>');
        el('total').textContent=`共 ${routes.length} 條路線`;
        return;
    }
    const selected=db.routes.find(r=>r.routeId===route);
    const all=db.stops.map((r,i)=>({r,i})).filter(({r})=>r.routeId===route&&r.rDirection===direction).sort((a,b)=>Number(a.r.stopSequence)-Number(b.r.stopSequence));
    const rows=all.filter(({r})=>{const station=db.stations.find(s=>s.stationId===r.stationId);return [r.stationId,station?.sName].some(v=>String(v??'').toLowerCase().includes(query.toLowerCase()))});
    el('table').innerHTML=`<button class="btn" data-back>← 返回路線清單</button><div class="route-detail-heading"><h2>${esc(selected?.routeName??route)}</h2><p>${esc(selected?.origin)} → ${esc(selected?.destination)}</p></div><div class="direction-tabs" aria-label="行駛方向">${['去程','返程'].map(d=>`<button class="btn ${direction===d?'selected':''}" aria-pressed="${direction===d}" data-direction="${d}">${d}</button>`).join('')}</div><ol class="stop-list">${rows.map(({r,i})=>{const station=db.stations.find(s=>s.stationId===r.stationId);return `<li class="stop-item"><span class="stop-number" aria-label="站序 ${esc(r.stopSequence)}">${esc(r.stopSequence)}</span><div class="stop-info"><strong>${esc(station?.sName??r.stationId)}</strong><small>${esc(r.stationId)}</small></div><div class="stop-actions"><button class="btn" data-edit="${i}">編輯</button><button class="btn danger" data-delete="${i}">刪除</button></div></li>`}).join('')}</ol>${rows.length?'':`<div class="empty">${query?'沒有符合條件的站點。':'此方向尚未設定站點，請點右上角「新增站序」。'}</div>`}`;
    el('total').textContent=`${direction}：顯示 ${rows.length} 站 / 共 ${all.length} 站`;
}



initManagement();
