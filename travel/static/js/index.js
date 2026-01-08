/**
 * index.js - JavaScript cho trang chủ
 * Bao gồm: Lịch sử tìm kiếm, Autocomplete, Slideshow, Auth Modal
 */

// ===== LỊCH SỬ TÌM KIẾM =====
const searchHistorySection = document.getElementById('searchHistorySection');
const searchHistoryList = document.getElementById('searchHistoryList');
const clearAllHistoryBtn = document.getElementById('clearAllHistory');


// Load lịch sử tìm kiếm khi trang load (theo IP, không cần đăng nhập)
function loadSearchHistory() {
    if (!searchHistorySection) return;
    
    fetch('/api/search-history/?limit=8')
        .then(res => res.json())
        .then(data => {
            // Hiển thị nếu có lịch sử
            if (data.history && data.history.length > 0) {
                displaySearchHistory(data.history);
                searchHistorySection.classList.remove('d-none');
            } else {
                searchHistorySection.classList.add('d-none');
            }
        })
        .catch(err => {
            console.error('Error loading search history:', err);
            searchHistorySection.classList.add('d-none');
        });
}

// Hiển thị lịch sử tìm kiếm
function displaySearchHistory(history) {
    if (!searchHistoryList) return;
    searchHistoryList.innerHTML = '';
    
    history.forEach(item => {
        const historyItem = document.createElement('a');
        historyItem.href = `/search/?q=${encodeURIComponent(item.query)}`;
        historyItem.className = 'history-item';
        
        // Hiển thị số lần tìm kiếm nếu > 1
        const countBadge = item.search_count > 1 
            ? `<span class="search-count">${item.search_count} lần</span>` 
            : '';
        
        historyItem.innerHTML = `
            <i class="fa-solid fa-search text-muted"></i>
            <span>${item.query}</span>
            ${countBadge}
            <button type="button" class="btn-close delete-history" 
                    data-query="${item.query}" title="Xóa"></button>
        `;
        
        // Ngăn click vào nút xóa không chuyển trang
        historyItem.querySelector('.delete-history').addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            deleteSearchHistory(item.query);
        });
        
        searchHistoryList.appendChild(historyItem);
    });
}

// Xóa một lịch sử tìm kiếm
function deleteSearchHistory(query) {
    fetch('/api/search-history/delete/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ query: query })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            loadSearchHistory();
        } else if (data.error) {
            console.error('Error:', data.error);
        }
    })
    .catch(err => console.error('Error deleting history:', err));
}

// Xóa tất cả lịch sử
if (clearAllHistoryBtn) {
    clearAllHistoryBtn.addEventListener('click', () => {
        if (confirm('Bạn có chắc muốn xóa tất cả lịch sử tìm kiếm?')) {
            fetch('/api/search-history/delete/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ delete_all: true })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    searchHistorySection.classList.add('d-none');
                } else if (data.error) {
                    alert(data.error);
                }
            })
            .catch(err => console.error('Error clearing history:', err));
        }
    });
}

// Lấy CSRF token
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ===== LƯU VÀ GỢI Ý EMAIL =====
function saveRecentEmail(email) {
    let emails = JSON.parse(localStorage.getItem('recentEmails') || '[]');
    // Xóa email cũ nếu đã tồn tại
    emails = emails.filter(e => e !== email);
    // Thêm vào đầu
    emails.unshift(email);
    // Giữ tối đa 5 email
    emails = emails.slice(0, 5);
    localStorage.setItem('recentEmails', JSON.stringify(emails));
}

function getRecentEmails() {
    return JSON.parse(localStorage.getItem('recentEmails') || '[]');
}

// Hiển thị gợi ý email khi focus vào input email
function setupEmailSuggestions() {
    const loginEmail = document.getElementById('loginEmail');
    const registerEmail = document.getElementById('registerEmail');
    
    [loginEmail, registerEmail].forEach(input => {
        if (!input) return;
        
        // Tạo dropdown gợi ý
        const suggestionDiv = document.createElement('div');
        suggestionDiv.className = 'email-suggestions';
        suggestionDiv.style.cssText = 'position:absolute;top:100%;left:0;right:0;background:white;border:1px solid #ddd;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:1060;display:none;max-height:200px;overflow-y:auto;';
        input.parentElement.style.position = 'relative';
        input.parentElement.appendChild(suggestionDiv);
        
        input.addEventListener('focus', () => {
            const emails = getRecentEmails();
            if (emails.length > 0) {
                suggestionDiv.innerHTML = emails.map(email => `
                    <div class="email-suggestion-item" style="padding:10px 15px;cursor:pointer;border-bottom:1px solid #f0f0f0;">
                        <i class="fa-solid fa-clock-rotate-left text-muted me-2"></i>${email}
                    </div>
                `).join('');
                suggestionDiv.style.display = 'block';
                
                // Click vào gợi ý
                suggestionDiv.querySelectorAll('.email-suggestion-item').forEach(item => {
                    item.addEventListener('click', () => {
                        input.value = item.textContent.trim();
                        suggestionDiv.style.display = 'none';
                    });
                    item.addEventListener('mouseenter', () => {
                        item.style.backgroundColor = '#f8f9fa';
                    });
                    item.addEventListener('mouseleave', () => {
                        item.style.backgroundColor = 'white';
                    });
                });
            }
        });
        
        input.addEventListener('blur', () => {
            setTimeout(() => suggestionDiv.style.display = 'none', 200);
        });
        
        input.addEventListener('input', () => {
            suggestionDiv.style.display = 'none';
        });
    });
}

// ===== AUTOCOMPLETE THÔNG MINH =====

// Hàm loại bỏ dấu tiếng Việt
function removeAccents(str) {
    return str.normalize('NFD')
              .replace(/[\u0300-\u036f]/g, '')
              .replace(/đ/g, 'd')
              .replace(/Đ/g, 'D');
}

// Autocomplete cho tìm kiếm nhanh
const quickSearchInput = document.getElementById('quickSearchInput');
const quickSuggestions = document.getElementById('quickSuggestions');
let quickSearchTimeout;

if (quickSearchInput) {
    quickSearchInput.addEventListener('input', function() {
        clearTimeout(quickSearchTimeout);
        const query = this.value.trim();
        
        if (query.length < 1) {
            quickSuggestions.style.display = 'none';
            return;
        }
        
        quickSearchTimeout = setTimeout(() => {
            fetch(`/api/search/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    displayQuickSuggestions(data.results, query);
                })
                .catch(err => console.error('Error:', err));
        }, 300);
    });
}

function displayQuickSuggestions(results = [], query) {
    if (!quickSuggestions) return;
    quickSuggestions.innerHTML = '';
    
    if (results.length === 0) {
        quickSuggestions.style.display = 'none';
        return;
    }
    
    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'autocomplete-item';
        
        const queryNormalized = removeAccents(query.toLowerCase());
        const nameNormalized = removeAccents(item.name.toLowerCase());
        
        let displayName = item.name;
        if (nameNormalized.includes(queryNormalized)) {
            const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escapedQuery})`, 'gi');
            displayName = item.name.replace(regex, '<strong class="text-primary">$1</strong>');
        }
        
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <div>${displayName}</div>
                    <small class="text-muted">
                        <i class="fa-solid fa-location-dot"></i> ${item.location} 
                        <span class="ms-2"><i class="fa-solid fa-tag"></i> ${item.travel_type}</span>
                    </small>
                </div>
                <div class="text-end">
                    <span class="badge bg-success">${item.score ?? 0} điểm</span>
                    <div class="text-warning small">
                        ${'★'.repeat(Math.round(item.avg_rating))}${'☆'.repeat(5 - Math.round(item.avg_rating))}
                    </div>
                </div>
            </div>
        `;
        
        div.addEventListener('click', () => {
            quickSearchInput.value = item.name;
            quickSuggestions.style.display = 'none';
            document.getElementById('quickSearchForm').submit();
        });
        
        quickSuggestions.appendChild(div);
    });
    
    quickSuggestions.style.display = 'block';
}


// Autocomplete cho vị trí xuất phát
const fromLocationInput = document.getElementById('fromLocationInput');
const fromLocationSuggestions = document.getElementById('fromLocationSuggestions');
let fromLocationTimeout;

if (fromLocationInput) {
    fromLocationInput.addEventListener('input', function() {
        clearTimeout(fromLocationTimeout);
        const query = this.value.trim();
        
        if (query.length < 1) {
            fromLocationSuggestions.style.display = 'none';
            return;
        }
        
        fromLocationTimeout = setTimeout(() => {
            fetch(`/api/provinces/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    displayProvinceSuggestions(data.provinces, query, fromLocationInput, fromLocationSuggestions);
                })
                .catch(err => console.error('Error:', err));
        }, 200);
    });
}

// Autocomplete cho nơi muốn đến
const toLocationInput = document.getElementById('toLocationInput');
const toLocationSuggestions = document.getElementById('toLocationSuggestions');
let toLocationTimeout;

if (toLocationInput) {
    toLocationInput.addEventListener('input', function() {
        clearTimeout(toLocationTimeout);
        const query = this.value.trim();
        
        if (query.length < 1) {
            toLocationSuggestions.style.display = 'none';
            return;
        }
        
        toLocationTimeout = setTimeout(() => {
            fetch(`/api/provinces/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    displayProvinceSuggestions(data.provinces, query, toLocationInput, toLocationSuggestions);
                })
                .catch(err => console.error('Error:', err));
        }, 200);
    });
}

function displayProvinceSuggestions(provinces, query, inputElement, suggestionsElement) {
    suggestionsElement.innerHTML = '';
    
    if (provinces.length === 0) {
        suggestionsElement.style.display = 'none';
        return;
    }
    
    provinces.forEach(province => {
        const div = document.createElement('div');
        div.className = 'autocomplete-item';
        
        const icon = document.createElement('i');
        icon.className = 'fa-solid fa-map-marker-alt text-primary me-2';
        
        const textSpan = document.createElement('span');
        textSpan.textContent = province;
        textSpan.style.whiteSpace = 'nowrap';
        
        div.appendChild(icon);
        div.appendChild(textSpan);
        
        div.addEventListener('click', () => {
            inputElement.value = province;
            suggestionsElement.style.display = 'none';
        });
        
        suggestionsElement.appendChild(div);
    });
    
    suggestionsElement.style.display = 'block';
}

// Đóng suggestions khi click bên ngoài
document.addEventListener('click', (e) => {
    if (quickSearchInput && quickSuggestions && 
        !quickSearchInput.contains(e.target) && !quickSuggestions.contains(e.target)) {
        quickSuggestions.style.display = 'none';
    }
    if (fromLocationInput && fromLocationSuggestions &&
        !fromLocationInput.contains(e.target) && !fromLocationSuggestions.contains(e.target)) {
        fromLocationSuggestions.style.display = 'none';
    }
    if (toLocationInput && toLocationSuggestions &&
        !toLocationInput.contains(e.target) && !toLocationSuggestions.contains(e.target)) {
        toLocationSuggestions.style.display = 'none';
    }
});

// Không cho chọn ngày trong quá khứ
const travelDateInput = document.getElementById('travelDateInput');
if (travelDateInput) {
    const today = new Date().toISOString().split('T')[0];
    travelDateInput.setAttribute('min', today);
    
    const maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 7);
    travelDateInput.setAttribute('max', maxDate.toISOString().split('T')[0]);
}


// Thanh
// ===== ĐĂNG KÝ / ĐĂNG NHẬP =====
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const preferencesForm = document.getElementById('preferencesForm');
const modalTitle = document.getElementById('modalTitle');

const authAlert = document.getElementById('authAlert');

// Hàm hiển thị thông báo
function showAlert(message, type = 'danger') {
    if (!authAlert) return;
    authAlert.className = `alert alert-${type}`;
    authAlert.innerHTML = `<i class="fa-solid fa-${type === 'danger' ? 'exclamation-circle' : 'check-circle'} me-2"></i>${message}`;
    authAlert.classList.remove('d-none');
    setTimeout(() => authAlert.classList.add('d-none'), 5000);
}

function hideAllForms() {
    if (loginForm) loginForm.classList.add('d-none');
    if (registerForm) registerForm.classList.add('d-none');
    if (preferencesForm) preferencesForm.classList.add('d-none');
}

// Chuyển sang form đăng ký
const showRegisterLink = document.getElementById('showRegisterLink');
if (showRegisterLink) {
    showRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        hideAllForms();
        registerForm.classList.remove('d-none');
        modalTitle.textContent = 'Đăng ký tài khoản';
    });
}

// Chuyển sang form đăng nhập
const showLoginLink = document.getElementById('showLoginLink');
if (showLoginLink) {
    showLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        hideAllForms();
        loginForm.classList.remove('d-none');
        modalTitle.textContent = 'Đăng nhập';
    });
}

// Đăng nhập
const loginBtn = document.getElementById('loginBtn');
if (loginBtn) {
    loginBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        if (!email || !password) {
            showAlert('Vui lòng nhập đầy đủ email và mật khẩu');
            return;
        }

        const btn = e.currentTarget;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Đang đăng nhập...';

        try {
            // const response = await fetch('/auth/login', {

            const response = await fetch('/auth/login', {

                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({email, password})
            });
            const data = await response.json();

            if (response.ok) {
                // Lưu thông tin đăng nhập
                localStorage.setItem('access', data.tokens.access);
                localStorage.setItem('refresh', data.tokens.refresh);
                localStorage.setItem('user', JSON.stringify(data.user));

                // Lưu email để gợi ý lần sau
                saveRecentEmail(email);

                showAlert('Đăng nhập thành công!', 'success');

                const modal = bootstrap.Modal.getInstance(document.getElementById('authModal'));
                if (modal) modal.hide();

                checkAuthStatus();
                loadSearchHistory();
                window.location.reload();
            } else {
                showAlert(data.detail || 'Email hoặc mật khẩu không đúng');
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-right-to-bracket me-2"></i>Đăng nhập';
            }
        } catch (err) {
            showAlert('Lỗi kết nối server');
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-right-to-bracket me-2"></i>Đăng nhập';
        }
    });
}

// Đăng ký
const registerBtn = document.getElementById('registerBtn');
if (registerBtn) {
    registerBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('registerConfirmPassword').value;

        // Validation
        if (!username || !email || !password || !confirmPassword) {
            showAlert('Vui lòng nhập đầy đủ thông tin');
            return;
        }
        if (password !== confirmPassword) {
            showAlert('Mật khẩu xác nhận không khớp');
            return;
        }
        if (password.length < 6) {
            showAlert('Mật khẩu phải có ít nhất 6 ký tự');
            return;
        }

        const btn = e.currentTarget;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Đang đăng ký...';

        try {
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({username, email, password})
            });
            const data = await response.json();

            if (response.ok) {
                // Lưu thông tin đăng nhập
                localStorage.setItem('access', data.tokens.access);
                localStorage.setItem('refresh', data.tokens.refresh);
                localStorage.setItem('user', JSON.stringify(data.user));

                showAlert('Đăng ký thành công! Vui lòng chọn sở thích', 'success');

                // Lưu email để gợi ý lần sau
                saveRecentEmail(email);

                hideAllForms();
                if (preferencesForm) preferencesForm.classList.remove('d-none');
                if (modalTitle) modalTitle.textContent = 'Chọn sở thích';
            } else {
                showAlert(data.detail || data.email?.[0] || data.username?.[0] || 'Đăng ký thất bại');
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-user-plus me-2"></i>Đăng ký';
            }
        } catch (err) {
            showAlert('Lỗi kết nối server');
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-user-plus me-2"></i>Đăng ký';
        }
    });
}

// Lưu sở thích
const savePreferencesBtn = document.getElementById('savePreferencesBtn');
if (savePreferencesBtn) {
    savePreferencesBtn.addEventListener('click', async () => {
        const travelTypes = Array.from(document.querySelectorAll('input[name="travelType"]:checked')).map(el => el.value);
        const locations = Array.from(document.querySelectorAll('input[name="locations"]:checked')).map(el => el.value);

        if (travelTypes.length === 0 || locations.length === 0) {
            showAlert('Vui lòng chọn ít nhất 1 loại hình và 1 địa điểm');
            return;
        }

        const accessToken = localStorage.getItem('access');
        if (!accessToken) {
            showAlert('Vui lòng đăng nhập lại');
            return;
        }

        try {
            const response = await fetch('/auth/preferences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                },
                body: JSON.stringify({ travelTypes, locations })
            });

            if (response.status === 401) {
                showAlert('Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại');
                logout();
                return;
            }

            if (response.ok) {
                showAlert('Đã lưu sở thích!', 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('authModal'));
                if (modal) modal.hide();

                checkAuthStatus();
                loadSearchHistory();
            } else {
                showAlert('Không thể lưu sở thích');
            }
        } catch (err) {
            console.error('Error saving preferences:', err);
        }
    });
}

// ===== MỞ MODAL ĐĂNG NHẬP / ĐĂNG KÝ =====
const showLoginBtn = document.getElementById('showLoginBtn');
const showRegisterBtn = document.getElementById('showRegisterBtn');

// Mở modal với form đăng nhập
if (showLoginBtn) {
    showLoginBtn.addEventListener('click', () => {
        hideAllForms();
        if (loginForm) loginForm.classList.remove('d-none');
        if (modalTitle) modalTitle.textContent = 'Đăng nhập';
        const authModal = new bootstrap.Modal(document.getElementById('authModal'));
        authModal.show();
    });
}

// Mở modal với form đăng ký
if (showRegisterBtn) {
    showRegisterBtn.addEventListener('click', () => {
        hideAllForms();
        if (registerForm) registerForm.classList.remove('d-none');
        if (modalTitle) modalTitle.textContent = 'Đăng ký tài khoản';
        const authModal = new bootstrap.Modal(document.getElementById('authModal'));
        authModal.show();
    });
}

// ===== KIỂM TRA TRẠNG THÁI ĐĂNG NHẬP =====
function hasValidAuth() {
    return !!localStorage.getItem('access');
}

function checkAuthStatus() {
    const user = localStorage.getItem('user');
    const authButtons = document.getElementById('authButtons');
    const userInfo = document.getElementById('userInfo');
    const userDisplayName = document.getElementById('userDisplayName');
    const userEmail = document.getElementById('userEmail');

    if (user && hasValidAuth()) {
        try {
            const userData = JSON.parse(user);

            if (authButtons) authButtons.classList.add('d-none');
            if (userInfo) userInfo.classList.remove('d-none');

            if (userDisplayName) {
                userDisplayName.textContent =
                    userData.username ||
                    (userData.email ? userData.email.split('@')[0] : 'User');
            }

            if (userEmail) userEmail.textContent = userData.email || '';
        } catch (e) {
            console.error('Invalid user data:', e);
            localStorage.clear();
            if (authButtons) authButtons.classList.remove('d-none');
            if (userInfo) userInfo.classList.add('d-none');
        }
    } else {
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
        localStorage.removeItem('user');
        if (authButtons) authButtons.classList.remove('d-none');
        if (userInfo) userInfo.classList.add('d-none');
    }
}

// Đăng xuất
async function logout() {
    const refresh = localStorage.getItem('refresh');

    if (refresh) {
        await fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh })
        });
    }

    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    localStorage.removeItem('user_info'); 

    window.location.href = '/';

    // localStorage.clear();
    // window.location.reload();
}

const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        logout();
    });
}

// ===== KHỞI TẠO KHI TRANG LOAD =====
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    loadSearchHistory();
    setupEmailSuggestions();
});





