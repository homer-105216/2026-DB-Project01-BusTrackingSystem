// 真實每日派車：精確依日期查詢，不使用最近一次派車或瀏覽器示範資料。
let dispatchRows=[],dispatchRoutes=[],dispatchTrips=[],dispatchBuses=[],dispatchStatuses=[],dispatchCsrf='';
let dispatchDay='',dispatchQuery='',dispatchRoute='',dispatchDirection='',dispatchReady=false,dispatchLoaded=false;
let dispatchLoading=false,dispatchWriting=false,dispatchError='',dispatchEditing=null;
const dispatchSubmit=el('form').querySelector('button[type=submit]');
const dispatchDirectionLabel=d=>d==='回程'?'返程':d;
const dispatchTripLabel=t=>`${t.tId} · ${t.routeName} · ${dispatchDirectionLabel(t.tDirection)} · ${t.departureTime}`;
async function dispatchRequest(url,options={}){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch(url,{...options,signal:controller.signal,cache:'no-store',headers:{Accept:'application/json',...(options.method?{'Content-Type':'application/json','X-CSRF-Token':dispatchCsrf}:{}),...(options.headers||{})}});
  const data=await response.json();if(!response.ok||data.status!=='ok')throw new Error(data.message||'派車操作失敗。');return data;
 }catch(error){
  if(error.name==='AbortError'||error instanceof TypeError||error instanceof SyntaxError)throw new Error(options.method?'連線中斷，請重新載入確認資料是否已更新，再決定是否重試。':'無法讀取派車資料，請確認 Flask 與資料庫連線後重試。');throw error;
 }finally{clearTimeout(timer);}
}
function renderDispatches(){
 el('add').disabled=!dispatchReady||!dispatchLoaded||dispatchLoading||dispatchWriting;
 for(const id of ['dispatch-reload','dispatch-day','dispatch-all'])el(id).disabled=dispatchLoading||dispatchWriting;
 for(const id of ['dispatch-search','dispatch-route','dispatch-direction'])el(id).disabled=!dispatchLoaded||dispatchLoading||dispatchWriting;
 el('dispatch-status').textContent=dispatchLoading?'正在讀取資料庫派車安排…':dispatchError;el('dispatch-status').setAttribute('role',dispatchError?'alert':'status');
 if(!dispatchLoaded||dispatchLoading){el('dispatch-table').innerHTML='';el('dispatch-total').textContent='';return;}
 const rows=dispatchRows.filter(r=>(!dispatchRoute||r.routeId===dispatchRoute)&&(!dispatchDirection||r.tDirection===dispatchDirection)&&[r.date,r.tId,r.routeId,r.routeName,r.departureTime,r.bId,r.driver,r.status,dispatchDirectionLabel(r.tDirection)].some(v=>String(v??'').toLowerCase().includes(dispatchQuery.toLowerCase())));
 el('dispatch-table').innerHTML=`<table><thead><tr>${['日期','班次編號','路線','方向','發車時間','車牌號碼','司機','執行狀態','操作'].map(x=>`<th scope="col">${x}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.date)}</td><td>${esc(r.tId)}</td><td>${esc(r.routeId)} · ${esc(r.routeName)}</td><td>${esc(dispatchDirectionLabel(r.tDirection))}</td><td>${esc(r.departureTime)}</td><td>${esc(r.bId)}</td><td>${esc(r.driver)}</td><td><span class="pill">${esc(r.status)}</span></td><td><button data-dispatch-edit="${dispatchRows.indexOf(r)}" ${dispatchWriting?'disabled':''}>編輯</button><button class="danger" data-dispatch-delete="${dispatchRows.indexOf(r)}" ${dispatchWriting?'disabled':''}>刪除</button></td></tr>`).join('')}</tbody></table>${rows.length?'':`<div class="empty">${dispatchRows.length?'沒有符合條件的派車安排。':dispatchDay?'指定日期沒有派車安排，可新增安排或查看全部日期。':'資料庫目前沒有派車安排。'}</div>`}`;
 el('dispatch-total').textContent=`${dispatchDay||'全部日期'}：顯示 ${rows.length} 筆 / 共 ${dispatchRows.length} 筆`;
}
async function loadDispatchOptions(){
 if(dispatchLoading||dispatchWriting)return;dispatchLoading=true;dispatchReady=false;dispatchLoaded=false;dispatchRows=[];dispatchError='';renderDispatches();
 try{
  const data=await dispatchRequest(dispatchOptionsUrl);
  if(!Array.isArray(data.routes)||!Array.isArray(data.trips)||!Array.isArray(data.buses)||!Array.isArray(data.statuses)||!data.statuses.every(s=>typeof s==='string')||typeof data.csrfToken!=='string')throw new Error('派車選單資料格式不正確。');
  dispatchRoutes=data.routes;dispatchTrips=data.trips;dispatchBuses=data.buses;dispatchStatuses=data.statuses;dispatchCsrf=data.csrfToken;dispatchReady=true;
  if(dispatchRoute&&!dispatchRoutes.some(r=>r.routeId===dispatchRoute))dispatchRoute='';
  el('dispatch-route').innerHTML='<option value="">所有路線</option>'+dispatchRoutes.map(r=>`<option value="${esc(r.routeId)}" ${dispatchRoute===r.routeId?'selected':''}>${esc(r.routeName)}</option>`).join('');
 }catch(error){dispatchError=error.message;}finally{dispatchLoading=false;renderDispatches();}
 if(dispatchReady)await loadDispatches();
}
async function loadDispatches(){
 if(dispatchLoading||dispatchWriting||!dispatchReady)return;dispatchLoading=true;dispatchLoaded=false;dispatchRows=[];dispatchError='';renderDispatches();
 const params=new URLSearchParams();if(dispatchDay)params.set('date',dispatchDay);
 try{
  const data=await dispatchRequest(`${dispatchApiUrl}?${params}`);
  if(!Array.isArray(data.dispatches)||!data.dispatches.every(r=>['date','tId','routeId','routeName','tDirection','departureTime','bId','driver','status'].every(k=>typeof r[k]==='string'))||typeof data.csrfToken!=='string')throw new Error('派車資料格式不正確，請確認 API 欄位。');
  dispatchRows=data.dispatches;dispatchCsrf=data.csrfToken;dispatchLoaded=true;
 }catch(error){dispatchError=error.message;}finally{dispatchLoading=false;renderDispatches();}
}
function openDispatchEditor(index=null){
 if(!dispatchReady||!dispatchLoaded||dispatchLoading||dispatchWriting)return;
 const row=index===null?null:dispatchRows[index];if(index!==null&&!row)return;dispatchEditing=row?{tId:row.tId,date:row.date}:null;
 el('form-title').textContent=row?'編輯派車安排':'新增派車安排';el('error').textContent='';
 const trip=row?dispatchTrips.find(t=>t.tId===row.tId):null;
 el('fields').innerHTML=`${row?`<label>預定班次<input value="${esc(trip?dispatchTripLabel(trip):row.tId)}" readonly class="member-readonly"><input type="hidden" name="tId" value="${esc(row.tId)}"></label>`:`
 <label>篩選班次路線<select id="dispatch-form-route"><option value="">所有路線</option>${dispatchRoutes.map(r=>`<option value="${esc(r.routeId)}" ${dispatchRoute===r.routeId?'selected':''}>${esc(r.routeName)}</option>`).join('')}</select></label>
 <label>篩選班次方向<select id="dispatch-form-direction"><option value="">所有方向</option>${['去程','回程'].map(d=>`<option value="${d}" ${dispatchDirection===d?'selected':''}>${dispatchDirectionLabel(d)}</option>`).join('')}</select></label>
 <label>預定班次<select name="tId" id="dispatch-form-trip" required></select></label>`}
 <label>執行日期<input type="date" name="date" value="${esc(row?.date||dispatchDay)}" required ${row?'readonly class="member-readonly"':''}></label>
 <label>車輛<select name="bId" required><option value="">請選擇車輛</option>${dispatchBuses.map(b=>`<option value="${esc(b.bId)}" ${row?.bId===b.bId?'selected':''}>${esc(b.bId)} · ${esc(b.busType)}</option>`).join('')}</select></label>
 <label>司機姓名<input name="driver" maxlength="100" value="${esc(row?.driver||'')}" required></label>
 <label>執行狀態<select name="status" required><option value="">請選擇狀態</option>${dispatchStatuses.map(s=>`<option value="${esc(s)}" ${row?.status===s?'selected':''}>${esc(s)}</option>`).join('')}</select></label>`;
 if(!row){
  const populate=()=>{
   const previous=el('dispatch-form-trip').value,route=el('dispatch-form-route').value,direction=el('dispatch-form-direction').value;
   const trips=dispatchTrips.filter(t=>(!route||t.routeId===route)&&(!direction||t.tDirection===direction));
   el('dispatch-form-trip').innerHTML='<option value="">'+(trips.length?'請選擇班次':'此條件沒有預定班次')+'</option>'+trips.map(t=>`<option value="${esc(t.tId)}" ${previous===t.tId?'selected':''}>${esc(dispatchTripLabel(t))}</option>`).join('');
  };
  el('dispatch-form-route').onchange=populate;el('dispatch-form-direction').onchange=populate;populate();
 }
 el('editor').showModal();
}
function setDispatchWriting(value){dispatchWriting=value;dispatchSubmit.disabled=value;el('cancel').disabled=value;renderDispatches();}
async function writeDispatch(method,data,key=null){
 if(dispatchWriting)return;setDispatchWriting(true);dispatchError='';el('error').textContent='';let updated=false;
 const url=key?`${dispatchApiUrl}/${encodeURIComponent(key.tId)}/${encodeURIComponent(key.date)}`:dispatchApiUrl;
 try{const result=await dispatchRequest(url,{method,...(data?{body:JSON.stringify(data)}:{})});updated=true;if(method!=='DELETE')el('editor').close();toast(result.message);}
 catch(error){if(method==='DELETE')dispatchError=error.message;else el('error').textContent=error.message;}
 finally{setDispatchWriting(false);}
 if(updated)await loadDispatches();
}
el('section-name').textContent='SCHEDULE / 班表調度';el('title').textContent='每日派車與司機安排';el('description').textContent='依執行日期指派班次、車輛與司機；日期留空時查看全部派車紀錄。';el('add').hidden=false;el('add').textContent='＋ 新增派車';dispatchSubmit.textContent='儲存至資料庫';
el('content').innerHTML=`<div class="panel"><div class="toolbar"><input id="dispatch-search" type="search" placeholder="搜尋班次、路線、車牌或司機…" aria-label="搜尋派車" disabled><label>執行日期<input id="dispatch-day" type="date"></label><button class="btn" type="button" id="dispatch-all">全部日期</button><select id="dispatch-route" aria-label="篩選路線" disabled><option value="">所有路線</option></select><select id="dispatch-direction" aria-label="篩選方向" disabled><option value="">所有方向</option><option value="去程">去程</option><option value="回程">返程</option></select><button id="dispatch-reload" class="btn" type="button">重新載入</button></div><p class="count" id="dispatch-status" role="status" aria-live="polite"></p><p class="count">目前僅列已建立的派車安排；尚未進行司機或車輛的時間重疊檢查。</p><div id="dispatch-table" class="table-wrap"></div><div class="foot"><span id="dispatch-total"></span><span>PostgreSQL 每日派車紀錄</span></div></div>`;
el('dispatch-search').oninput=e=>{dispatchQuery=e.target.value.trim();renderDispatches();};el('dispatch-route').onchange=e=>{dispatchRoute=e.target.value;renderDispatches();};el('dispatch-direction').onchange=e=>{dispatchDirection=e.target.value;renderDispatches();};
el('dispatch-day').onchange=async e=>{dispatchDay=e.target.value;await loadDispatches();};el('dispatch-all').onclick=async()=>{dispatchDay='';el('dispatch-day').value='';await loadDispatches();};el('dispatch-reload').onclick=loadDispatchOptions;
el('add').onclick=()=>openDispatchEditor();el('cancel').onclick=()=>{if(!dispatchWriting)el('editor').close();};el('editor').addEventListener('cancel',e=>{if(dispatchWriting)e.preventDefault();});
el('dispatch-table').onclick=async e=>{
 const b=e.target.closest('button');if(!b||b.disabled||dispatchLoading||dispatchWriting)return;
 if(b.hasAttribute('data-dispatch-edit')){openDispatchEditor(Number(b.dataset.dispatchEdit));return;}
 if(b.hasAttribute('data-dispatch-delete')){const row=dispatchRows[Number(b.dataset.dispatchDelete)];if(row&&confirm(`確定刪除 ${row.date} 的班次 ${row.tId} 派車安排？若有位置紀錄，資料庫會禁止刪除。`))await writeDispatch('DELETE',null,row);}
};
el('form').onsubmit=async e=>{
 e.preventDefault();if(dispatchWriting)return;const f=new FormData(e.target),data=Object.fromEntries(['tId','date','bId','driver','status'].map(k=>[k,String(f.get(k)||'').trim()]));
 if(!dispatchTrips.some(t=>t.tId===data.tId)||!data.date||!dispatchBuses.some(b=>b.bId===data.bId)||!data.driver||[...data.driver].length>100||!dispatchStatuses.includes(data.status)){el('error').textContent='請選擇有效班次、日期、車輛與狀態，並填寫司機姓名。';return;}
 await writeDispatch(dispatchEditing?'PATCH':'POST',data,dispatchEditing);
};
loadDispatchOptions();
