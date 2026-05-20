from django.db import models
from django.conf import settings
from django.utils import timezone


class TradingViewProduct(models.Model):
    slug = models.SlugField(unique=True, max_length=50)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True, help_text='English name (optional)')
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True, help_text='English description (optional)')
    chart_id = models.CharField(max_length=50, help_text='TradingView chart ID from URL')

    features = models.TextField(
        blank=True,
        help_text='Mỗi dòng = 1 tính năng (Tiếng Việt). Ví dụ:\nChart real-time chuyên gia\nMACD · RSI · EMA · Supertrend',
    )
    features_en = models.TextField(
        blank=True,
        help_text='English features, one per line. Leave blank to use Vietnamese.',
    )
    week_cost = models.PositiveIntegerField(default=10)
    month_cost = models.PositiveIntegerField(default=30)
    year_cost = models.PositiveIntegerField(default=200)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'pk']

    def __str__(self):
        return self.name

    @property
    def features_list(self):
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    @property
    def features_en_list(self):
        lines = self.features_en.strip()
        if not lines:
            return self.features_list
        return [f.strip() for f in lines.splitlines() if f.strip()]


class UserTVSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tv_subscriptions',
    )
    product = models.ForeignKey(TradingViewProduct, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()

    class Meta:
        unique_together = ('user', 'product')

    @property
    def is_active(self):
        return self.expires_at > timezone.now()

    def __str__(self):
        return f'{self.user} — {self.product}'


class ChartAnalysisLog(models.Model):
    SIGNAL_CHOICES = [('BUY', 'BUY'), ('SELL', 'SELL'), ('HOLD', 'HOLD')]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chart_analyses',
    )
    symbol = models.CharField(max_length=50)
    interval = models.CharField(max_length=10)
    signal = models.CharField(max_length=10, choices=SIGNAL_CHOICES)
    confidence = models.IntegerField(default=0)
    entry = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    sl = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    tp = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    reasoning = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
