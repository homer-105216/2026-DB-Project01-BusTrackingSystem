// 真實一般會員資料；詳細資料及收藏皆由 API 讀取，不使用 localStorage。
let realMembers = [], memberSummary = null, memberQuery = '', memberLoaded = false;
let memberLoading = false, memberWriting = false, memberError = '', memberCsrf = '', editingMemberId = null;
let memberDetailSequence = 0;
const memberSubmit = el('form').querySelector('button[type="submit"]');

function validPublicMember(member) {
    return member && Number.isInteger(member.mId) && member.admin === 'user' &&
        ['userName', 'email', 'registerDatetime'].every(key => typeof member[key] === 'string');
}

async function memberRequest(url, options = {}) {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal, cache: 'no-store',
            headers: { Accept: 'application/json', ...(options.headers || {}) } });
        const payload = await response.json();
        if (!response.ok || payload.status !== 'ok') throw new Error(payload.message || '會員資料操作失敗。');
        return payload;
    } catch (error) {
        if (error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError) {
            throw new Error(options.method ? '連線中斷，請重新載入確認資料是否已更新，再決定是否重試。' : '無法讀取會員資料，請確認 Flask 與資料庫連線後重試。');
        }
        throw error;
    } finally { clearTimeout(timer); }
}

function renderMembers() {
    el('member-reload').disabled = memberLoading || memberWriting;
    el('member-search').disabled = !memberLoaded || memberLoading;
    el('member-load-status').textContent = memberLoading ? '正在讀取資料庫會員…' : memberError;
    el('member-load-status').setAttribute('role', memberError ? 'alert' : 'status');
    if (!memberLoaded || memberLoading) {
        el('member-summary').innerHTML = ''; el('member-table').innerHTML = ''; el('member-total').textContent = ''; return;
    }
    el('member-summary').innerHTML = cards([
        ['註冊會員', memberSummary.userCount, '一般會員總數，不含管理者'],
        ['有收藏的會員', memberSummary.favoriteMemberCount, '至少收藏一條路線或一個站點，不含管理者']
    ]);
    const rows = realMembers.filter(member => [member.mId, member.userName, member.email].some(value =>
        String(value).toLowerCase().includes(memberQuery.toLowerCase())));
    el('member-table').innerHTML = `<table><thead><tr><th scope="col">會員編號</th><th scope="col">會員名稱</th><th scope="col">Email</th>
        <th scope="col">註冊時間</th><th scope="col">操作</th></tr></thead><tbody>
        ${rows.map(member => `<tr><td>${esc(member.mId)}</td><td>${esc(member.userName)}</td><td>${esc(member.email)}</td>
        <td>${esc(member.registerDatetime)}</td><td>
            <button data-member-view="${member.mId}" ${memberWriting ? 'disabled' : ''}>查看</button>
            <button data-member-edit="${member.mId}" ${memberWriting ? 'disabled' : ''}>編輯</button>
            <button class="danger" data-member-delete="${member.mId}" ${memberWriting ? 'disabled' : ''}>刪除</button></td></tr>`).join('')}
        </tbody></table>${rows.length ? '' : `<div class="empty">${realMembers.length ? '沒有符合條件的會員。' : '資料庫目前沒有一般會員。'}</div>`}`;
    el('member-total').textContent = `顯示 ${rows.length} 筆 / 共 ${realMembers.length} 筆`;
}

async function loadDatabaseMembers() {
    if (memberLoading || memberWriting) return;
    memberLoading = true; memberLoaded = false; memberError = ''; realMembers = []; memberSummary = null; renderMembers();
    try {
        const payload = await memberRequest(membersApiUrl);
        if (!Array.isArray(payload.members) || !payload.members.every(validPublicMember) || typeof payload.csrfToken !== 'string' ||
            !payload.summary || !Number.isInteger(payload.summary.userCount) || !Number.isInteger(payload.summary.favoriteMemberCount)) {
            throw new Error('會員資料格式不正確，請確認 API 欄位及角色設定。');
        }
        realMembers = payload.members; memberSummary = payload.summary; memberCsrf = payload.csrfToken; memberLoaded = true;
    } catch (error) { memberError = error.message; }
    finally { memberLoading = false; renderMembers(); }
}

async function showMember(member) {
    const sequence = ++memberDetailSequence;
    el('member-detail-title').textContent = '會員詳細資料';
    el('member-detail-body').innerHTML = '<p role="status">正在讀取會員資料與收藏…</p>';
    el('member-details').showModal();
    try {
        const payload = await memberRequest(`${membersApiUrl}/${member.mId}`);
        if (sequence !== memberDetailSequence) return;
        if (!validPublicMember(payload.member) || !Array.isArray(payload.favoriteRoutes) || !Array.isArray(payload.favoriteStations)) {
            throw new Error('會員詳細資料格式不正確。');
        }
        const m = payload.member, routes = payload.favoriteRoutes, stations = payload.favoriteStations;
        el('member-detail-title').textContent = `${m.userName} · 會員資料`;
        el('member-detail-body').innerHTML = `<dl class="member-details-list">
            <dt>會員編號</dt><dd>${esc(m.mId)}</dd><dt>會員名稱</dt><dd>${esc(m.userName)}</dd>
            <dt>Email</dt><dd>${esc(m.email)}</dd><dt>註冊時間</dt><dd>${esc(m.registerDatetime)}</dd>
            </dl>
            <h2 class="member-subtitle">收藏路線（${routes.length}）</h2>
            ${routes.length ? '<ul class="member-favorites">' + routes.map(r => `<li>${esc(r.routeId)} · ${esc(r.routeName)}</li>`).join('') + '</ul>' : '<p>尚無收藏路線。</p>'}
            <h2 class="member-subtitle">收藏站點（${stations.length}）</h2>
            ${stations.length ? '<ul class="member-favorites">' + stations.map(s => `<li>${esc(s.stationId)} · ${esc(s.sName)}</li>`).join('') + '</ul>' : '<p>尚無收藏站點。</p>'}`;
    } catch (error) {
        if (sequence === memberDetailSequence) el('member-detail-body').innerHTML = `<p class="feedback" role="alert">${esc(error.message)}</p>`;
    }
}

function editMember(member) {
    editingMemberId = member.mId; el('form-title').textContent = '編輯會員資料'; el('error').textContent = '';
    el('fields').innerHTML = `<label>會員編號<input class="member-readonly" value="${member.mId}" readonly></label>
        <label>會員名稱<input name="userName" value="${esc(member.userName)}" maxlength="50" required></label>
        <label>Email<input type="email" name="email" value="${esc(member.email)}" maxlength="100" required></label>
        <label>註冊時間<input class="member-readonly" value="${esc(member.registerDatetime)}" readonly></label>`;
    el('editor').showModal();
}

el('section-name').textContent = 'CMS / 資料管理'; el('title').textContent = '會員管理';
el('description').textContent = '管理資料庫中一般會員的基本資料與收藏；管理者帳號不列入。'; el('add').hidden = true;
memberSubmit.textContent = '儲存至資料庫';
el('content').innerHTML = `<div id="member-summary" class="user-stat-cards"></div><div class="panel"><div class="toolbar">
    <input id="member-search" type="search" aria-label="搜尋會員" placeholder="搜尋會員編號、名稱或 Email…" disabled>
    <button id="member-reload" class="btn" type="button">重新載入</button></div>
    <p id="member-load-status" class="count" role="status" aria-live="polite"></p><div class="table-wrap" id="member-table"></div>
    <div class="foot"><span id="member-total"></span><span>PostgreSQL 一般會員資料</span></div></div>`;
el('member-search').oninput = e => { memberQuery = e.target.value.trim(); renderMembers(); };
el('member-reload').onclick = loadDatabaseMembers;
el('close-member-details').onclick = () => el('member-details').close();
el('member-details').addEventListener('close', () => { memberDetailSequence++; });
el('cancel').onclick = () => { if (!memberWriting) el('editor').close(); };
el('editor').addEventListener('cancel', e => { if (memberWriting) e.preventDefault(); });

el('member-table').onclick = async e => {
    const button = e.target.closest('button'); if (!button || memberWriting || memberLoading) return;
    const id = Number(button.dataset.memberView ?? button.dataset.memberEdit ?? button.dataset.memberDelete);
    const member = realMembers.find(m => m.mId === id); if (!member) return;
    if (button.hasAttribute('data-member-view')) { await showMember(member); return; }
    if (button.hasAttribute('data-member-edit')) { editMember(member); return; }
    if (!button.hasAttribute('data-member-delete') || !confirm(`確定從資料庫刪除會員「${member.userName}」（編號 ${member.mId}）？此帳號及其路線、站點收藏將一併刪除。`)) return;
    memberWriting = true; memberError = ''; renderMembers(); let deleted = false;
    try {
        const payload = await memberRequest(`${membersApiUrl}/${member.mId}`, { method: 'DELETE', headers: { 'X-CSRF-Token': memberCsrf } });
        deleted = true; toast(payload.message);
    } catch (error) { memberError = error.message; }
    finally { memberWriting = false; renderMembers(); }
    if (deleted) await loadDatabaseMembers();
};

el('form').onsubmit = async e => {
    e.preventDefault(); if (memberWriting) return;
    const fields = new FormData(e.target), userName = String(fields.get('userName') || '').trim(), email = String(fields.get('email') || '').trim();
    if (!userName || !email) { el('error').textContent = '請填寫會員名稱及 Email。'; return; }
    memberWriting = true; memberSubmit.disabled = true; el('cancel').disabled = true; el('error').textContent = ''; renderMembers();
    let updated = false;
    try {
        const payload = await memberRequest(`${membersApiUrl}/${editingMemberId}`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': memberCsrf }, body: JSON.stringify({ userName, email })
        });
        updated = true; el('editor').close(); toast(payload.message);
    } catch (error) { el('error').textContent = error.message; }
    finally { memberWriting = false; memberSubmit.disabled = false; el('cancel').disabled = false; renderMembers(); }
    if (updated) await loadDatabaseMembers();
};
loadDatabaseMembers();
