from datetime import date

from django import forms
from django.contrib.auth import get_user_model

from .models import AccountProfile, Booking  # Import model Profile

User = get_user_model()


# Form xử lý thông tin cơ bản (User)
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    # Khóa ô Username và Email không cho sửa (chỉ để xem)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['readonly'] = True
        self.fields['email'].widget.attrs['readonly'] = True


# Form xử lý thông tin mở rộng (Profile)
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = AccountProfile

        fields = ['phone', 'birthday', 'profession']

        # Định dạng lịch chọn ngày tháng
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['full_name', 'phone_number', 'email', 'departure_date', 'number_of_adults', 'number_of_children', 'special_requests']
        widgets = {
            'departure_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nguyễn Văn A'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0901234567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'number_of_adults': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'number_of_children': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': '3', 'placeholder': 'Ví dụ: Dị ứng hải sản, cần phòng tầng trệt...'}),
        }

    # Server-side validation — HTML min/placeholder trên widget chỉ là cosmetic,
    # client bypass được. Mọi rule thật phải nằm ở clean_*/clean().
    def clean_number_of_adults(self):
        adults = self.cleaned_data.get('number_of_adults')
        if adults is None or adults < 1:
            raise forms.ValidationError('Phải có ít nhất 1 người lớn.')
        return adults

    def clean_number_of_children(self):
        children = self.cleaned_data.get('number_of_children')
        if children is None or children < 0:
            raise forms.ValidationError('Số trẻ em không hợp lệ.')
        return children

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '')
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) < 9 or len(digits) > 15:
            raise forms.ValidationError('Số điện thoại không hợp lệ (9-15 chữ số).')
        return phone

    def clean_departure_date(self):
        departure_date = self.cleaned_data.get('departure_date')
        if departure_date and departure_date < date.today():
            raise forms.ValidationError('Ngày khởi hành không thể là ngày trong quá khứ.')
        return departure_date

    def clean(self):
        cleaned = super().clean()
        adults = cleaned.get('number_of_adults') or 0
        children = cleaned.get('number_of_children') or 0
        if adults + children < 1:
            raise forms.ValidationError('Đặt tour phải có ít nhất 1 hành khách.')
        return cleaned
