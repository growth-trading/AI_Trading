import random
import string
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    coins = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_email_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    @property
    def memo_code(self):
        return f"UID-{self.pk:04d}"

    def generate_otp(self):
        self.otp_code = ''.join(random.choices(string.digits, k=6))
        self.otp_created_at = timezone.now()
        self.save(update_fields=['otp_code', 'otp_created_at'])
        return self.otp_code

    def is_otp_valid(self, code):
        if not self.otp_code or not self.otp_created_at:
            return False
        expired = timezone.now() > self.otp_created_at + timezone.timedelta(minutes=10)
        return not expired and self.otp_code == code

    def __str__(self):
        return self.username
