from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'autocomplete': 'new-password', 'id': 'id_password1', 'class': 'form-control pw-with-toggle'})
        self.fields['password2'].widget.attrs.update({'autocomplete': 'new-password', 'id': 'id_password2', 'class': 'form-control pw-with-toggle'})

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Mật khẩu xác nhận không khớp.')
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email


class LoginForm(forms.Form):
    username = forms.CharField(label='Tên đăng nhập')
    password = forms.CharField(label='Mật khẩu', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control pw-with-toggle', 'id': 'id_password'})


class OTPForm(forms.Form):
    otp = forms.CharField(
        label='Mã xác thực',
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control otp-input',
            'placeholder': '000000',
            'maxlength': '6',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
        })
    )
