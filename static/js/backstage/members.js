// 會員管理介面。目前只操作示範會員，未與前台註冊／登入資料庫串接。
let memberQuery = '', memberRole = '', editingMemberId = null;
const isMemberAdmin = member => member.admin === true || member.admin === 'true';
const memberRoleName = member => isMemberAdmin(member) ? '管理者' : '一般會員';

function memberFavorites(memberId, kind) {
    const routes = kind === 'routes';
    const key = routes ? 'routeId' : 'stationId';
    const favorites = db[routes ? 'favoriteRoutes' : 'favoriteStations'];
    const ids = new Set(favorites.filter(f => String(f.mId) === String(memberId)).map(f => String(f[key])));
    return db[routes ? 'routes' : 'stations'].filter(item => ids.has(String(item[key])));
}

function renderMembers() {
    el('member-summary').innerHTML = cards([
        ['註冊會員', db.members.length, '目前示範會員總數'],
        ['一般會員', db.members.filter(m => !isMemberAdmin(m)).length, '一般乘客帳號'],
        ['管理者', db.members.filter(isMemberAdmin).length, '管理者帳號'],
        ['有收藏的會員', db.members.filter(m => memberFavorites(m.mId, 'routes').length || memberFavorites(m.mId, 'stations').length).length, '至少收藏一條路線或一個站點']
    ]);
    const rows = db.members.filter(m =>
        (!memberQuery || [m.mId, m.userName, m.email].some(v => String(v ?? '').toLowerCase().includes(memberQuery.toLowerCase()))) &&
        (!memberRole || (memberRole === 'admin') === isMemberAdmin(m)));
    el('member-table').innerHTML = `<table><thead><tr>
        <th scope="col">會員編號</th><th scope="col">會員名稱</th><th scope="col">Email</th>
        <th scope="col">註冊時間</th><th scope="col">角色</th><th scope="col">操作</th>
        </tr></thead><tbody>${rows.map(m => `<tr>
        <td>${esc(m.mId)}</td><td>${esc(m.userName)}</td><td>${esc(m.email)}</td>
        <td>${esc(m.registerDatetime)}</td><td><span class="pill">${memberRoleName(m)}</span></td>
        <td><button data-member-view="${esc(m.mId)}">查看</button>
            <button data-member-edit="${esc(m.mId)}">編輯</button>
            <button class="danger" data-member-delete="${esc(m.mId)}">刪除</button></td></tr>`).join('')}
        </tbody></table>${rows.length ? '' : '<div class="empty">沒有符合條件的會員。</div>'}`;
    el('member-total').textContent = `顯示 ${rows.length} 筆 / 共 ${db.members.length} 筆`;
}

function showMember(member) {
    el('member-detail-title').textContent = `${member.userName} · 會員資料`;
    const routes = memberFavorites(member.mId, 'routes'), stations = memberFavorites(member.mId, 'stations');
    el('member-detail-body').innerHTML = `<dl class="member-details-list">
        <dt>會員編號</dt><dd>${esc(member.mId)}</dd><dt>會員名稱</dt><dd>${esc(member.userName)}</dd>
        <dt>Email</dt><dd>${esc(member.email)}</dd><dt>註冊時間</dt><dd>${esc(member.registerDatetime)}</dd>
        <dt>角色</dt><dd>${memberRoleName(member)}</dd></dl>
        <h2 class="member-subtitle">收藏路線（${routes.length}）</h2>
        ${routes.length ? '<ul class="member-favorites">' + routes.map(r => `<li>${esc(r.routeId)} · ${esc(r.routeName)}</li>`).join('') + '</ul>' : '<p>尚無收藏路線。</p>'}
        <h2 class="member-subtitle">收藏站點（${stations.length}）</h2>
        ${stations.length ? '<ul class="member-favorites">' + stations.map(s => `<li>${esc(s.stationId)} · ${esc(s.sName)}</li>`).join('') + '</ul>' : '<p>尚無收藏站點。</p>'}`;
    el('member-details').showModal();
}

function editMember(member) {
    editingMemberId = member.mId;
    el('form-title').textContent = '編輯會員資料';
    el('error').textContent = '';
    el('fields').innerHTML = `
        <label>會員編號<input class="member-readonly" value="${esc(member.mId)}" readonly></label>
        <label>會員名稱<input name="userName" value="${esc(member.userName)}" maxlength="80" required></label>
        <label>Email<input type="email" name="email" value="${esc(member.email)}" maxlength="254" required></label>
        <label>註冊時間<input class="member-readonly" value="${esc(member.registerDatetime)}" readonly></label>
        <label>角色<input class="member-readonly" value="${memberRoleName(member)}" readonly></label>`;
    el('editor').showModal();
}

el('section-name').textContent = 'CMS / 資料管理';
el('title').textContent = '會員管理';
el('description').textContent = configs.members.desc;
el('add').hidden = true;
el('content').innerHTML = `<p class="member-note">此頁目前為示範會員資料，尚未連接前台註冊帳號。正式串接後會讀取 Member 資料表。</p>
    <div id="member-summary"></div><div class="panel"><div class="toolbar">
        <input id="member-search" type="search" aria-label="搜尋會員" placeholder="搜尋會員編號、名稱或 Email…">
        <select id="member-role" aria-label="篩選會員角色"><option value="">所有角色</option><option value="member">一般會員</option><option value="admin">管理者</option></select>
    </div><div class="table-wrap" id="member-table"></div><div class="foot"><span id="member-total"></span><span>示範資料 · 本機儲存</span></div></div>`;
el('member-search').oninput = e => { memberQuery = e.target.value.trim(); renderMembers(); };
el('member-role').onchange = e => { memberRole = e.target.value; renderMembers(); };
el('close-member-details').onclick = () => el('member-details').close();
el('cancel').onclick = () => el('editor').close();

el('member-table').onclick = e => {
    const button = e.target.closest('button'); if (!button) return;
    const id = button.dataset.memberView ?? button.dataset.memberEdit ?? button.dataset.memberDelete;
    const member = db.members.find(m => String(m.mId) === id); if (!member) return;
    if (button.hasAttribute('data-member-view')) { showMember(member); return; }
    if (button.hasAttribute('data-member-edit')) { editMember(member); return; }
    if (!confirm(`確定刪除示範會員「${member.userName}」及其收藏？此操作不影響前台真實帳號。`)) return;
    const previous = { members: db.members, favoriteRoutes: db.favoriteRoutes, favoriteStations: db.favoriteStations };
    db.members = db.members.filter(m => String(m.mId) !== id);
    db.favoriteRoutes = db.favoriteRoutes.filter(f => String(f.mId) !== id);
    db.favoriteStations = db.favoriteStations.filter(f => String(f.mId) !== id);
    if (!save()) { Object.assign(db, previous); return; }
    renderMembers(); toast('已刪除示範會員及其收藏');
};

el('form').onsubmit = e => {
    e.preventDefault();
    const fields = new FormData(e.target);
    const userName = String(fields.get('userName') ?? '').trim();
    const email = String(fields.get('email') ?? '').trim();
    if (!userName || !email) { el('error').textContent = '請填寫會員名稱及 Email。'; return; }
    if (db.members.some(m => m.mId !== editingMemberId && (m.userName === userName || m.email.toLowerCase() === email.toLowerCase()))) {
        el('error').textContent = '會員名稱或 Email 已被其他帳號使用。'; return;
    }
    const index = db.members.findIndex(m => m.mId === editingMemberId);
    if (index < 0) { el('error').textContent = '找不到會員，請關閉後重新選擇。'; return; }
    const previous = db.members[index];
    db.members[index] = { ...previous, userName, email };
    if (!save()) { db.members[index] = previous; return; }
    el('editor').close(); renderMembers(); toast('已更新示範會員資料');
};
renderMembers();
