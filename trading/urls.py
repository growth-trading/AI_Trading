from django.urls import path
from . import views

urlpatterns = [
    path('', views.trading_view, name='trading'),
    path('analyze/', views.analyze_chart_view, name='analyze_chart'),
    path('subscribe/', views.subscribe_ai_trading_view, name='subscribe_ai'),
    path('chart-data/', views.chart_data_view, name='chart_data'),
    path('tick/', views.tick_view, name='tick'),
    path('tradingview/', views.tradingview_view, name='tradingview'),
    path('tradingview/subscribe/', views.subscribe_tradingview_view, name='subscribe_tradingview'),
    path('trade-status/<int:log_id>/', views.trade_status_view, name='trade_status'),
]
