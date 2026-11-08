// 所有統計由 API 執行 api/sql.py 的彙總查詢，不讀取示範 db。
let analysisData=null,analysisLoading=false;
function favoriteChart(rows,limit){
    const visible=rows.filter(r=>r.count>0).slice(0,limit);
    if(!visible.length)return '<div class="empty">目前尚無收藏資料。</div>';
    const max=visible[0].count;
    return '<div class="favorite-axis">依收藏人數排序 · 單位：人</div><ol class="favorite-ranking">'+visible.map((r,i)=>`<li class="favorite-row"><span class="favorite-rank">${i+1}</span><div class="favorite-detail"><strong>${esc(r.name)}</strong><small>${esc(r.id)}</small><div class="bar-track" role="img" aria-label="${esc(r.name)}：${r.count} 人收藏"><div class="bar" style="width:${r.count/max*100}%"></div></div></div><strong class="favorite-count">${r.count} 人</strong></li>`).join('')+'</ol>';
}

function registrationChart(rows){
    const width=900,height=260,left=45,right=15,top=25,bottom=42;
    const plotWidth=width-left-right,plotHeight=height-top-bottom,max=Math.max(1,...rows.map(r=>r.count));
    const step=plotWidth/rows.length,barWidth=Math.max(2,step*.62);
    const ticks=[...new Set([0,Math.ceil(max/2),max])];
    return `<svg class="registration-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="所選期間每日新增使用者人數長條圖，完整數據可於下方展開查看。">
        <text x="${left}" y="14" class="chart-label">人數</text>
        ${ticks.map(n=>{const y=top+plotHeight*(1-n/max);return `<line x1="${left}" y1="${y}" x2="${width-right}" y2="${y}" class="chart-grid"/><text x="${left-10}" y="${y+4}" text-anchor="end" class="chart-label">${n}</text>`}).join('')}
        ${rows.map((row,i)=>{const h=row.count/max*plotHeight,x=left+step*i+(step-barWidth)/2;return `<rect x="${x}" y="${top+plotHeight-h}" width="${barWidth}" height="${h}" rx="2" class="registration-bar"><title>${row.date}：${row.count} 人</title></rect>`}).join('')}
        ${rows.map((row,i)=>i===0||i===rows.length-1||i%Math.ceil(rows.length/6)===0?`<text x="${left+step*(i+.5)}" y="${height-15}" text-anchor="middle" class="chart-label">${row.date.slice(5).replace('-','/')}</text>`:'').join('')}
        </svg>`;
}

function renderTripComparison(){
    const order=el('trip-comparison-order').value;
    const rows=analysisData.tripComparison.map(r=>({id:r.routeId,name:r.routeName,outbound:r.outboundCount,inbound:r.inboundCount,total:r.totalCount})).sort((a,b)=>
        (order==='most'?b.total-a.total:order==='least'?a.total-b.total:0)||a.id.localeCompare(b.id));
    if(!rows.length){
        el('trip-comparison-chart').innerHTML='<div class="empty">尚無路線資料，請先到路線管理新增路線。</div>';
        el('trip-comparison-table').innerHTML='';return;
    }
    const max=Math.max(1,...rows.flatMap(r=>[r.outbound,r.inbound]));
    el('trip-comparison-chart').innerHTML=rows.map(row=>`<div class="trip-compare-row">
        <div class="trip-compare-name"><strong>${esc(row.name)}</strong><small>${esc(row.id)} · 合計 ${row.total} 班</small></div>
        <div class="trip-compare-bars">${[['去程',row.outbound,'outbound'],['返程',row.inbound,'inbound']].map(([label,count,kind])=>`
            <div class="trip-compare-series"><span>${label}</span><div class="bar-track" role="img" aria-label="${esc(row.name)}${label}：${count} 班">
                <div class="bar ${kind}" style="width:${count/max*100}%"></div></div><strong>${count} 班</strong></div>`).join('')}
        </div></div>`).join('');
    el('trip-comparison-table').innerHTML='<table><thead><tr><th scope="col">路線</th><th scope="col">去程班次</th><th scope="col">返程班次</th><th scope="col">合計</th></tr></thead><tbody>'+rows.map(row=>`<tr><td>${esc(row.id)} · ${esc(row.name)}</td><td>${row.outbound}</td><td>${row.inbound}</td><td>${row.total}</td></tr>`).join('')+'</tbody></table>';
}


el('section-name').textContent='ANALYSIS / 統計分析';
el('title').textContent='營運統計分析';
el('description').textContent='查看使用者註冊成長、各路線預定班次，以及熱門收藏路線與站點。';
    el('content').innerHTML=`
        <div class="toolbar"><button id="analysis-reload" class="btn" type="button">重新載入</button><span id="analysis-status" class="count" role="status" aria-live="polite"></span></div><div class="toolbar"><label>使用者統計期間<select id="user-period"><option value="7">近 7 天</option><option value="30" selected>近 30 天</option><option value="90">近 90 天</option></select></label>
            <span class="count">含今天；使用者總數不受期間篩選影響，所有使用者統計皆排除管理者。</span></div>
        <div class="user-stat-cards" id="user-stats"></div>
        <section class="panel registration-panel"><h2>每日新增使用者</h2><p id="registration-range" class="count"></p>
            <div id="registration-chart"></div><p id="registration-empty" class="count"></p>
            <details class="registration-data"><summary>查看每日數據</summary><div class="table-wrap" id="registration-table"></div></details>
        </section>
        <section class="panel trip-comparison-panel"><h2>各路線去返程預定班次比較</h2>
            <p class="count">依目前預定班次計算，非當日實際發車數；不受上方使用者統計期間影響。班次少不一定代表服務不足。</p>
            <div class="toolbar trip-comparison-toolbar"><label>排列方式<select id="trip-comparison-order">
                <option value="least">班次由少到多</option><option value="most">班次由多到少</option><option value="id">依路線編號</option></select></label>
                <div class="trip-comparison-legend"><span><i class="outbound"></i>去程</span><span><i class="inbound"></i>返程</span></div></div>
            <div id="trip-comparison-chart"></div>
            <details class="registration-data"><summary>查看班次數據</summary><div class="table-wrap" id="trip-comparison-table"></div></details>
        </section>
        <div class="toolbar"><label>收藏排行<select id="rank-limit"><option value="5">前 5 名</option><option value="10">前 10 名</option><option value="all">全部</option></select></label>
            <span class="count">收藏排行計全部有效收藏，包含管理者，不受註冊期間影響；同一使用者對同一項目只計一次。</span></div>
        <div class="favorite-charts"><section class="panel"><h2>熱門收藏路線</h2><div id="favorite-route-chart"></div></section>
            <section class="panel"><h2>熱門收藏站點</h2><div id="favorite-station-chart"></div></section></div>
        <p class="favorite-note">資料來自 PostgreSQL。註冊統計以目前保留的一般會員資料計算，已刪除會員不計入；日期按台北時間，依資料庫儲存的註冊日期統計。收藏人數相同時依編號排序。</p>`;


function clearAnalysisCharts(){
 for(const id of ['user-stats','registration-chart','registration-table','trip-comparison-chart','trip-comparison-table','favorite-route-chart','favorite-station-chart'])el(id).innerHTML='';
 el('registration-range').textContent='';el('registration-empty').textContent='';
}
function renderUserAnalysis(){
 const trend=analysisData.userGrowth,rows=trend.daily.map(r=>({date:r.registrationDate,count:r.newUserCount}));
 el('user-stats').innerHTML=cards([
  ['使用者總數',trend.userCount,'目前一般會員總數，不含管理者'],
  [`近 ${trend.days} 天新增使用者`,trend.newUserCount,'依一般會員註冊日期計算，不含管理者']
 ]);
 el('registration-range').textContent=`${trend.startDate} 至 ${trend.endDate} · 台北時間 · 單位：人`;
 el('registration-chart').innerHTML=registrationChart(rows);
 el('registration-empty').textContent=trend.newUserCount?'':'此期間沒有新增使用者。';
 el('registration-table').innerHTML='<table><thead><tr><th scope="col">註冊日期</th><th scope="col">新增人數</th></tr></thead><tbody>'+rows.map(r=>`<tr><td>${esc(r.date)}</td><td>${r.count}</td></tr>`).join('')+'</tbody></table>';
}
function renderFavoriteAnalysis(){
 const routes=analysisData.favorites.routes.map(r=>({id:r.routeId,name:r.routeName,count:r.favoriteCount}));
 const stations=analysisData.favorites.stations.map(r=>({id:r.stationId,name:r.sName,count:r.favoriteCount}));
 el('favorite-route-chart').innerHTML=favoriteChart(routes,Infinity);
 el('favorite-station-chart').innerHTML=favoriteChart(stations,Infinity);
}
const nonnegative=n=>Number.isSafeInteger(n)&&n>=0;
function validAnalysis(data){
 const g=data.userGrowth;
 return g&&nonnegative(g.userCount)&&nonnegative(g.newUserCount)&&[7,30,90].includes(g.days)&&
  /^\d{4}-\d{2}-\d{2}$/.test(g.startDate)&&/^\d{4}-\d{2}-\d{2}$/.test(g.endDate)&&Array.isArray(g.daily)&&g.daily.length===g.days&&g.daily.every(r=>/^\d{4}-\d{2}-\d{2}$/.test(r.registrationDate)&&nonnegative(r.newUserCount))&&
  g.daily.reduce((s,r)=>s+r.newUserCount,0)===g.newUserCount&&Array.isArray(data.tripComparison)&&data.tripComparison.every(r=>typeof r.routeId==='string'&&typeof r.routeName==='string'&&[r.outboundCount,r.inboundCount,r.totalCount].every(nonnegative)&&r.totalCount===r.outboundCount+r.inboundCount)&&
  data.favorites&&data.favorites.scope==='all-valid-members'&&['routes','stations'].every(kind=>Array.isArray(data.favorites[kind])&&data.favorites[kind].every(r=>typeof r[kind==='routes'?'routeId':'stationId']==='string'&&typeof r[kind==='routes'?'routeName':'sName']==='string'&&nonnegative(r.favoriteCount)&&r.favoriteCount>0));
}
async function loadAnalysis(){
 if(analysisLoading)return;analysisLoading=true;analysisData=null;clearAnalysisCharts();
 for(const id of ['user-period','rank-limit','trip-comparison-order','analysis-reload'])el(id).disabled=true;
 el('analysis-status').textContent='正在讀取資料庫統計…';el('analysis-status').setAttribute('role','status');
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{
  const params=new URLSearchParams({days:el('user-period').value,limit:el('rank-limit').value,order:el('trip-comparison-order').value});
  const response=await fetch(`${analysisApiUrl}?${params}`,{signal:controller.signal,cache:'no-store',headers:{Accept:'application/json'}});
  const data=await response.json();if(!response.ok||data.status!=='ok')throw new Error(data.message||'無法取得統計資料。');
  if(!validAnalysis(data))throw new Error('統計資料格式不正確，請確認 API 回傳欄位與統計口徑。');
  analysisData=data;renderUserAnalysis();renderTripComparison();renderFavoriteAnalysis();el('analysis-status').textContent='已載入 PostgreSQL 統計';
 }catch(error){
  clearAnalysisCharts();el('analysis-status').textContent=(error.name==='AbortError'||error instanceof TypeError||error instanceof SyntaxError)?'無法讀取統計，請確認 Flask 與資料庫連線後重新載入。':error.message;el('analysis-status').setAttribute('role','alert');
 }finally{
  clearTimeout(timer);analysisLoading=false;for(const id of ['user-period','rank-limit','trip-comparison-order','analysis-reload'])el(id).disabled=false;
 }
}
el('user-period').onchange=loadAnalysis;el('rank-limit').onchange=loadAnalysis;
el('trip-comparison-order').onchange=()=>{if(analysisData)renderTripComparison();};el('analysis-reload').onclick=loadAnalysis;
loadAnalysis();
