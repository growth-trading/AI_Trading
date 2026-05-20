from django import forms
from PIL import Image, UnidentifiedImageError
from accounts.models import CustomUser

_MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
_ALLOWED_PIL_FORMATS = {'JPEG', 'PNG', 'GIF', 'WEBP'}


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone', 'address', 'country', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.HiddenInput(),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'read'):
            if avatar.size > _MAX_AVATAR_SIZE:
                raise forms.ValidationError('Kích thước ảnh tối đa là 5 MB.')
            # Validate actual file content via PIL (không tin browser content_type)
            try:
                avatar.seek(0)
                img = Image.open(avatar)
                img_format = img.format  # lưu trước khi verify() đóng file handle
                img.verify()
            except (UnidentifiedImageError, OSError, SyntaxError):
                raise forms.ValidationError('File không phải ảnh hợp lệ.')
            finally:
                avatar.seek(0)
            if img_format not in _ALLOWED_PIL_FORMATS:
                raise forms.ValidationError('Chỉ cho phép file ảnh (JPEG, PNG, GIF, WebP).')
        return avatar
