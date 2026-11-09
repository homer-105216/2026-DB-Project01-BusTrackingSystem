// 共用選單、提示訊息與摘要繪製工具。
const el=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url=k=>k==='overview'?base:base+k;
el('nav').innerHTML=`<a class="${page==='overview'?'active':''}" href="${url('overview')}">◫ 營運總覽</a>`+['CMS / 資料管理','SCHEDULE / 班表調度'].map(g=>`<div class="group">${g}</div>`+Object.entries(configs).filter(([k,c])=>c.group===g&&k!=='stop-times').map(([k,c])=>`<a class="${page===k?'active':''}" href="${url(k)}">${c.title}</a>`).join('')).join('')+`<div class="group">ANALYSIS / 統計分析</div><a class="${page==='analysis'?'active':''}" href="${url('analysis')}">營運統計分析</a>`;
function toast(message){el('toast').textContent=message;el('toast').hidden=false;setTimeout(()=>el('toast').hidden=true,3000)}
function save(){try{localStorage.setItem('bus-backstage-demo-v1',JSON.stringify(db));return true}catch{toast('瀏覽器無法儲存資料，請確認儲存空間與權限。');return false}}
function cards(items){return '<div class="cards">'+items.map(([label,n,note])=>`<div class="card"><p>${label}</p><div class="number">${n}</div><small>${note}</small></div>`).join('')+'</div>'}
function bars(items){const max=Math.max(1,...items.map(x=>x[1]));return items.map(([name,n])=>`<div class="bar-row"><span>${esc(name)}</span><div class="bar-track"><div class="bar" style="width:${n/max*100}%"></div></div><strong>${n}</strong></div>`).join('')||'<div class="empty">尚無資料</div>'}
function summary(){return cards([['服務路線',db.routes.length,'已建立的路線'],['營運站點',db.stations.length,'可供路線設定使用'],['車隊規模',db.buses.length,`${db['bus-types'].length} 種車型`],['預定班次',db.trips.length,'固定發車班次']])}
