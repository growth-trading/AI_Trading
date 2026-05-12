from django import forms
from accounts.models import CustomUser

_ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
_MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'content_type'):
            if avatar.content_type not in _ALLOWED_IMAGE_TYPES:
                raise forms.ValidationError('Chỉ cho phép file ảnh (JPEG, PNG, GIF, WebP).')
            if avatar.size > _MAX_AVATAR_SIZE:
                raise forms.ValidationError('Kích thước ảnh tối đa là 5 MB.')
        return avatar
