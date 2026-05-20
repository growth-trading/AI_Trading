from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

COUNTRY_CHOICES = [
    ('', '—'),
    ('Afghanistan', '🇦🇫 Afghanistan'), ('Albania', '🇦🇱 Albania'), ('Algeria', '🇩🇿 Algeria'),
    ('Argentina', '🇦🇷 Argentina'), ('Australia', '🇦🇺 Australia'), ('Austria', '🇦🇹 Austria'),
    ('Azerbaijan', '🇦🇿 Azerbaijan'), ('Bahrain', '🇧🇭 Bahrain'), ('Bangladesh', '🇧🇩 Bangladesh'),
    ('Belarus', '🇧🇾 Belarus'), ('Belgium', '🇧🇪 Belgium'), ('Bolivia', '🇧🇴 Bolivia'),
    ('Bosnia and Herzegovina', '🇧🇦 Bosnia and Herzegovina'), ('Brazil', '🇧🇷 Brazil'),
    ('Brunei', '🇧🇳 Brunei'), ('Bulgaria', '🇧🇬 Bulgaria'), ('Cambodia', '🇰🇭 Cambodia'),
    ('Canada', '🇨🇦 Canada'), ('Chile', '🇨🇱 Chile'), ('China', '🇨🇳 China'),
    ('Colombia', '🇨🇴 Colombia'), ('Croatia', '🇭🇷 Croatia'), ('Cuba', '🇨🇺 Cuba'),
    ('Cyprus', '🇨🇾 Cyprus'), ('Czech Republic', '🇨🇿 Czech Republic'), ('Denmark', '🇩🇰 Denmark'),
    ('Ecuador', '🇪🇨 Ecuador'), ('Egypt', '🇪🇬 Egypt'), ('Estonia', '🇪🇪 Estonia'),
    ('Ethiopia', '🇪🇹 Ethiopia'), ('Finland', '🇫🇮 Finland'), ('France', '🇫🇷 France'),
    ('Georgia', '🇬🇪 Georgia'), ('Germany', '🇩🇪 Germany'), ('Ghana', '🇬🇭 Ghana'),
    ('Greece', '🇬🇷 Greece'), ('Guatemala', '🇬🇹 Guatemala'), ('Hong Kong', '🇭🇰 Hong Kong'),
    ('Hungary', '🇭🇺 Hungary'), ('India', '🇮🇳 India'), ('Indonesia', '🇮🇩 Indonesia'),
    ('Iran', '🇮🇷 Iran'), ('Iraq', '🇮🇶 Iraq'), ('Ireland', '🇮🇪 Ireland'),
    ('Israel', '🇮🇱 Israel'), ('Italy', '🇮🇹 Italy'), ('Japan', '🇯🇵 Japan'),
    ('Jordan', '🇯🇴 Jordan'), ('Kazakhstan', '🇰🇿 Kazakhstan'), ('Kenya', '🇰🇪 Kenya'),
    ('Kuwait', '🇰🇼 Kuwait'), ('Kyrgyzstan', '🇰🇬 Kyrgyzstan'), ('Laos', '🇱🇦 Laos'),
    ('Latvia', '🇱🇻 Latvia'), ('Lebanon', '🇱🇧 Lebanon'), ('Libya', '🇱🇾 Libya'),
    ('Lithuania', '🇱🇹 Lithuania'), ('Luxembourg', '🇱🇺 Luxembourg'), ('Macau', '🇲🇴 Macau'),
    ('Malaysia', '🇲🇾 Malaysia'), ('Mexico', '🇲🇽 Mexico'), ('Moldova', '🇲🇩 Moldova'),
    ('Mongolia', '🇲🇳 Mongolia'), ('Morocco', '🇲🇦 Morocco'), ('Myanmar', '🇲🇲 Myanmar'),
    ('Nepal', '🇳🇵 Nepal'), ('Netherlands', '🇳🇱 Netherlands'), ('New Zealand', '🇳🇿 New Zealand'),
    ('Nigeria', '🇳🇬 Nigeria'), ('Norway', '🇳🇴 Norway'), ('Oman', '🇴🇲 Oman'),
    ('Pakistan', '🇵🇰 Pakistan'), ('Palestine', '🇵🇸 Palestine'), ('Panama', '🇵🇦 Panama'),
    ('Paraguay', '🇵🇾 Paraguay'), ('Peru', '🇵🇪 Peru'), ('Philippines', '🇵🇭 Philippines'),
    ('Poland', '🇵🇱 Poland'), ('Portugal', '🇵🇹 Portugal'), ('Qatar', '🇶🇦 Qatar'),
    ('Romania', '🇷🇴 Romania'), ('Russia', '🇷🇺 Russia'), ('Saudi Arabia', '🇸🇦 Saudi Arabia'),
    ('Serbia', '🇷🇸 Serbia'), ('Singapore', '🇸🇬 Singapore'), ('Slovakia', '🇸🇰 Slovakia'),
    ('Slovenia', '🇸🇮 Slovenia'), ('South Africa', '🇿🇦 South Africa'), ('South Korea', '🇰🇷 South Korea'),
    ('Spain', '🇪🇸 Spain'), ('Sri Lanka', '🇱🇰 Sri Lanka'), ('Sudan', '🇸🇩 Sudan'),
    ('Sweden', '🇸🇪 Sweden'), ('Switzerland', '🇨🇭 Switzerland'), ('Syria', '🇸🇾 Syria'),
    ('Taiwan', '🇹🇼 Taiwan'), ('Tajikistan', '🇹🇯 Tajikistan'), ('Tanzania', '🇹🇿 Tanzania'),
    ('Thailand', '🇹🇭 Thailand'), ('Tunisia', '🇹🇳 Tunisia'), ('Turkey', '🇹🇷 Turkey'),
    ('Turkmenistan', '🇹🇲 Turkmenistan'), ('Ukraine', '🇺🇦 Ukraine'),
    ('United Arab Emirates', '🇦🇪 United Arab Emirates'), ('United Kingdom', '🇬🇧 United Kingdom'),
    ('United States', '🇺🇸 United States'), ('Uruguay', '🇺🇾 Uruguay'),
    ('Uzbekistan', '🇺🇿 Uzbekistan'), ('Venezuela', '🇻🇪 Venezuela'), ('Vietnam', '🇻🇳 Vietnam'),
    ('Yemen', '🇾🇪 Yemen'),
]


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        required=False,
        label='Quốc gia',
        widget=forms.HiddenInput(),
    )
    referral_code_input = forms.CharField(
        required=False,
        label='Mã giới thiệu',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập mã giới thiệu (nếu có)',
            'autocomplete': 'off',
            'style': 'text-transform:uppercase',
        }),
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'country']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'autocomplete': 'new-password', 'id': 'id_password1', 'class': 'form-control pw-with-toggle'})
        self.fields['password2'].widget.attrs.update({'autocomplete': 'new-password', 'id': 'id_password2', 'class': 'form-control pw-with-toggle'})
        self.fields['referral_code_input'].widget.attrs.update({'class': 'form-control', 'style': 'text-transform:uppercase'})

    def clean_referral_code_input(self):
        code = self.cleaned_data.get('referral_code_input', '').strip().upper()
        if not code:
            return ''
        if not CustomUser.objects.filter(referral_code=code).exists():
            raise forms.ValidationError('Mã giới thiệu không hợp lệ.')
        return code

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
