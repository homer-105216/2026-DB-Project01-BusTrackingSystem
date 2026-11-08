// 固定班次資料來自 Trip；不讀寫示範 db 或 localStorage。
let tripRoutes=[], liveTrips=[], tripRoute='', tripRouteData=null, tripQuery='', tripCsrf='';
let tripReady=false, tripLoaded=false, tripLoading=false, tripWriting=false, tripError='', tripEditing=null;
const tripSubmit=el('form').querySelector('button[type=submit]');
const tripDirectionLabel=d=>d==='回程'?'返程':d;
async function tripRequest(url,options={}){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch(url,{...options,signal:controller.signal,cache:'no-store',headers:{Accept:'application/json',...(options.method?{'Content-Type':'application/json','X-CSRF-Token':tripCsrf}:{}),...(options.headers||{})}});
  const data=await response.json();if(!response.ok||data.status!=='ok')throw new Error(data.message||'預定班次操作失敗。');return data;
 }catch(error){
  if(error.name==='AbortError'||error instanceof TypeError||error instanceof SyntaxError)throw new Error(options.method?'連線中斷，請重新載入確認資料是否已更新，再決定是否重試。':'無法讀取班次資料，請確認 Flask 與資料庫連線後重試。');
  throw error;
 }finally{clearTimeout(timer);}
}
function renderLiveTrips(){
 el('add').hidden=!tripRoute;el('add').disabled=!tripLoaded||tripLoading||tripWriting;
 el('trip-reload').disabled=tripLoading||tripWriting;el('search').disabled=!tripReady||tripLoading||tripWriting;
 el('search').placeholder=tripRoute?'搜尋班次編號或發車時間…':'搜尋路線編號或名稱…';el('search').setAttribute('aria-label',tripRoute?'搜尋班次':'搜尋路線');
 el('trip-status').textContent=tripLoading?'正在讀取資料庫預定班次…':tripError;el('trip-status').setAttribute('role',tripError?'alert':'status');el('total').textContent='';
 if(!tripReady||tripLoading){el('table').innerHTML='';return;}
 if(!tripRoute){
  const routes=tripRoutes.filter(r=>[r.routeId,r.routeName,r.origin,r.destination].some(v=>String(v).toLowerCase().includes(tripQuery.toLowerCase())));
  el('table').innerHTML='<div class="route-cards">'+routes.map(r=>`<button class="route-choice" data-route="${esc(r.routeId)}"><span>${esc(r.routeId)}</span><strong>${esc(r.routeName)}</strong><span>${esc(r.origin)} → ${esc(r.destination)}</span><span>查看去返程班次 →</span></button>`).join('')+'</div>'+(routes.length?'':'<div class="empty">沒有符合條件的路線，請調整搜尋或先到路線管理新增路線。</div>');
  el('total').textContent=`共 ${routes.length} 條路線`;return;
 }
 const selected=tripRouteData||tripRoutes.find(r=>r.routeId===tripRoute);
 const rows=liveTrips.filter(t=>[t.tId,t.departureTime].some(v=>String(v).toLowerCase().includes(tripQuery.toLowerCase())));
 el('table').innerHTML=`<button class="btn" data-back ${tripWriting?'disabled':''}>← 返回路線清單</button><div class="route-detail-heading"><h2>${esc(selected?.routeName||tripRoute)}</h2><p>每列是一筆預定發車班次，依發車時間排序。</p></div>`+(!tripLoaded?'<div class="empty">班次讀取失敗，請重新載入或返回路線清單。</div>':['去程','回程'].map(d=>{
  const trips=rows.filter(t=>t.tDirection===d).sort((a,b)=>a.departureTime.localeCompare(b.departureTime)||a.tId.localeCompare(b.tId));
  const origin=d==='去程'?selected?.origin:selected?.destination,destination=d==='去程'?selected?.destination:selected?.origin;
  return `<section class="trip-direction"><div class="heading"><div><h2>${tripDirectionLabel(d)} <span class="count">${trips.length} 班</span></h2><p>${esc(origin||'')} → ${esc(destination||'')}</p></div><button class="btn" data-add-direction="${d}" ${tripWriting?'disabled':''}>＋ 新增${tripDirectionLabel(d)}班次</button></div><div class="table-wrap"><table><caption class="trip-caption">${esc(selected?.routeName||tripRoute)} · ${tripDirectionLabel(d)}發車班次</caption><thead><tr><th scope="col">班次編號</th><th scope="col">發車時間</th><th scope="col">操作</th></tr></thead><tbody>${trips.map(t=>`<tr><td>${esc(t.tId)}</td><td>${esc(t.departureTime)}</td><td><button data-trip-edit="${esc(t.tId)}" ${tripWriting?'disabled':''}>編輯</button><button class="danger" data-trip-delete="${esc(t.tId)}" ${tripWriting?'disabled':''}>刪除</button></td></tr>`).join('')}</tbody></table>${trips.length?'':`<div class="empty">${tripQuery?'沒有符合搜尋條件的班次。':`尚未設定${tripDirectionLabel(d)}班次，可點選上方按鈕新增。`}</div>`}</div></section>`;
 }).join(''));
 if(tripLoaded)el('total').textContent=`顯示 ${rows.length} 筆 / 此路線共 ${liveTrips.length} 筆班次`;
}
async function loadTripRoutes(){
 if(tripLoading||tripWriting)return;tripLoading=true;tripReady=false;tripError='';tripLoaded=false;liveTrips=[];renderLiveTrips();
 try{const data=await tripRequest(tripRoutesUrl);if(!Array.isArray(data.routes))throw new Error('路線資料格式不正確。');tripRoutes=data.routes;tripReady=true;if(tripRoute&&!tripRoutes.some(r=>r.routeId===tripRoute))tripRoute='';}
 catch(error){tripError=error.message;}finally{tripLoading=false;renderLiveTrips();}
 if(tripReady&&tripRoute)await loadDatabaseTrips();
}
async function loadDatabaseTrips(){
 if(!tripRoute||tripLoading||tripWriting)return;tripLoading=true;tripLoaded=false;liveTrips=[];tripError='';tripRouteData=null;renderLiveTrips();
 try{
  const data=await tripRequest(`${tripsApiUrl}?${new URLSearchParams({routeId:tripRoute})}`);
  if(!data.route||!Array.isArray(data.trips)||typeof data.csrfToken!=='string'||!data.trips.every(t=>['tId','routeId','departureTime','tDirection'].every(k=>typeof t[k]==='string')&&t.routeId===tripRoute&&['去程','回程'].includes(t.tDirection)))throw new Error('班次資料格式不正確，請確認 API 欄位與方向。');
  liveTrips=data.trips;tripRouteData=data.route;tripCsrf=data.csrfToken;tripLoaded=true;
 }catch(error){tripError=error.message;}finally{tripLoading=false;renderLiveTrips();}
}
function openLiveTripEditor(id=null,direction='去程'){
 if(!tripLoaded||tripWriting||tripLoading)return;const row=id===null?null:liveTrips.find(t=>t.tId===id);if(id!==null&&!row)return;tripEditing=id;
 el('form-title').textContent=row?'編輯預定班次':'新增預定班次';el('error').textContent='';
 el('fields').innerHTML=`<label>班次編號<input name="tId" maxlength="50" value="${esc(row?.tId||'')}" required ${row?'readonly class="member-readonly"':''}></label>
 <label>路線<select name="routeId" required>${tripRoutes.map(r=>`<option value="${esc(r.routeId)}" ${(row?.routeId||tripRoute)===r.routeId?'selected':''}>${esc(r.routeId)} · ${esc(r.routeName)}</option>`).join('')}</select></label>
 <label>發車時間<input name="departureTime" type="time" step="any" value="${esc(row?.departureTime||'')}" required></label>
 <label>行駛方向<select name="tDirection">${['去程','回程'].map(d=>`<option value="${d}" ${(row?.tDirection||direction)===d?'selected':''}>${tripDirectionLabel(d)}</option>`).join('')}</select></label>`;
 el('editor').showModal();
}
function setTripWriting(value){tripWriting=value;tripSubmit.disabled=value;el('cancel').disabled=value;renderLiveTrips();}
async function writeTrip(method,data,id=null){
 if(tripWriting)return;setTripWriting(true);tripError='';el('error').textContent='';let updated=false;
 try{const response=await tripRequest(id===null?tripsApiUrl:`${tripsApiUrl}/${encodeURIComponent(id)}`,{method,...(data?{body:JSON.stringify(data)}:{})});updated=true;if(method!=='DELETE')el('editor').close();toast(response.message);}
 catch(error){if(method==='DELETE')tripError=error.message;else el('error').textContent=error.message;}
 finally{setTripWriting(false);}
 if(updated)await loadDatabaseTrips();
}
el('section-name').textContent='SCHEDULE / 班表調度';el('title').textContent='預定班次管理';el('description').textContent='設定路線的固定發車時間與行駛方向。';el('add').textContent='＋ 新增班次';tripSubmit.textContent='儲存至資料庫';
el('content').innerHTML=`<div class="panel"><div class="toolbar"><input id="search" type="search" aria-label="搜尋路線" disabled><button id="trip-reload" class="btn" type="button">重新載入</button></div><p id="trip-status" class="count" role="status" aria-live="polite"></p><div id="table" class="table-wrap"></div><div class="foot"><span id="total"></span><span>PostgreSQL 固定預定班次</span></div></div>`;
el('search').oninput=e=>{tripQuery=e.target.value.trim();renderLiveTrips();};el('trip-reload').onclick=loadTripRoutes;el('add').onclick=()=>openLiveTripEditor();el('cancel').onclick=()=>{if(!tripWriting)el('editor').close();};el('editor').addEventListener('cancel',e=>{if(tripWriting)e.preventDefault();});
el('table').onclick=async e=>{
 const b=e.target.closest('button');if(!b||b.disabled||tripWriting||tripLoading)return;
 if(b.hasAttribute('data-route')){tripRoute=b.dataset.route;tripQuery='';el('search').value='';await loadDatabaseTrips();return;}
 if(b.hasAttribute('data-back')){tripRoute='';tripQuery='';el('search').value='';renderLiveTrips();return;}
 if(b.hasAttribute('data-add-direction')){openLiveTripEditor(null,b.dataset.addDirection);return;}
 if(b.hasAttribute('data-trip-edit')){openLiveTripEditor(b.dataset.tripEdit);return;}
 if(b.hasAttribute('data-trip-delete')&&confirm(`確定刪除預定班次「${b.dataset.tripDelete}」？已有各站時間或每日派車紀錄時，資料庫會禁止刪除。`))await writeTrip('DELETE',null,b.dataset.tripDelete);
};
el('form').onsubmit=async e=>{
 e.preventDefault();if(tripWriting)return;const f=new FormData(e.target),data=Object.fromEntries(['tId','routeId','departureTime','tDirection'].map(k=>[k,String(f.get(k)||'').trim()]));
 if(!data.tId||[...data.tId].length>50||!tripRoutes.some(r=>r.routeId===data.routeId)||!data.departureTime){el('error').textContent='請填寫班次編號、路線、發車時間與方向。';return;}
 await writeTrip(tripEditing===null?'POST':'PATCH',data,tripEditing);
};
loadTripRoutes();
