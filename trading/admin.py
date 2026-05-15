from django.contrib import admin
from .models import TradingViewProduct, UserTVSubscription, ChartAnalysisLog


@admin.register(TradingViewProduct)
class TradingViewProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'chart_id', 'symbol', 'interval', 'week_cost', 'month_cost', 'year_cost', 'is_active', 'sort_order')
    list_editable = ('chart_id', 'symbol', 'interval', 'week_cost', 'month_cost', 'year_cost', 'is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {'fields': ('slug', 'chart_id', 'symbol', 'interval', 'is_active', 'sort_order', 'week_cost', 'month_cost', 'year_cost')}),
        ('Tiếng Việt', {'fields': ('name', 'description')}),
        ('English', {'fields': ('name_en', 'description_en'), 'classes': ('collapse',)}),
    )


@admin.register(UserTVSubscription)
class UserTVSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'expires_at')
    list_filter = ('product',)
    raw_id_fields = ('user',)


@admin.register(ChartAnalysisLog)
class ChartAnalysisLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'symbol', 'interval', 'signal', 'confidence', 'created_at')
    list_filter = ('signal', 'symbol')
    readonly_fields = ('created_at',)
