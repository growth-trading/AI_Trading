from django.urls import path
from . import views

urlpatterns = [
    path('', views.trading_view, name='trading'),
    path('analyze/', views.analyze_chart_view, name='analyze_chart'),
    path('subscribe/', views.subscribe_ai_trading_view, name='subscribe_ai'),
]
