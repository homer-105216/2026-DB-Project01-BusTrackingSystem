// 同一使用者對同一項目只計一次；忽略已不存在的路線或站點。
function favoriteRanking(items,favorites,idKey,nameKey){
    const members=new Map(items.map(item=>[String(item[idKey]),new Set()]));
    for(const row of favorites){
        if(row&&row.mId!==undefined&&row.mId!==null&&String(row.mId)!=='')members.get(String(row[idKey]))?.add(String(row.mId));
    }
    return items.map(item=>({id:String(item[idKey]),name:item[nameKey],members:members.get(String(item[idKey])),count:members.get(String(item[idKey])).size}))
        .sort((a,b)=>b.count-a.count||a.id.localeCompare(b.id));
}

function favoriteChart(rows,limit){
    const visible=rows.filter(r=>r.count>0).slice(0,limit);
    if(!visible.length)return '<div class="empty">目前尚無收藏資料。</div>';
    const max=visible[0].count;
    return '<div class="favorite-axis">依收藏人數排序 · 單位：人</div><ol class="favorite-ranking">'+visible.map((r,i)=>`<li class="favorite-row"><span class="favorite-rank">${i+1}</span><div class="favorite-detail"><strong>${esc(r.name)}</strong><small>${esc(r.id)}</small><div class="bar-track" role="img" aria-label="${esc(r.name)}：${r.count} 人收藏"><div class="bar" style="width:${r.count/max*100}%"></div></div></div><strong class="favorite-count">${r.count} 人</strong></li>`).join('')+'</ol>';
}

if(page==='analysis'){
    el('section-name').textContent='ANALYSIS / 統計分析';
    el('title').textContent='熱門收藏排行';
    el('description').textContent='彙整所有使用者的收藏，查看最受歡迎的公車路線與站點。';
    el('content').innerHTML=`<div class="toolbar"><label>顯示排行<select id="rank-limit"><option value="5">前 5 名</option><option value="10">前 10 名</option><option value="all">全部</option></select></label><span class="count">統計目前收藏，不含已取消收藏；同一使用者對同一項目只計一次。</span></div><div id="favorite-stats"></div><div class="favorite-charts"><section class="panel"><h2>熱門收藏路線</h2><div id="favorite-route-chart"></div></section><section class="panel"><h2>熱門收藏站點</h2><div id="favorite-station-chart"></div></section></div><p class="favorite-note">此頁為示範排行，尚未連接正式使用者收藏資料。收藏人數相同時依編號排序。</p>`;
    function renderFavoriteAnalysis(){
        const routes=favoriteRanking(db.routes,db.favoriteRoutes,'routeId','routeName');
        const stations=favoriteRanking(db.stations,db.favoriteStations,'stationId','sName');
        const users=new Set([...routes,...stations].flatMap(r=>[...r.members]));
        el('favorite-stats').innerHTML=cards([
            ['參與收藏使用者',users.size,'至少收藏一條路線或一個站點'],
            ['路線收藏總數',routes.reduce((n,r)=>n+r.count,0),'每位使用者對每條路線計一次'],
            ['站點收藏總數',stations.reduce((n,r)=>n+r.count,0),'每位使用者對每個站點計一次'],
            ['被收藏的項目',routes.filter(r=>r.count>0).length+stations.filter(r=>r.count>0).length,'路線與站點合計']
        ]);
        const limit=el('rank-limit').value==='all'?Infinity:Number(el('rank-limit').value||5);
        el('favorite-route-chart').innerHTML=favoriteChart(routes,limit);
        el('favorite-station-chart').innerHTML=favoriteChart(stations,limit);
    }
    el('rank-limit').onchange=renderFavoriteAnalysis;
    renderFavoriteAnalysis();
}
