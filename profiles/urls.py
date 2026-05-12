from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
]
