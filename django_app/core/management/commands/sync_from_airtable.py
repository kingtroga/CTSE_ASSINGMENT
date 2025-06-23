# core/management/commands/sync_from_airtable.py
from django.core.management.base import BaseCommand
from core.airtable_sync import airtable_sync
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync data FROM Airtable TO Django (for cron jobs)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='all',
            choices=['all', 'inventory', 'sku_mappings'],
            help='Type of data to sync'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of records to sync'
        )
        
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Run quietly without progress output'
        )

    def handle(self, *args, **options):
        sync_type = options['type']
        limit = options['limit']
        quiet = options['quiet']
        
        if not quiet:
            self.stdout.write("🔄 Starting Airtable → Django sync...")
            if sync_type != 'all':
                self.stdout.write(f"📊 Syncing {sync_type}...")
            if limit:
                self.stdout.write(f"🔢 Limited to {limit} records")
        
        try:
            results = airtable_sync.sync_from_airtable(
                model_type=sync_type,
                limit=limit
            )
            
            if not quiet:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Sync complete! "
                        f"Created: {results['created']}, "
                        f"Updated: {results['updated']}, "
                        f"Errors: {results['errors']}"
                    )
                )
                
            # Log for monitoring
            logger.info(f"Airtable sync completed: {results}")
            
        except Exception as e:
            error_msg = f"❌ Sync failed: {str(e)}"
            if not quiet:
                self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise