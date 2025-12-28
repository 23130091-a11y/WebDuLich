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

function displayQuickSuggestions(results, query) {
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
            const regex = new RegExp(`(${query})`, 'gi');
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
                    <span class="badge bg-success">${item.score} điểm</span>
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

// ===== KHỞI TẠO KHI TRANG LOAD =====
document.addEventListener('DOMContentLoaded', () => {
    // checkAuthStatus();
    loadSearchHistory();
    setupEmailSuggestions();
});
