from django.contrib import admin
from .models import DepositTransaction


@admin.register(DepositTransaction)
class DepositTransactionAdmin(admin.ModelAdmin):
    list_display = ['tx_hash_short', 'user', 'amount_usdt', 'coins_credited', 'status', 'created_at']
    list_filter = ['status', 'network']
    search_fields = ['tx_hash', 'user__username']
    readonly_fields = ['tx_hash', 'created_at', 'confirmed_at']

    def tx_hash_short(self, obj):
        return f"{obj.tx_hash[:16]}..."
    tx_hash_short.short_description = 'TxHash'
