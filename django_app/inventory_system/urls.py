from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


# Error handlers
handler404 = 'web.views.custom_404_view'
handler500 = 'web.views.custom_500_view'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('core/', include('core.urls')),
    path('', include('web.urls')),
]
# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
