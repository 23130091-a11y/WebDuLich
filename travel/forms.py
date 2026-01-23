from django import forms
from django.contrib.auth.models import User
from .models import AccountProfile, Booking  # Import model Profile


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