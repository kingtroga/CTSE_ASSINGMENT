from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView


urlpatterns = [
    path('', RedirectView.as_view(url='/web/', permanent=True)),
    path('admin/', admin.site.urls),
    path('core/', include('core.urls')),
    path('web/', include('web.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'core.views.custom_404_view'
handler500 = 'core.views.custom_500_view'