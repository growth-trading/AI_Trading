from django.db import models
from django.conf import settings


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
