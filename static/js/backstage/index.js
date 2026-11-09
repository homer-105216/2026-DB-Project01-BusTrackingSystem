// 總覽統計由資料庫 API 計算，不使用示範 db 的筆數。
let overviewLoading=false;
el('section-name').textContent='OPERATIONS / 營運總覽';el('title').hidden=true;
el('description').textContent='從基礎資料到每日調度，在這裡掌握公車營運。';
el('content').innerHTML=`<div class="toolbar"><button class="btn" id="overview-reload" type="button">重新載入</button><span id="overview-status" class="count" role="status" aria-live="polite"></span></div><div id="overview-summary"></div><div class="grid-two"><div class="panel"><h2>快速開始</h2><div class="quick">${['routes','bus-types','trips','dispatch'].map(k=>`<a href="${url(k)}"><strong>${configs[k].title} →</strong><p>${configs[k].desc}</p></a>`).join('')}</div></div><div class="panel"><h2>各路線預定班次</h2><div id="overview-trips"></div></div></div>`;
async function loadOverview(){
 if(overviewLoading)return;overviewLoading=true;el('overview-reload').disabled=true;
 el('overview-summary').innerHTML='';el('overview-trips').innerHTML='';el('overview-status').textContent='正在讀取資料庫統計…';el('overview-status').setAttribute('role','status');
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch(overviewApiUrl,{signal:controller.signal,cache:'no-store',headers:{Accept:'application/json'}});
  const data=await response.json();if(!response.ok||data.status!=='ok')throw new Error(data.message||'無法取得總覽資料。');
  const s=data.summary,valid=n=>Number.isSafeInteger(n)&&n>=0;
  if(!s||!['routeCount','stationCount','busCount','busTypeCount','tripCount'].every(k=>valid(s[k]))||!Array.isArray(data.routeTrips)||!data.routeTrips.every(r=>typeof r.routeId==='string'&&typeof r.routeName==='string'&&valid(r.totalCount)))throw new Error('營運總覽資料格式不正確。');
  el('overview-summary').innerHTML=cards([['服務路線',s.routeCount,'已建立的路線'],['營運站點',s.stationCount,'可供路線設定使用'],['車隊規模',s.busCount,`${s.busTypeCount} 種車型`],['預定班次',s.tripCount,'固定發車班次']]);
  el('overview-trips').innerHTML=bars(data.routeTrips.map(r=>[r.routeName,r.totalCount]));
  el('overview-status').textContent='已載入 PostgreSQL 統計';
 }catch(error){
  el('overview-status').textContent=(error.name==='AbortError'||error instanceof TypeError||error instanceof SyntaxError)?'無法讀取營運總覽，請確認 Flask 與資料庫連線後重試。':error.message;el('overview-status').setAttribute('role','alert');
 }finally{clearTimeout(timer);overviewLoading=false;el('overview-reload').disabled=false;}
}
el('overview-reload').onclick=loadOverview;loadOverview();
