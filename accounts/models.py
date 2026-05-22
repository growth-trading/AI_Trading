import logging
import secrets
import string
import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)

_REFERRAL_F1_RATE = Decimal('40')  # fallback nếu chưa có DB config
_REFERRAL_F2_RATE = Decimal('20')


def _gen_referral_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


def _avatar_upload_to(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    return f'avatars/{uuid.uuid4().hex}.{ext}'


def pay_referral_commission(buyer_pk: int, coins_amount) -> None:
    """Trả hoa hồng F1 (40%) và F2 (20%) khi người được giới thiệu mua dịch vụ."""
    try:
        depositor = CustomUser.objects.select_related(
            'referred_by', 'referred_by__referred_by'
        ).get(pk=buyer_pk)
    except CustomUser.DoesNotExist:
        return

    amount = Decimal(str(coins_amount))
    f1 = depositor.referred_by
    if not f1:
        return
    cfg = ReferralSettings.get()
    f1_bonus = (amount * cfg.f1_rate / 100).quantize(Decimal('0.01'))
    if f1_bonus > 0:
        CustomUser.objects.filter(pk=f1.pk).update(
            referral_coins_earned=F('referral_coins_earned') + f1_bonus,
        )
        logger.info('Referral F1 commission: +%s earned to user %s (from purchase by %s)', f1_bonus, f1.pk, buyer_pk)

    f2 = f1.referred_by
    if not f2:
        return
    f2_bonus = (amount * cfg.f2_rate / 100).quantize(Decimal('0.01'))
    if f2_bonus > 0:
        CustomUser.objects.filter(pk=f2.pk).update(
            referral_coins_earned=F('referral_coins_earned') + f2_bonus,
        )
        logger.info('Referral F2 commission: +%s earned to user %s (from purchase by %s)', f2_bonus, f2.pk, buyer_pk)


class CustomUser(AbstractUser):
    # unique=True ở DB level — chặn race condition 2 user đăng ký cùng email đồng thời
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to=_avatar_upload_to, null=True, blank=True)
    coins = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_email_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    referral_code = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    referral_coins_earned = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    referred_by = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='referrals'
    )
    payout_wallet = models.CharField(max_length=42, blank=True, help_text='Địa chỉ ví BSC (BEP-20) để nhận hoa hồng USDT')
    ai_trading_expires_at = models.DateTimeField(null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.referral_code:
            code = _gen_referral_code()
            while CustomUser.objects.filter(referral_code=code).exists():
                code = _gen_referral_code()
            self.referral_code = code
        super().save(*args, **kwargs)

    @property
    def memo_code(self):
        return f"UID-{self.pk:04d}"

    @property
    def has_ai_trading_access(self):
        if not self.ai_trading_expires_at:
            return False
        return self.ai_trading_expires_at > timezone.now()

    def generate_otp(self):
        self.otp_code = ''.join(secrets.choice(string.digits) for _ in range(6))
        self.otp_created_at = timezone.now()
        self.save(update_fields=['otp_code', 'otp_created_at'])
        return self.otp_code

    def is_otp_valid(self, code):
        if not self.otp_code or not self.otp_created_at:
            return False
        expired = timezone.now() > self.otp_created_at + timezone.timedelta(minutes=10)
        return not expired and secrets.compare_digest(self.otp_code, code)

    def __str__(self):
        return self.username


class ReferralSettings(models.Model):
    """Singleton — chỉ có 1 row. Quản lý tỷ lệ hoa hồng qua Admin."""
    f1_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=40,
        verbose_name='Tỷ lệ F1 (%)',
        help_text='Hoa hồng cấp 1 (người trực tiếp giới thiệu). Mặc định: 40%'
    )
    f2_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=20,
        verbose_name='Tỷ lệ F2 (%)',
        help_text='Hoa hồng cấp 2 (người giới thiệu người giới thiệu). Mặc định: 20%'
    )

    class Meta:
        verbose_name = 'Cấu hình hoa hồng'
        verbose_name_plural = 'Cấu hình hoa hồng'

    def __str__(self):
        return f'F1: {self.f1_rate}% / F2: {self.f2_rate}%'

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ReferralPayout(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        ('PENDING', 'Đang xử lý'),
        ('COMPLETED', 'Hoàn tất'),
        ('FAILED', 'Thất bại'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='referral_payouts')
    wallet_address = models.CharField(max_length=42)
    amount_coins = models.DecimalField(max_digits=18, decimal_places=2)
    amount_usdt = models.DecimalField(max_digits=18, decimal_places=6)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    tx_hash = models.CharField(max_length=66, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.amount_usdt} USDT — {self.status}'
