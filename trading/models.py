from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import URLValidator


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
    register_url = models.URLField(
        help_text='Link đăng ký IB/affiliate',
        validators=[URLValidator(schemes=['http', 'https'])],
    )
    partner_code = models.CharField(max_length=100, blank=True, help_text='Mã đối tác / mã mời')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Broker / Sàn giao dịch'
        verbose_name_plural = 'Brokers / Sàn giao dịch'

    def __str__(self):
        return self.name


class CopyTradeExchange(models.Model):
    name = models.CharField(max_length=100, verbose_name='Tên sàn')
    slug = models.SlugField(max_length=50, unique=True)
    logo = models.ImageField(upload_to='copytrade_logos/', blank=True, null=True, verbose_name='Logo sàn')
    copy_trade_url = models.URLField(verbose_name='Link Copy Trade', help_text='Link tới trang Copy Trade của sàn')
    register_url = models.URLField(blank=True, verbose_name='Link đăng ký affiliate', help_text='Link đăng ký IB/affiliate (nút Đăng Ký)')
    tag_vi = models.CharField(max_length=80, blank=True, verbose_name='Badge tag (VI)', help_text='Vd: Đề xuất cho người mới')
    tag_en = models.CharField(max_length=80, blank=True, verbose_name='Badge tag (EN)')
    trader_count = models.CharField(max_length=20, blank=True, verbose_name='Số trader', help_text='Vd: 3,000+')
    trader_count_label_vi = models.CharField(max_length=60, blank=True, default='Trader để chọn', verbose_name='Nhãn số trader (VI)')
    trader_count_label_en = models.CharField(max_length=60, blank=True, default='Traders available', verbose_name='Nhãn số trader (EN)')
    copy_features = models.TextField(blank=True, verbose_name='Tính năng (VI)', help_text='Mỗi dòng 1 tính năng')
    copy_features_en = models.TextField(blank=True, verbose_name='Tính năng (EN)', help_text='Mỗi dòng 1 tính năng. Để trống = dùng bản VI.')
    guide_steps = models.TextField(blank=True, verbose_name='Hướng dẫn các bước (VI)', help_text='Mỗi dòng 1 bước. Vd: Truy cập link và đăng nhập tài khoản')
    guide_steps_en = models.TextField(blank=True, verbose_name='Hướng dẫn các bước (EN)', help_text='Mỗi dòng 1 bước. Để trống = dùng bản VI.')
    is_active = models.BooleanField(default=True, verbose_name='Hiển thị')
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Thứ tự')

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Copy Trade — Sàn giao dịch'
        verbose_name_plural = 'Copy Trade — Sàn giao dịch'

    def __str__(self):
        return self.name

    @property
    def copy_features_list(self):
        return [f.strip() for f in self.copy_features.splitlines() if f.strip()]

    @property
    def copy_features_en_list(self):
        lines = self.copy_features_en.strip()
        if not lines:
            return self.copy_features_list
        return [f.strip() for f in lines.splitlines() if f.strip()]

    @property
    def copy_features_pairs(self):
        vi = self.copy_features_list
        en = self.copy_features_en_list
        length = max(len(vi), len(en)) if (vi or en) else 0
        vi = vi + [''] * (length - len(vi))
        en = en + [''] * (length - len(en))
        return list(zip(vi, en))

    @property
    def guide_steps_list(self):
        return [s.strip() for s in self.guide_steps.splitlines() if s.strip()]

    @property
    def guide_steps_en_list(self):
        lines = self.guide_steps_en.strip()
        if not lines:
            return self.guide_steps_list
        return [s.strip() for s in lines.splitlines() if s.strip()]

    @property
    def guide_steps_pairs(self):
        vi = self.guide_steps_list
        en = self.guide_steps_en_list
        length = max(len(vi), len(en)) if (vi or en) else 0
        vi = vi + [''] * (length - len(vi))
        en = en + [''] * (length - len(en))
        return list(zip(vi, en))


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


class TradingSignal(models.Model):
    SIGNAL_TYPE = [('BUY', 'BUY'), ('SELL', 'SELL')]
    STATUS = [
        ('active', 'Đang chạy'),
        ('tp1', 'Chạm TP1'), ('tp2', 'Chạm TP2'), ('tp3', 'Chạm TP3'),
        ('tp4', 'Chạm TP4'), ('tp5', 'Chạm TP5'),
        ('sl', 'Chạm SL'), ('closed', 'Đã đóng'),
    ]

    signal_type = models.CharField(max_length=4, choices=SIGNAL_TYPE)
    symbol = models.CharField(max_length=20, default='XAUUSD')
    timeframe = models.CharField(max_length=10, default='5m')
    entry = models.DecimalField(max_digits=14, decimal_places=2)
    tp1 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    tp2 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    tp3 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    tp4 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    tp5 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    sl = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS, default='active')
    note = models.TextField(blank=True, help_text='Ghi chú thêm (tuỳ chọn)')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tín hiệu giao dịch'
        verbose_name_plural = 'Tín hiệu giao dịch'

    def __str__(self):
        return f"{self.signal_type} {self.symbol} @ {self.entry} — {self.get_status_display()}"

    @property
    def tps_reached(self):
        return {'tp1': 1, 'tp2': 2, 'tp3': 3, 'tp4': 4, 'tp5': 5}.get(self.status, 0)

    @property
    def tp_list(self):
        return [(i, getattr(self, f'tp{i}')) for i in range(1, 6) if getattr(self, f'tp{i}') is not None]
