from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Sum
from .models import CustomUser, ReferralPayout, ReferralSettings


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    change_list_template = 'admin/accounts/customuser/change_list.html'

    list_display = [
        'username', 'email', 'coins', 'is_email_verified',
        'referral_code', 'referred_by', 'referral_coins_earned', 'date_joined',
    ]
    list_filter = ['is_email_verified', 'is_staff']
    search_fields = ['username', 'email', 'referral_code']
    readonly_fields = ['referral_code']
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin RichAITrading', {'fields': (
            'avatar', 'coins', 'is_email_verified',
            'phone', 'address', 'country', 'ai_trading_expires_at',
        )}),
        ('Giới thiệu', {'fields': (
            'referral_code', 'referred_by', 'referral_coins_earned', 'payout_wallet',
        )}),
        ('OTP', {'fields': ('otp_code', 'otp_created_at'), 'classes': ('collapse',)}),
    )

    def changelist_view(self, request, extra_context=None):
        from deposits.models import DepositTransaction

        total_deposited = (
            DepositTransaction.objects
            .filter(status=DepositTransaction.STATUS_COMPLETED)
            .aggregate(total=Sum('coins_credited'))['total'] or 0
        )
        total_f1 = self.model.objects.filter(referred_by__isnull=False).count()
        total_f2 = self.model.objects.filter(referred_by__referred_by__isnull=False).count()
        total_commission = (
            ReferralPayout.objects
            .filter(status=ReferralPayout.STATUS_COMPLETED)
            .aggregate(total=Sum('amount_coins'))['total'] or 0
        )

        extra_context = extra_context or {}
        extra_context['overview_stats'] = {
            'total_deposited': f'{total_deposited:,.2f}',
            'total_f1': total_f1,
            'total_f2': total_f2,
            'total_commission': f'{total_commission:,.2f}',
        }
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ReferralSettings)
class ReferralSettingsAdmin(admin.ModelAdmin):
    fields = ('f1_rate', 'f2_rate')

    def has_add_permission(self, request):
        return not ReferralSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReferralPayout)
class ReferralPayoutAdmin(admin.ModelAdmin):
    list_display = ('user', 'wallet_address', 'amount_coins', 'amount_usdt', 'status', 'tx_hash', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('user', 'wallet_address', 'amount_coins', 'amount_usdt', 'tx_hash', 'error_message', 'created_at', 'processed_at')
    search_fields = ('user__username', 'wallet_address', 'tx_hash')
