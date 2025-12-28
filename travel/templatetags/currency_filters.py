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
