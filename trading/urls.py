from django.urls import path
from . import views

urlpatterns = [
    path('', views.trading_view, name='trading'),
]
