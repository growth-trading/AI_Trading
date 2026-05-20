from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'username', 'email', 'coins', 'is_email_verified',
        'referral_code', 'referred_by', 'referral_coins_earned', 'date_joined',
    ]
    list_filter = ['is_email_verified', 'is_staff']
    search_fields = ['username', 'email', 'referral_code']
    readonly_fields = ['referral_code', 'referral_coins_earned', 'memo_code']
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin RichAITrading', {'fields': (
            'avatar', 'coins', 'is_email_verified',
            'phone', 'address', 'country', 'ai_trading_expires_at',
        )}),
        ('Giới thiệu', {'fields': (
            'referral_code', 'memo_code', 'referred_by', 'referral_coins_earned',
        )}),
        ('OTP', {'fields': ('otp_code', 'otp_created_at'), 'classes': ('collapse',)}),
    )
