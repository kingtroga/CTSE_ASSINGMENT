
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import SKUMapping, Product, ComboProduct, Inventory, InventoryMovement
from .airtable_sync import airtable_sync
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=SKUMapping)
def sync_sku_mapping_on_save(sender, instance, created, **kwargs):
    """Auto-sync SKU mapping to Airtable when saved"""
    try:
        airtable_sync.sync_sku_mapping_to_airtable(instance)
        action = "Created" if created else "Updated"
        logger.info(f"✅ {action} SKU mapping {instance.sku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync SKU mapping {instance.sku}: {e}")

@receiver(post_save, sender=Product)
def sync_product_on_save(sender, instance, created, **kwargs):
    """Auto-sync product inventory to Airtable when saved"""
    try:
        airtable_sync.sync_product_to_airtable(instance)
        action = "Created" if created else "Updated"
        logger.info(f"✅ {action} product {instance.msku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync product {instance.msku}: {e}")

@receiver(post_save, sender=ComboProduct)
def sync_combo_product_on_save(sender, instance, created, **kwargs):
    """Auto-sync combo product to Airtable when saved"""
    try:
        airtable_sync.sync_combo_product_to_airtable(instance)
        action = "Created" if created else "Updated"
        logger.info(f"✅ {action} combo product {instance.combo_sku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync combo product {instance.combo_sku}: {e}")

@receiver(post_save, sender=Inventory)
def sync_inventory_on_save(sender, instance, created, **kwargs):
    """Auto-sync inventory changes to Airtable"""
    try:
        airtable_sync.sync_product_to_airtable(instance.product)
        logger.info(f"✅ Inventory change for {instance.product.msku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync inventory for {instance.product.msku}: {e}")

@receiver(post_save, sender=InventoryMovement)
def sync_inventory_movement_on_save(sender, instance, created, **kwargs):
    """Auto-sync when inventory movements occur"""
    try:
        airtable_sync.sync_product_to_airtable(instance.product)
        logger.info(f"✅ Inventory movement for {instance.product.msku} synced to Airtable")
    except Exception as e:
        logger.error(f"❌ Failed to sync inventory movement for {instance.product.msku}: {e}")