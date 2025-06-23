
# core/management/commands/test_airtable_connection.py
from django.core.management.base import BaseCommand
from core.airtable_sync import airtable_sync

class Command(BaseCommand):
    help = 'Test Airtable connection and permissions'
    
    def handle(self, *args, **options):
        self.stdout.write("🔍 Testing Airtable connection...")
        
        if airtable_sync._validate_connection():
            self.stdout.write("✅ Connection successful!")
        else:
            self.stdout.write("❌ Connection failed!")