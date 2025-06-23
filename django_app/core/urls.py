# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('webhook/airtable/', views.airtable_webhook, name='airtable_webhook'),
]
