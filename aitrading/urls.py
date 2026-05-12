from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.defaults import page_not_found
from trading import views as trading_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', trading_views.landing, name='landing'),
    path('accounts/', include('accounts.urls')),
    path('deposit/', include('deposits.urls')),
    path('trading/', include('trading.urls')),
    path('profile/', include('profiles.urls')),
    # Catch-all: show custom 404 for any unmatched URL
    re_path(r'^.*$', lambda r, **kw: page_not_found(r, None)),
]

if settings.DEBUG:
    urlpatterns = (
        static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        + urlpatterns
    )
