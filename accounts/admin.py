from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'coins', 'is_email_verified', 'date_joined']
    list_filter = ['is_email_verified', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin AITrading', {'fields': (
            'avatar', 'coins', 'is_email_verified',
            'phone', 'address', 'ai_trading_expires_at',
        )}),
        ('OTP', {'fields': ('otp_code', 'otp_created_at'), 'classes': ('collapse',)}),
    )
