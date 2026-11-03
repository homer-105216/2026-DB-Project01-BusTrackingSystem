/**
 * 高雄市公車追蹤系統 (Kaohsiung BusTrackingSystem)
 * 前端介面互動邏輯、輸入驗證與自訂收藏功能
 */

let redirectTimer = null;
let countdownInterval = null;

// ==========================================
// 1. 收藏點擊與未登入提示跳轉邏輯 (規格核心需求)
// ==========================================

/**
 * 彈出「請先登入帳號」提示框，並在倒數後跳轉至登入頁面
 * @param {string} desc - 提示文字
 * @param {string} nextUrl - 登入後要回傳的目的地網址
 */
function requireLoginPrompt(desc = '收藏公車路線與站點為會員專屬功能，請先登入帳號後再進行操作！', nextUrl = null) {
    const targetUrl = nextUrl || window.location.href;
    const loginUrl = `${window.LOGIN_URL || '/login'}?next=${encodeURIComponent(targetUrl)}`;

    const descEl = document.getElementById('loginModalDesc');
    const redirectBtn = document.getElementById('loginModalRedirectBtn');
    const timerEl = document.getElementById('countdownTimer');

    if (descEl) descEl.innerText = desc;
    if (redirectBtn) redirectBtn.href = loginUrl;

    const modalEl = document.getElementById('loginPromptModal');
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();

        // 倒數 3 秒後自動跳轉至登入頁
        let secondsLeft = 3;
        if (timerEl) timerEl.innerText = secondsLeft;

        cancelAutoRedirect();

        countdownInterval = setInterval(() => {
            secondsLeft -= 1;
            if (timerEl) timerEl.innerText = secondsLeft;
            if (secondsLeft <= 0) {
                clearInterval(countdownInterval);
                window.location.href = loginUrl;
            }
        }, 1000);
    } else {
        alert('請先登入帳號！');
        window.location.href = loginUrl;
    }
}

/**
 * 取消自動跳轉計時
 */
function cancelAutoRedirect() {
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
}

/**
 * 收藏/取消收藏處理 (路線或站點)
 * 若未登入，強制彈出提示框並導向登入頁
 * @param {string} type - 'route' 或 'station'
 * @param {string} id - routeId 或 stationId
 * @param {HTMLElement} btn - 按鈕元素
 */
async function toggleFavorite(type, id, btn) {
    // 檢查全域登入狀態 (後端 session 或 前端展示標記)
    const isLoggedIn = (typeof window.IS_LOGGED_IN !== 'undefined') ? window.IS_LOGGED_IN : false;

    if (!isLoggedIn) {
        requireLoginPrompt('收藏公車路線與站點為會員專屬功能，請先登入帳號！', window.location.href);
        return;
    }

    // 若已登入，執行前端收藏切換與 Toast 提示
    const isCurrentlyFav = btn.classList.contains('active');
    const newStatus = !isCurrentlyFav;

    if (newStatus) {
        btn.classList.add('active');
        const icon = btn.querySelector('i');
        const label = btn.querySelector('.fav-label');
        if (icon) {
            icon.classList.remove('bi-star');
            icon.classList.add('bi-star-fill', 'text-warning');
        }
        if (label) label.innerText = '已收藏路線';
        showToast(type === 'route' ? '已成功收藏該高雄公車路線！' : '已成功收藏該公車站牌！');
    } else {
        btn.classList.remove('active');
        const icon = btn.querySelector('i');
        const label = btn.querySelector('.fav-label');
        if (icon) {
            icon.classList.remove('bi-star-fill', 'text-warning');
            icon.classList.add('bi-star');
        }
        if (label) label.innerText = '收藏路線';
        showToast(type === 'route' ? '已取消收藏路線' : '已取消收藏站點');
    }

    // 嘗試通知後端 API (若後端尚未連接亦不會影響前端操作)
    try {
        await fetch(`/api/favorite/${type}/${id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (e) {
        // 純前端模式，忽略後端連線異常
    }
}

/**
 * 顯示全域 Toast 提示訊息
 */
function showToast(message, isError = false) {
    const toastEl = document.getElementById('actionToast');
    const toastMsg = document.getElementById('actionToastMsg');
    if (toastEl && toastMsg) {
        toastMsg.innerHTML = isError
            ? `<i class="bi bi-exclamation-triangle-fill text-danger me-2"></i><span>${message}</span>`
            : `<i class="bi bi-check-circle-fill text-success me-2"></i><span>${message}</span>`;
        const toast = bootstrap.Toast.getOrCreateInstance(toastEl);
        toast.show();
    }
}


// ==========================================
// 2. 前端表單輸入驗證 (Input Validation)
// ==========================================
document.addEventListener('DOMContentLoaded', function () {
    initFormValidations();
});

function initFormValidations() {
    // 註冊表單驗證
    const regForm = document.getElementById('register-form');
    if (regForm) {
        regForm.addEventListener('submit', function (e) {
            let isValid = true;
            const username = document.getElementById('reg-username');
            const email = document.getElementById('reg-email');
            const password = document.getElementById('reg-password');
            const confirmPassword = document.getElementById('reg-confirm-password');

            // 1. 驗證使用者名稱 (3-20字元)
            if (!username.value.trim() || username.value.trim().length < 3 || username.value.trim().length > 20) {
                username.classList.add('is-invalid');
                isValid = false;
            } else {
                username.classList.remove('is-invalid');
                username.classList.add('is-valid');
            }

            // 2. 驗證 Email 格式
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email.value.trim())) {
                email.classList.add('is-invalid');
                isValid = false;
            } else {
                email.classList.remove('is-invalid');
                email.classList.add('is-valid');
            }

            // 3. 驗證密碼長度 (>= 6)
            if (!password.value || password.value.length < 6) {
                password.classList.add('is-invalid');
                isValid = false;
            } else {
                password.classList.remove('is-invalid');
                password.classList.add('is-valid');
            }

            // 4. 驗證兩次密碼是否一致
            if (!confirmPassword.value || confirmPassword.value !== password.value) {
                confirmPassword.classList.add('is-invalid');
                isValid = false;
            } else {
                confirmPassword.classList.remove('is-invalid');
                confirmPassword.classList.add('is-valid');
            }

            if (!isValid) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }

    // 登入表單驗證
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function (e) {
            let isValid = true;
            const idInput = document.getElementById('login-identifier');
            const pwdInput = document.getElementById('login-password');

            if (!idInput.value.trim()) {
                idInput.classList.add('is-invalid');
                isValid = false;
            } else {
                idInput.classList.remove('is-invalid');
            }

            if (!pwdInput.value || pwdInput.value.length < 6) {
                pwdInput.classList.add('is-invalid');
                isValid = false;
            } else {
                pwdInput.classList.remove('is-invalid');
            }

            if (!isValid) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }

    // 帳號設定資料維護表單驗證
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', function (e) {
            let isValid = true;
            const username = document.getElementById('profile-username');
            const email = document.getElementById('profile-email');
            const currentPwd = document.getElementById('profile-current-pwd');
            const newPwd = document.getElementById('profile-new-pwd');
            const confirmPwd = document.getElementById('profile-confirm-pwd');

            if (!username.value.trim() || username.value.trim().length < 3) {
                username.classList.add('is-invalid');
                isValid = false;
            } else {
                username.classList.remove('is-invalid');
            }

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email.value.trim())) {
                email.classList.add('is-invalid');
                isValid = false;
            } else {
                email.classList.remove('is-invalid');
            }

            // 若有填寫新密碼，則需驗證目前密碼與一致性
            if (newPwd.value) {
                if (!currentPwd.value) {
                    currentPwd.classList.add('is-invalid');
                    isValid = false;
                } else {
                    currentPwd.classList.remove('is-invalid');
                }

                if (newPwd.value.length < 6) {
                    newPwd.classList.add('is-invalid');
                    isValid = false;
                } else {
                    newPwd.classList.remove('is-invalid');
                }

                if (newPwd.value !== confirmPwd.value) {
                    confirmPwd.classList.add('is-invalid');
                    isValid = false;
                } else {
                    confirmPwd.classList.remove('is-invalid');
                }
            }

            if (!isValid) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }
}


// ==========================================
// 3. HTML5 瀏覽器定位高雄附近公車站點
// ==========================================
function useCurrentLocation() {
    const locBtn = document.getElementById('btn-get-location');
    const statusText = document.getElementById('location-status-text');

    if (!navigator.geolocation) {
        alert('您的瀏覽器不支援地理定位功能');
        return;
    }

    if (locBtn) locBtn.disabled = true;
    if (statusText) statusText.innerText = '正在獲取您的目前位置...';

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            if (statusText) statusText.innerText = `已定位！座標：${lat.toFixed(4)}, ${lng.toFixed(4)}`;

            try {
                const res = await fetch(`/api/nearby?lat=${lat}&lng=${lng}`);
                const data = await res.json();
                if (data.success && data.stations) {
                    renderNearbyStations(data.stations);
                }
            } catch (e) {
                // 若 API 尚未實作，保持高雄預設站點
            } finally {
                if (locBtn) locBtn.disabled = false;
            }
        },
        (error) => {
            console.warn('Geolocation error:', error);
            if (statusText) statusText.innerText = '定位授權失敗，顯示預設車站（高雄車站）附近路線';
            if (locBtn) locBtn.disabled = false;
        },
        { timeout: 7000 }
    );
}

/**
 * 動態渲染附近站點卡片
 */
function renderNearbyStations(stations) {
    const container = document.getElementById('nearby-stations-container');
    if (!container) return;

    if (stations.length === 0) {
        container.innerHTML = '<div class="col-12 text-center text-muted py-4">附近暫無公車站點</div>';
        return;
    }

    let html = '';
    stations.forEach(s => {
        let routesHtml = '';
        if (s.routes && s.routes.length > 0) {
            routesHtml = s.routes.map(r => `
                <a href="/route/${r.routeId}" class="badge bg-primary text-decoration-none px-2 py-1 me-1 mb-1">
                    ${r.routeName}
                </a>
            `).join('');
        } else {
            routesHtml = '<span class="text-muted small">暫無路線</span>';
        }

        html += `
            <div class="col-md-6 col-lg-3">
                <div class="nearby-station-card p-3 h-100 d-flex flex-column justify-content-between">
                    <div>
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="fw-bold mb-0 text-dark">
                                <i class="bi bi-geo-alt-fill text-danger me-1"></i>${s.sName}
                            </h6>
                            <span class="badge bg-light text-secondary border small">
                                約 ${s.distanceKm} km
                            </span>
                        </div>
                        <p class="text-secondary small mb-2 text-truncate" title="${s.address}">
                            ${s.address || '高雄市交通幹道'}
                        </p>
                        <div class="mb-3">
                            <div class="small fw-semibold text-muted mb-1">行經路線：</div>
                            <div class="d-flex flex-wrap">${routesHtml}</div>
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center pt-2 border-top">
                        <button class="btn btn-sm btn-outline-warning btn-fav" onclick="toggleFavorite('station', '${s.stationId}', this)" title="收藏站點">
                            <i class="bi bi-star"></i>
                        </button>
                        <span class="text-success small fw-semibold">
                            <i class="bi bi-clock me-1"></i>即時運行中
                        </span>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}
