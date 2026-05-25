from django.contrib import admin
from .models import TradingViewProduct, UserTVSubscription, ChartAnalysisLog, AIPlanSettings


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


@admin.register(ChartAnalysisLog)
class ChartAnalysisLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'symbol', 'interval', 'signal', 'confidence', 'created_at')
    list_filter = ('signal', 'symbol')
    readonly_fields = ('created_at',)
