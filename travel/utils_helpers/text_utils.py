# Utility functions cho tìm kiếm và xử lý tiếng Việt

import unicodedata

def remove_accents(text):
    """
    Loại bỏ dấu tiếng Việt
    VD: "Hà Nội" -> "Ha Noi"
    """
    if not text:
        return ""
    
    # Normalize unicode
    nfd = unicodedata.normalize('NFD', text)
    # Loại bỏ các ký tự dấu
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    # Xử lý các ký tự đặc biệt tiếng Việt
    replacements = {
        'đ': 'd', 'Đ': 'D',
        'ð': 'd', 'Ð': 'D'
    }
    
    for old, new in replacements.items():
        without_accents = without_accents.replace(old, new)
    
    return without_accents


def normalize_search_text(text):
    """
    Chuẩn hóa text để tìm kiếm
    - Loại bỏ dấu
    - Chuyển thường
    - Loại bỏ khoảng trắng thừa
    """
    if not text:
        return ""
    
    text = remove_accents(text)
    text = text.lower().strip()
    text = ' '.join(text.split())  # Loại bỏ khoảng trắng thừa
    
    return text


def levenshtein_distance(s1, s2):
    """
    Tính khoảng cách Levenshtein giữa 2 chuỗi
    Dùng cho fuzzy search
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Thêm 1 nếu ký tự khác nhau
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def fuzzy_match(query, text, threshold=0.6):
    """
    Kiểm tra xem query có khớp mờ với text không
    
    Args:
        query: Từ khóa tìm kiếm
        text: Text cần so sánh
        threshold: Ngưỡng tương đồng (0-1), mặc định 0.6
    
    Returns:
        tuple: (is_match, similarity_score)
    """
    query_norm = normalize_search_text(query)
    text_norm = normalize_search_text(text)
    
    if not query_norm or not text_norm:
        return False, 0
    
    # Exact match hoặc contains
    if query_norm in text_norm:
        return True, 1.0
    
    # Kiểm tra từng từ trong text
    text_words = text_norm.split()
    query_words = query_norm.split()
    
    best_score = 0
    for q_word in query_words:
        for t_word in text_words:
            # Tính độ tương đồng
            max_len = max(len(q_word), len(t_word))
            if max_len == 0:
                continue
            distance = levenshtein_distance(q_word, t_word)
            similarity = 1 - (distance / max_len)
            best_score = max(best_score, similarity)
            
            # Kiểm tra prefix match (autofill)
            if t_word.startswith(q_word) or q_word.startswith(t_word):
                best_score = max(best_score, 0.9)
    
    return best_score >= threshold, best_score


def calculate_search_score(query, name, location=None, description=None):
    """
    Tính điểm tìm kiếm tổng hợp
    
    Returns:
        float: Điểm từ 0-1, cao hơn = khớp tốt hơn
    """
    query_norm = normalize_search_text(query)
    name_norm = normalize_search_text(name)
    
    score = 0
    
    # 1. Exact match tên (cao nhất)
    if query_norm == name_norm:
        return 1.0
    
    # 2. Tên bắt đầu bằng query (autofill)
    if name_norm.startswith(query_norm):
        score = max(score, 0.95)
    
    # 3. Query nằm trong tên
    elif query_norm in name_norm:
        score = max(score, 0.85)
    
    # 4. Fuzzy match tên
    else:
        is_match, fuzzy_score = fuzzy_match(query, name)
        if is_match:
            score = max(score, fuzzy_score * 0.7)
    
    # 5. Kiểm tra location
    if location:
        loc_norm = normalize_search_text(location)
        if query_norm in loc_norm:
            score = max(score, 0.6)
        elif loc_norm.startswith(query_norm):
            score = max(score, 0.65)
    
    # 6. Kiểm tra description (thấp nhất)
    if description:
        desc_norm = normalize_search_text(description)
        if query_norm in desc_norm:
            score = max(score, 0.4)
    
    return score


# Danh sách tỉnh thành Việt Nam
VIETNAM_PROVINCES = [
    'Hà Nội', 'TP Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ',
    'An Giang', 'Bà Rịa - Vũng Tàu', 'Bắc Giang', 'Bắc Kạn', 'Bạc Liêu',
    'Bắc Ninh', 'Bến Tre', 'Bình Định', 'Bình Dương', 'Bình Phước',
    'Bình Thuận', 'Cà Mau', 'Cao Bằng', 'Đắk Lắk', 'Đắk Nông',
    'Điện Biên', 'Đồng Nai', 'Đồng Tháp', 'Gia Lai', 'Hà Giang',
    'Hà Nam', 'Hà Tĩnh', 'Hải Dương', 'Hậu Giang', 'Hòa Bình',
    'Hưng Yên', 'Khánh Hòa', 'Kiên Giang', 'Kon Tum', 'Lai Châu',
    'Lâm Đồng', 'Lạng Sơn', 'Lào Cai', 'Long An', 'Nam Định',
    'Nghệ An', 'Ninh Bình', 'Ninh Thuận', 'Phú Thọ', 'Phú Yên',
    'Quảng Bình', 'Quảng Nam', 'Quảng Ngãi', 'Quảng Ninh', 'Quảng Trị',
    'Sóc Trăng', 'Sơn La', 'Tây Ninh', 'Thái Bình', 'Thái Nguyên',
    'Thanh Hóa', 'Thừa Thiên Huế', 'Tiền Giang', 'Trà Vinh', 'Tuyên Quang',
    'Vĩnh Long', 'Vĩnh Phúc', 'Yên Bái'
]


# Mapping các biến thể tên địa điểm
LOCATION_ALIASES = {
    # TP Hồ Chí Minh
    'tp hồ chí minh': ['hồ chí minh', 'hcm', 'tp. hcm', 'tp.hcm', 'sài gòn', 'saigon', 'thành phố hồ chí minh'],
    'hồ chí minh': ['tp hồ chí minh', 'hcm', 'tp. hcm', 'tp.hcm', 'sài gòn', 'saigon', 'thành phố hồ chí minh'],
    'hcm': ['tp hồ chí minh', 'hồ chí minh', 'tp. hcm', 'sài gòn', 'saigon', 'thành phố hồ chí minh'],
    'sài gòn': ['tp hồ chí minh', 'hồ chí minh', 'hcm', 'tp. hcm', 'saigon', 'thành phố hồ chí minh'],
    
    # Hà Nội
    'hà nội': ['ha noi', 'hanoi', 'thủ đô'],
    'ha noi': ['hà nội', 'hanoi', 'thủ đô'],
    
    # Đà Nẵng
    'đà nẵng': ['da nang', 'danang'],
    'da nang': ['đà nẵng', 'danang'],
    
    # Đà Lạt
    'đà lạt': ['da lat', 'dalat', 'tp. đà lạt', 'tp đà lạt'],
    'da lat': ['đà lạt', 'dalat', 'tp. đà lạt'],
    
    # Nha Trang
    'nha trang': ['tp. nha trang', 'tp nha trang', 'khánh hòa'],
    
    # Phú Quốc
    'phú quốc': ['phu quoc', 'đảo phú quốc', 'kiên giang'],
    
    # Huế
    'huế': ['hue', 'thừa thiên huế', 'cố đô huế'],
    'hue': ['huế', 'thừa thiên huế'],
    
    # Hội An
    'hội an': ['hoi an', 'phố cổ hội an', 'quảng nam'],
    
    # Hạ Long
    'hạ long': ['ha long', 'vịnh hạ long', 'quảng ninh'],
    'ha long': ['hạ long', 'vịnh hạ long', 'quảng ninh'],
    
    # Sa Pa
    'sa pa': ['sapa', 'lào cai'],
    'sapa': ['sa pa', 'lào cai'],
}


def get_search_variants(query):
    """
    Lấy tất cả các biến thể tìm kiếm cho một query.
    
    Args:
        query: Từ khóa tìm kiếm gốc
        
    Returns:
        list: Danh sách các biến thể bao gồm query gốc
    """
    if not query:
        return []
    
    query_lower = query.lower().strip()
    query_normalized = normalize_search_text(query)
    
    variants = [query]  # Bắt đầu với query gốc
    
    # Thêm các alias nếu có
    if query_lower in LOCATION_ALIASES:
        variants.extend(LOCATION_ALIASES[query_lower])
    
    # Thêm phiên bản không dấu
    if query_normalized != query_lower:
        variants.append(query_normalized)
    
    # Loại bỏ trùng lặp và giữ thứ tự
    seen = set()
    unique_variants = []
    for v in variants:
        v_lower = v.lower()
        if v_lower not in seen:
            seen.add(v_lower)
            unique_variants.append(v)
    
    return unique_variants

def search_provinces(query):
    """
    Tìm kiếm tỉnh thành theo query (hỗ trợ không dấu)
    Sắp xếp: tỉnh bắt đầu bằng query lên trước, sau đó đến tỉnh chứa query
    """
    if not query:
        return VIETNAM_PROVINCES  # Trả về tất cả tỉnh
    
    query_normalized = normalize_search_text(query)
    
    # Phân loại kết quả
    starts_with = []  # Tỉnh bắt đầu bằng query
    contains = []     # Tỉnh chứa query (nhưng không bắt đầu)
    
    for province in VIETNAM_PROVINCES:
        province_normalized = normalize_search_text(province)
        
        if province_normalized.startswith(query_normalized):
            # Tỉnh bắt đầu bằng query
            starts_with.append(province)
        elif query_normalized in province_normalized:
            # Tỉnh chứa query (nhưng không bắt đầu)
            contains.append(province)
    
    # Kết hợp: bắt đầu trước, chứa sau
    results = starts_with + contains
    
    return results  # Trả về tất cả kết quả
