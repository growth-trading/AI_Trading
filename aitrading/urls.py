from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from trading import views as trading_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', trading_views.landing, name='landing'),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('accounts.dashboard_urls')),
    path('deposit/', include('deposits.urls')),
    path('trading/', include('trading.urls')),
    path('profile/', include('profiles.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
