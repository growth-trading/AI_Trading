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

_REFERRAL_F1_RATE = Decimal('40')
_REFERRAL_F2_RATE = Decimal('20')


def _gen_referral_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


def _avatar_upload_to(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    return f'avatars/{uuid.uuid4().hex}.{ext}'


def pay_referral_commission(depositor_pk: int, coins_amount) -> None:
    """Trả hoa hồng F1 (40%) và F2 (20%) ngay khi người được giới thiệu nạp tiền."""
    try:
        depositor = CustomUser.objects.select_related(
            'referred_by', 'referred_by__referred_by'
        ).get(pk=depositor_pk)
    except CustomUser.DoesNotExist:
        return

    amount = Decimal(str(coins_amount))
    f1 = depositor.referred_by
    if not f1:
        return
    f1_bonus = (amount * _REFERRAL_F1_RATE / 100).quantize(Decimal('0.01'))
    if f1_bonus > 0:
        CustomUser.objects.filter(pk=f1.pk).update(
            referral_coins_earned=F('referral_coins_earned') + f1_bonus,
        )
        logger.info('Referral F1 commission: +%s earned to user %s (from deposit by %s)', f1_bonus, f1.pk, depositor_pk)

    f2 = f1.referred_by
    if not f2:
        return
    f2_bonus = (amount * _REFERRAL_F2_RATE / 100).quantize(Decimal('0.01'))
    if f2_bonus > 0:
        CustomUser.objects.filter(pk=f2.pk).update(
            referral_coins_earned=F('referral_coins_earned') + f2_bonus,
        )
        logger.info('Referral F2 commission: +%s earned to user %s (from deposit by %s)', f2_bonus, f2.pk, depositor_pk)


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
