from django import template

register = template.Library()


@register.filter
def vnd_format(value):
    """
    Format số tiền theo định dạng VND: 130.000.000 đ
    """
    if value is None:
        return "0 đ"
    try:
        # Chuyển về số nguyên
        number = int(float(value))
        # Format với dấu chấm phân cách hàng nghìn
        formatted = "{:,.0f}".format(number).replace(",", ".")
        return f"{formatted} đ"
    except (ValueError, TypeError):
        return "0 đ"


@register.filter
def get_item(dictionary, key):
    """
    Truy cập dictionary với key động trong template.
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(str(key))


@register.filter
def get_dest_distance(distance_info, dest_id):
    """
    Lấy thông tin khoảng cách cho destination.
    Usage: {{ distance_info|get_dest_distance:dest.id }}
    """
    if distance_info is None:
        return None
    key = f'dest_{dest_id}'
    return distance_info.get(key)


@register.filter
def get_tour_distance(distance_info, tour_id):
    """
    Lấy thông tin khoảng cách cho tour.
    Usage: {{ distance_info|get_tour_distance:tour.id }}
    """
    if distance_info is None:
        return None
    key = f'tour_{tour_id}'
    return distance_info.get(key)
