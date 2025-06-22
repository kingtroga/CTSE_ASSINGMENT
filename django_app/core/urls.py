from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_daily_report, name='upload_report'),
    path('sync-baserow/', views.sync_baserow, name='sync_baserow'),
]