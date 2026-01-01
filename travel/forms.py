from django import forms
from django.contrib.auth.models import User
from .models import AccountProfile  # Import model Profile


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