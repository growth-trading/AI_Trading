import secrets
import string
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    # unique=True ở DB level — chặn race condition 2 user đăng ký cùng email đồng thời
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    coins = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_email_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    ai_trading_expires_at = models.DateTimeField(null=True, blank=True)
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
