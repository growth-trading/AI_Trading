from django.urls import path
from . import views

urlpatterns = [
    path('', views.deposit_view, name='deposit'),
    path('submit/', views.submit_txhash_view, name='submit_txhash'),
    path('status/<int:deposit_id>/', views.check_deposit_status, name='deposit_status'),
]
