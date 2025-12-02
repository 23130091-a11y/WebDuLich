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
