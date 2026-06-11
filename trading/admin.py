from django.contrib import admin
from .models import TradingViewProduct, UserTVSubscription, ChartAnalysisLog, AIPlanSettings, BrokerLink, CopyTradeExchange, TradingSignal


@admin.register(TradingViewProduct)
class TradingViewProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'chart_id', 'week_cost', 'month_cost', 'year_cost', 'is_active', 'is_coming_soon', 'sort_order')
    list_editable = ('chart_id', 'week_cost', 'month_cost', 'year_cost', 'is_active', 'is_coming_soon', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {'fields': ('slug', 'chart_id', 'is_active', 'is_coming_soon', 'sort_order', 'week_cost', 'month_cost', 'year_cost')}),
        ('Tiếng Việt', {'fields': ('name', 'description', 'features')}),
        ('English', {'fields': ('name_en', 'description_en', 'features_en'), 'classes': ('collapse',)}),
    )


@admin.register(AIPlanSettings)
class AIPlanSettingsAdmin(admin.ModelAdmin):
    list_display = ('week_cost', 'month_cost', 'year_cost')

    def has_add_permission(self, request):
        return not AIPlanSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserTVSubscription)
class UserTVSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'expires_at')
    list_filter = ('product',)
    raw_id_fields = ('user',)


@admin.register(BrokerLink)
class BrokerLinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category', 'partner_code', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    list_filter = ('category', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    fields = ('name', 'slug', 'category', 'logo', 'register_url', 'partner_code', 'is_active', 'sort_order')


@admin.register(CopyTradeExchange)
class CopyTradeExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'copy_trade_url', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'slug', 'logo', 'copy_trade_url', 'register_url', 'is_active', 'sort_order'),
        }),
        ('Hiển thị card', {
            'fields': ('tag_vi', 'tag_en', 'trader_count', 'trader_count_label_vi', 'trader_count_label_en'),
        }),
        ('Tính năng (VI)', {'fields': ('copy_features',)}),
        ('Tính năng (EN)', {'fields': ('copy_features_en',), 'classes': ('collapse',)}),
        ('Hướng dẫn (VI)', {'fields': ('guide_steps',)}),
        ('Hướng dẫn (EN)', {'fields': ('guide_steps_en',), 'classes': ('collapse',)}),
    )


@admin.register(ChartAnalysisLog)
class ChartAnalysisLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'symbol', 'interval', 'signal', 'confidence', 'created_at')
    list_filter = ('signal', 'symbol')
    readonly_fields = ('created_at',)


@admin.register(TradingSignal)
class TradingSignalAdmin(admin.ModelAdmin):
    list_display = ('signal_type', 'symbol', 'timeframe', 'entry', 'sl', 'status', 'created_at')
    list_editable = ('status',)
    list_filter = ('signal_type', 'symbol', 'status')
    fieldsets = (
        ('Tín hiệu', {'fields': ('signal_type', 'symbol', 'timeframe', 'status', 'created_at')}),
        ('Giá', {'fields': ('entry', 'sl')}),
        ('Take Profit', {'fields': ('tp1', 'tp2', 'tp3', 'tp4', 'tp5')}),
        ('Ghi chú', {'fields': ('note',)}),
    )
