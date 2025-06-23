# core/urls.py
from django.urls import path
from . import views

# Would have used this but Airtable's free tier does not support it 
urlpatterns = [
    path('webhook/airtable/', views.airtable_webhook, name='airtable_webhook'),
]
