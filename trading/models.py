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
    is_coming_soon = models.BooleanField(default=False, verbose_name='Chuẩn bị ra mắt', help_text='Hiện thị giao diện "Sắp ra mắt", ẩn nút mua.')
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


class AIPlanSettings(models.Model):
    """Singleton — cấu hình giá gói AI Trading qua Admin."""
    week_cost = models.PositiveIntegerField(default=20, verbose_name='Giá gói tuần (xu)')
    month_cost = models.PositiveIntegerField(default=50, verbose_name='Giá gói tháng (xu)')
    year_cost = models.PositiveIntegerField(default=400, verbose_name='Giá gói năm (xu)')

    class Meta:
        verbose_name = 'Giá gói AI Trading'
        verbose_name_plural = 'Giá gói AI Trading'

    def __str__(self):
        return f'Tuần: {self.week_cost}xu / Tháng: {self.month_cost}xu / Năm: {self.year_cost}xu'

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'week_cost': 20,
            'month_cost': 50,
            'year_cost': 400,
        })
        return obj


class BrokerLink(models.Model):
    CATEGORY_CHOICES = [
        ('forex', 'Forex'),
        ('crypto', 'Crypto'),
        ('cfd', 'CFD'),
        ('stock', 'Chứng khoán'),
        ('other', 'Khác'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    logo = models.ImageField(upload_to='broker_logos/', blank=True, null=True, help_text='Upload ảnh logo sàn')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='forex')
    register_url = models.URLField(help_text='Link đăng ký IB/affiliate')
    partner_code = models.CharField(max_length=100, blank=True, help_text='Mã đối tác / mã mời')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Broker / Sàn giao dịch'
        verbose_name_plural = 'Brokers / Sàn giao dịch'

    def __str__(self):
        return self.name


class ChartAnalysisLog(models.Model):
    SIGNAL_CHOICES = [('BUY', 'BUY'), ('SELL', 'SELL'), ('HOLD', 'HOLD')]
    TRADE_STATUS_CHOICES = [('', 'Chưa kiểm tra'), ('TP', 'Chạm TP'), ('SL', 'Chạm SL')]

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
    trade_status = models.CharField(max_length=2, choices=TRADE_STATUS_CHOICES, default='', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
