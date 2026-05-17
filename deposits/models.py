from django.db import models
from django.conf import settings


class DepositTransaction(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Đang chờ'),
        (STATUS_COMPLETED, 'Hoàn thành'),
        (STATUS_FAILED, 'Thất bại'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deposits',
    )
    tx_hash = models.CharField(max_length=100, unique=True, db_index=True)
    amount_usdt = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    coins_credited = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    network = models.CharField(max_length=10, default='BSC')
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tx_hash[:16]}... | {self.amount_usdt} USDT | {self.status}"
