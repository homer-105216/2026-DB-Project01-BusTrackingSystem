// 班次頁：先選路線，再以兩張表分別管理去程與返程。
function renderTrips(){
    el('add').hidden=!route;
    el('search').placeholder=route?'搜尋班次編號或發車時間…':'搜尋路線編號或名稱…';
    el('search').setAttribute('aria-label',route?'搜尋班次':'搜尋路線');
    if(!route){
        const routes=db.routes.filter(r=>[r.routeId,r.routeName,r.origin,r.destination].some(v=>String(v).toLowerCase().includes(query.toLowerCase())));
        el('table').innerHTML='<div class="route-cards">'+routes.map(r=>`<button class="route-choice" data-route="${esc(r.routeId)}"><span>${esc(r.routeId)}</span><strong>${esc(r.routeName)}</strong><span>${esc(r.origin)} → ${esc(r.destination)}</span><span>查看去返程班次 →</span></button>`).join('')+'</div>'+(routes.length?'':'<div class="empty">沒有符合條件的路線，請調整搜尋或先到路線管理新增路線。</div>');
        el('total').textContent=`共 ${routes.length} 條路線`;return;
    }
    const selected=db.routes.find(r=>r.routeId===route);
    const all=db.trips.map((r,i)=>({r,i})).filter(({r})=>r.routeId===route);
    const rows=all.filter(({r})=>[r.tId,r.departureTime].some(v=>String(v).toLowerCase().includes(query.toLowerCase())));
    el('table').innerHTML=`<button class="btn" data-back>← 返回路線清單</button><div class="route-detail-heading"><h2>${esc(selected?.routeName??route)}</h2><p>每列是一筆預定發車班次，依發車時間排序。</p></div>`+['去程','返程'].map(d=>{
        const trips=rows.filter(({r})=>r.tDirection===d).sort((a,b)=>a.r.departureTime.localeCompare(b.r.departureTime)||a.r.tId.localeCompare(b.r.tId));
        const origin=d==='去程'?selected?.origin:selected?.destination,destination=d==='去程'?selected?.destination:selected?.origin;
        return `<section class="trip-direction"><div class="heading"><div><h2>${d} <span class="count">${trips.length} 班</span></h2><p>${esc(origin)} → ${esc(destination)}</p></div><button class="btn" data-add-direction="${d}">＋ 新增${d}班次</button></div><div class="table-wrap"><table><caption class="trip-caption">${esc(selected?.routeName??route)} · ${d}發車班次</caption><thead><tr><th scope="col">班次編號</th><th scope="col">發車時間</th><th scope="col">操作</th></tr></thead><tbody>${trips.map(({r,i})=>`<tr><td>${esc(r.tId)}</td><td>${esc(r.departureTime)}</td><td><button data-edit="${i}">編輯</button><button class="danger" data-delete="${i}">刪除</button></td></tr>`).join('')}</tbody></table>${trips.length?'':`<div class="empty">${query?'沒有符合搜尋條件的班次。':`尚未設定${d}班次，可點選上方按鈕新增。`}</div>`}</div></section>`;
    }).join('');
    el('total').textContent=`顯示 ${rows.length} 筆 / 此路線共 ${all.length} 筆班次`;
}


initManagement();
