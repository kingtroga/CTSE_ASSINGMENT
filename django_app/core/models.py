# core/models.py - Step 2: Foundation Models

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# =============================================================================
# Step 2A: Core Foundation Models
# =============================================================================

class Product(models.Model):
    """Master product model (MSKU level) - matches your cleaned inventory data"""
    
    # Primary identifier (matches your cleaned data: msku column)
    msku = models.CharField(max_length=100, unique=True, primary_key=True, 
                           help_text="Master SKU - unique product identifier")
    
    # Product details (matches your cleaned data: Product Name column)
    product_name = models.CharField(max_length=255, 
                                   help_text="Product name from inventory data")
    
    # Optional product categorization
    category = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    
    # Pricing (for combo calculations)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, 
                                    blank=True, null=True,
                                    help_text="Cost price for margin calculations")
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['msku']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
    
    def __str__(self):
        return f"{self.msku} - {self.product_name}"
    
    @property
    def total_stock(self):
        """Calculate total stock across all warehouses"""
        return sum(inv.current_stock for inv in self.inventory_records.all())


class Warehouse(models.Model):
    """Warehouse/fulfillment center model - matches your 15 warehouse columns"""
    
    # Warehouse codes from your data: TLCQ, BLR7, BLR8, BOM5, BOM7, CCU1, 
    # CCX1, DEL4, DEL5, DEX3, PNQ2, PNQ3, SDED, SDEE, XHJ9
    code = models.CharField(max_length=10, unique=True, primary_key=True,
                           help_text="Warehouse code (TLCQ, BLR7, etc.)")
    
    name = models.CharField(max_length=100, 
                           help_text="Human readable warehouse name")
    
    location = models.CharField(max_length=100, 
                               help_text="City/region where warehouse is located")
    
    is_active = models.BooleanField(default=True)
    
    # Contact information (optional for now)
    address = models.TextField(blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'warehouses'
        ordering = ['code']
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def total_products(self):
        """Count of unique products in this warehouse"""
        return self.inventory_records.filter(current_stock__gt=0).count()
    
    @property
    def total_stock_value(self):
        """Total stock units in this warehouse"""
        return sum(inv.current_stock for inv in self.inventory_records.all())


class Inventory(models.Model):
    """Current stock levels per product per warehouse - matches your inventory data structure"""
    
    # Foreign keys to link products and warehouses
    product = models.ForeignKey(Product, on_delete=models.CASCADE, 
                               related_name='inventory_records')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                 related_name='inventory_records')
    
    # Stock levels (matches your inventory columns)
    current_stock = models.IntegerField(default=0, 
                                       help_text="Current available stock")
    buffer_stock = models.IntegerField(default=0, 
                                      help_text="Buffer/safety stock")
    opening_stock = models.IntegerField(default=0, 
                                       help_text="Opening stock for the period")
    
    # Business rules
    reorder_level = models.IntegerField(default=0, 
                                       help_text="Reorder when stock hits this level")
    max_stock_level = models.IntegerField(blank=True, null=True,
                                         help_text="Maximum stock capacity")
    
    # Tracking
    last_updated = models.DateTimeField(auto_now=True)
    last_stock_count_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'inventory'
        unique_together = ['product', 'warehouse']  # One record per product per warehouse
        ordering = ['product', 'warehouse']
        verbose_name = 'Inventory Record'
        verbose_name_plural = 'Inventory Records'
    
    def __str__(self):
        return f"{self.product.msku} @ {self.warehouse.code}: {self.current_stock} units"
    
    @property
    def available_stock(self):
        """Stock available for sale (current - buffer)"""
        return max(0, self.current_stock - self.buffer_stock)
    
    @property
    def is_low_stock(self):
        """Check if stock is below reorder level"""
        return self.current_stock <= self.reorder_level
    
    @property
    def stock_status(self):
        """Human readable stock status"""
        if self.current_stock <= 0:
            return "Out of Stock"
        elif self.is_low_stock:
            return "Low Stock"
        elif self.max_stock_level and self.current_stock >= self.max_stock_level:
            return "Overstocked"
        else:
            return "In Stock"


# =============================================================================
# Step 3A: Marketplace and SKU Mapping Models
# =============================================================================

class Marketplace(models.Model):
    """Marketplace/Panel definitions - matches your 6 sales channels"""
    
    # Your marketplace codes from cleaned data
    MARKETPLACE_CHOICES = [
        ('CSTE_AMAZON', 'CSTE Amazon'),
        ('CSTE_FK', 'CSTE Flipkart'),
        ('CSTE_MEESHO', 'CSTE Meesho'),
        ('GL_FK', 'GL Flipkart'),
        ('RUDRAV_MEESHO', 'Rudrav Meesho'),
        ('MISC', 'Miscellaneous'),
    ]
    
    code = models.CharField(max_length=20, choices=MARKETPLACE_CHOICES, 
                           unique=True, primary_key=True,
                           help_text="Marketplace code (Panel)")
    
    name = models.CharField(max_length=100, 
                           help_text="Human readable marketplace name")
    
    # Business configuration
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
                                         help_text="Commission rate as percentage")
    is_active = models.BooleanField(default=True)
    
    # API configuration (for future integrations)
    api_endpoint = models.URLField(blank=True, null=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplaces'
        ordering = ['code']
        verbose_name = 'Marketplace'
        verbose_name_plural = 'Marketplaces'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def total_skus(self):
        """Count of SKUs mapped to this marketplace"""
        return self.sku_mappings.count()
    
    @property
    def active_skus(self):
        """Count of active SKUs on this marketplace"""
        return self.sku_mappings.filter(status='ACTIVE').count()


class SKUMapping(models.Model):
    """Maps marketplace SKUs to master products - your 5,115 cleaned mappings"""
    
    # Core mapping (matches your cleaned data structure)
    sku = models.CharField(max_length=100, 
                          help_text="Marketplace SKU identifier")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, 
                               related_name='sku_mappings',
                               help_text="Master product (MSKU)")
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE, 
                                   related_name='sku_mappings',
                                   help_text="Sales channel/panel")
    
    # Marketplace specific data (from your cleaned data)
    marketplace_product_url = models.URLField(blank=True, null=True,
                                             help_text="Product URL on marketplace")
    marketplace_price = models.DecimalField(max_digits=10, decimal_places=2, 
                                           blank=True, null=True,
                                           help_text="Listed price on marketplace")
    image_url = models.URLField(blank=True, null=True,
                               help_text="Product image URL")
    
    # Status tracking (matches your Status 1, Status 2 columns)
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('IN_PROGRESS', 'In Progress'),
        ('BLOCKED', 'Blocked'),
        ('PAUSED', 'Paused'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE',
                             help_text="Current listing status")
    
    # Additional status field (for Status 2 from your data)
    status_2 = models.CharField(max_length=20, choices=STATUS_CHOICES, 
                               blank=True, null=True,
                               help_text="Secondary status field")
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sku_mappings'
        unique_together = ['sku', 'marketplace']  # Critical: Your composite key constraint!
        ordering = ['sku', 'marketplace']
        verbose_name = 'SKU Mapping'
        verbose_name_plural = 'SKU Mappings'
        indexes = [
            models.Index(fields=['sku']),  # Fast SKU lookups for daily reports
            models.Index(fields=['marketplace', 'status']),  # Fast marketplace queries
            models.Index(fields=['product']),  # Fast MSKU lookups
        ]
    
    def __str__(self):
        return f"{self.sku} → {self.product.msku} ({self.marketplace.code})"
    
    @property
    def is_active(self):
        """Check if mapping is active"""
        return self.status == 'ACTIVE'
    
    @property
    def has_image(self):
        """Check if product has image URL"""
        return bool(self.image_url)
    
    def clean(self):
        """Validate the mapping"""
        from django.core.exceptions import ValidationError
        
        # Ensure product exists and is active
        if not self.product.is_active:
            raise ValidationError(f"Cannot map to inactive product: {self.product.msku}")
        
        # Ensure marketplace is active
        if not self.marketplace.is_active:
            raise ValidationError(f"Cannot map to inactive marketplace: {self.marketplace.code}")
    
    def save(self, *args, **kwargs):
        # Run validation before saving
        self.clean()
        super().save(*args, **kwargs)


# =============================================================================
# Step 3C: Order and Inventory Movement Models
# =============================================================================

class Order(models.Model):
    """Order tracking - handles both inbound (purchase) and outbound (sales) orders"""
    
    ORDER_TYPE_CHOICES = [
        ('INBOUND', 'Inbound (Purchase/Restock)'),
        ('OUTBOUND', 'Outbound (Sale/Fulfillment)'),
        ('TRANSFER', 'Transfer (Between Warehouses)'),
        ('ADJUSTMENT', 'Inventory Adjustment'),
        ('RETURN', 'Return/Refund'),
    ]
    
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
    ]
    
    # Primary identifier
    order_id = models.CharField(max_length=100, unique=True, primary_key=True,
                               help_text="Unique order identifier")
    
    # Order classification
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES,
                                 help_text="Type of order")
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, 
                             default='PENDING')
    
    # Relationships
    marketplace = models.ForeignKey(Marketplace, on_delete=models.SET_NULL, 
                                   blank=True, null=True,
                                   related_name='orders',
                                   help_text="Source marketplace (for outbound orders)")
    
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE,
                                 related_name='orders',
                                 help_text="Primary warehouse for this order")
    
    # Business data
    order_date = models.DateTimeField(default=timezone.now,
        help_text="When the order was placed/created")
    
    expected_delivery_date = models.DateTimeField(blank=True, null=True,
                                                 help_text="Expected delivery/completion date")
    
    actual_delivery_date = models.DateTimeField(blank=True, null=True,
                                               help_text="Actual delivery/completion date")
    
    # Financial information
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, 
                                      default=0.00,
                                      help_text="Total order value")
    
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, 
                                       default=0.00,
                                       help_text="Shipping/handling cost")
    
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, 
                                    default=0.00,
                                    help_text="Tax amount")
    
    # External references
    external_order_id = models.CharField(max_length=100, blank=True, null=True,
                                        help_text="Marketplace/supplier order ID")
    
    tracking_number = models.CharField(max_length=100, blank=True, null=True,
                                      help_text="Shipping tracking number")
    
    # Customer/supplier information
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    shipping_address = models.TextField(blank=True, null=True,
                                       help_text="Delivery address")
    
    # Notes and metadata
    notes = models.TextField(blank=True, null=True,
                            help_text="Internal notes about the order")
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                  blank=True, null=True,
                                  help_text="User who created the order")
    
    class Meta:
        db_table = 'orders'
        ordering = ['-order_date', '-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [
            models.Index(fields=['order_type', 'status']),
            models.Index(fields=['marketplace', 'order_date']),
            models.Index(fields=['warehouse', 'order_date']),
            models.Index(fields=['order_date']),
            models.Index(fields=['external_order_id']),
        ]
    
    def __str__(self):
        return f"{self.order_id} - {self.get_order_type_display()} ({self.status})"
    
    @property
    def total_items(self):
        """Total number of different products in order"""
        return self.order_items.count()
    
    @property
    def total_quantity(self):
        """Total quantity of all items in order"""
        return sum(item.quantity for item in self.order_items.all())
    
    @property
    def is_complete(self):
        """Check if order is in a completed state"""
        return self.status in ['DELIVERED', 'CANCELLED', 'RETURNED']
    
    @property
    def days_since_order(self):
        """Days since order was placed"""
        from django.utils import timezone
        return (timezone.now().date() - self.order_date.date()).days
    
    def calculate_total(self):
        """Recalculate order total based on line items"""
        items_total = sum(item.line_total for item in self.order_items.all())
        self.total_amount = items_total + self.shipping_cost + self.tax_amount
        return self.total_amount


class OrderItem(models.Model):
    """Individual line items within orders"""
    
    # Relationships
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                             related_name='order_items',
                             help_text="Parent order")
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                               related_name='order_items',
                               help_text="Product being ordered")
    
    # Quantity and pricing
    quantity = models.PositiveIntegerField(
        help_text="Quantity ordered")
    
    unit_price = models.DecimalField(max_digits=10, decimal_places=2,
                                    help_text="Price per unit")
    
    line_total = models.DecimalField(max_digits=10, decimal_places=2,
                                    help_text="Total for this line (quantity × unit_price)")
    
    # Status tracking per line item
    item_status = models.CharField(max_length=20, 
                                  choices=Order.ORDER_STATUS_CHOICES,
                                  default='PENDING',
                                  help_text="Status of this specific item")
    
    # Special handling
    is_combo_item = models.BooleanField(default=False,
                                       help_text="True if this item is part of a combo")
    
    parent_combo_sku = models.CharField(max_length=100, blank=True, null=True,
                                       help_text="Original combo SKU if this is a split item")
    
    # Fulfillment details
    picked_quantity = models.PositiveIntegerField(default=0,
                                                 help_text="Quantity actually picked")
    
    shipped_quantity = models.PositiveIntegerField(default=0,
                                                  help_text="Quantity shipped")
    
    # Notes
    item_notes = models.TextField(blank=True, null=True,
                                 help_text="Notes specific to this line item")
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'order_items'
        unique_together = ['order', 'product']  # One line per product per order
        ordering = ['order', 'product__msku']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
            models.Index(fields=['is_combo_item']),
            models.Index(fields=['parent_combo_sku']),
        ]
    
    def __str__(self):
        return f"{self.order.order_id} - {self.product.msku} (×{self.quantity})"
    
    @property
    def remaining_quantity(self):
        """Quantity not yet shipped"""
        if self.quantity is None or self.shipped_quantity is None:
            return 0
        return self.quantity - self.shipped_quantity
    
    @property
    def fulfillment_percentage(self):
        """Percentage of item fulfilled"""
        if self.quantity and self.quantity > 0:
            return (self.shipped_quantity / self.quantity) * 100
        return 0
    
    def save(self, *args, **kwargs):
        # Auto-calculate line total
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class InventoryMovement(models.Model):
    """Audit trail for all inventory movements - critical for tracking stock changes"""
    
    MOVEMENT_TYPE_CHOICES = [
        ('INBOUND', 'Stock In (Purchase/Restock)'),
        ('OUTBOUND', 'Stock Out (Sale/Fulfillment)'),
        ('TRANSFER_IN', 'Transfer In (From Another Warehouse)'),
        ('TRANSFER_OUT', 'Transfer Out (To Another Warehouse)'),
        ('ADJUSTMENT_POSITIVE', 'Positive Adjustment (Count Correction)'),
        ('ADJUSTMENT_NEGATIVE', 'Negative Adjustment (Count Correction)'),
        ('RETURN_IN', 'Return In (Customer Return)'),
        ('RETURN_OUT', 'Return Out (Supplier Return)'),
        ('DAMAGE', 'Damage/Loss'),
        ('COMBO_SPLIT', 'Combo Split (Combo → Individual Items)'),
        ('COMBO_COMBINE', 'Combo Combine (Individual Items → Combo)'),
    ]
    
    # Unique movement identifier
    movement_id = models.CharField(max_length=100, unique=True, primary_key=True,
                                  help_text="Unique movement tracking ID")
    
    # Core movement data
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPE_CHOICES,
                                    help_text="Type of inventory movement")
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                               related_name='inventory_movements',
                               help_text="Product being moved")
    
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE,
                                 related_name='inventory_movements',
                                 help_text="Warehouse where movement occurred")
    
    # Quantity and stock levels
    quantity = models.IntegerField(help_text="Quantity moved (positive or negative)")
    
    stock_before = models.IntegerField(help_text="Stock level before movement")
    stock_after = models.IntegerField(help_text="Stock level after movement")
    
    # References to source transactions
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, 
                             blank=True, null=True,
                             related_name='inventory_movements',
                             help_text="Related order (if applicable)")
    
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL,
                                  blank=True, null=True,
                                  related_name='inventory_movements',
                                  help_text="Related order item (if applicable)")
    
    # Transfer details (for warehouse transfers)
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL,
                                             blank=True, null=True,
                                             related_name='incoming_transfers',
                                             help_text="Destination warehouse for transfers")
    
    # Cost tracking
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2,
                                   blank=True, null=True,
                                   help_text="Cost per unit for this movement")
    
    total_cost = models.DecimalField(max_digits=12, decimal_places=2,
                                    blank=True, null=True,
                                    help_text="Total cost for this movement")
    
    # Movement metadata
    movement_date = models.DateTimeField(default=timezone.now,
        help_text="When the movement occurred")
    
    reference_number = models.CharField(max_length=100, blank=True, null=True,
                                       help_text="External reference (invoice, receipt, etc.)")
    
    reason = models.CharField(max_length=255, blank=True, null=True,
                             help_text="Reason for the movement")
    
    notes = models.TextField(blank=True, null=True,
                            help_text="Additional notes about the movement")
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                  blank=True, null=True,
                                  help_text="User who recorded the movement")
    
    class Meta:
        db_table = 'inventory_movements'
        ordering = ['-movement_date', '-created_at']
        verbose_name = 'Inventory Movement'
        verbose_name_plural = 'Inventory Movements'
        indexes = [
            models.Index(fields=['product', 'warehouse', 'movement_date']),
            models.Index(fields=['movement_type', 'movement_date']),
            models.Index(fields=['order']),
            models.Index(fields=['movement_date']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        direction = "+" if self.quantity > 0 else ""
        return f"{self.movement_id}: {self.product.msku} @ {self.warehouse.code} ({direction}{self.quantity})"
    
    @property
    def is_inbound(self):
        """Check if this is an inbound movement (increases stock)"""
        return self.quantity > 0
    
    @property
    def is_outbound(self):
        """Check if this is an outbound movement (decreases stock)"""
        return self.quantity < 0
    
    @property
    def absolute_quantity(self):
        """Get absolute quantity value"""
        return abs(self.quantity)
    
    def clean(self):
        """Validate the movement data"""
        from django.core.exceptions import ValidationError
        
        # Validate stock calculation
        expected_after = self.stock_before + self.quantity
        if self.stock_after != expected_after:
            raise ValidationError(
                f"Stock calculation error: {self.stock_before} + {self.quantity} ≠ {self.stock_after}"
            )
        
        # Validate stock cannot go negative (unless it's an adjustment)
        if self.stock_after < 0 and not self.movement_type.startswith('ADJUSTMENT'):
            raise ValidationError(
                f"Stock cannot go negative: {self.stock_after}"
            )
    
    def save(self, *args, **kwargs):
        # Generate movement ID if not provided
        if not self.movement_id:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.movement_id = f"MOV_{timestamp}_{self.product.msku}_{self.warehouse.code}"
        
        # Calculate total cost if unit cost provided
        if self.unit_cost:
            self.total_cost = abs(self.quantity) * self.unit_cost
        
        # Run validation
        self.clean()
        super().save(*args, **kwargs)


# =============================================================================
# Step 3B: Combo Product Models
# =============================================================================

class ComboProduct(models.Model):
    """Combo SKU definitions - handles your 375 combo products"""
    
    # Combo identifier (this would be a marketplace SKU that's actually a combo)
    combo_sku = models.CharField(max_length=100, unique=True, primary_key=True,
                                help_text="Combo SKU identifier")
    
    combo_name = models.CharField(max_length=255,
                                 help_text="Display name for the combo")
    
    # Link to marketplace where this combo is sold
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE,
                                   related_name='combo_products',
                                   help_text="Primary marketplace for this combo")
    
    # Business data
    combo_price = models.DecimalField(max_digits=10, decimal_places=2,
                                     help_text="Selling price of complete combo")
    
    # Status and configuration
    is_active = models.BooleanField(default=True)
    is_auto_split = models.BooleanField(default=True,
                                       help_text="Auto-split orders into individual items")
    
    # Description and marketing
    description = models.TextField(blank=True, null=True,
                                  help_text="Combo description for customers")
    combo_image_url = models.URLField(blank=True, null=True,
                                     help_text="Main image for the combo")
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'combo_products'
        ordering = ['combo_sku']
        verbose_name = 'Combo Product'
        verbose_name_plural = 'Combo Products'
        indexes = [
            models.Index(fields=['marketplace', 'is_active']),
            models.Index(fields=['combo_sku']),
        ]
    
    def __str__(self):
        return f"{self.combo_sku} - {self.combo_name}"
    
    @property
    def total_items(self):
        """Total number of different products in this combo"""
        return self.combo_items.count()
    
    @property
    def total_quantity(self):
        """Total quantity of all items in this combo"""
        return sum(item.quantity for item in self.combo_items.all())
    
    @property
    def calculated_cost(self):
        """Calculate total cost based on individual item prices"""
        # This would calculate based on individual product costs
        # For now, return 0 if no pricing data available
        return sum(
            item.quantity * (item.product.cost_price or 0) 
            for item in self.combo_items.all()
        )
    
    @property
    def profit_margin(self):
        """Calculate profit margin for the combo"""
        cost = self.calculated_cost
        if cost > 0:
            return ((self.combo_price - cost) / self.combo_price) * 100
        return 0
    
    def can_fulfill(self, warehouse_code=None):
        """Check if combo can be fulfilled from available inventory"""
        for item in self.combo_items.all():
            if warehouse_code:
                # Check specific warehouse
                try:
                    inventory = item.product.inventory_records.get(warehouse__code=warehouse_code)
                    if inventory.available_stock < item.quantity:
                        return False
                except Inventory.DoesNotExist:
                    return False
            else:
                # Check total stock across all warehouses
                if item.product.total_stock < item.quantity:
                    return False
        return True


class ComboProductItem(models.Model):
    """Individual items within combo products - junction table with quantities"""
    
    # Links combo to individual products
    combo_product = models.ForeignKey(ComboProduct, on_delete=models.CASCADE,
                                     related_name='combo_items',
                                     help_text="Parent combo product")
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                               related_name='combo_memberships',
                               help_text="Individual product in the combo")
    
    # Quantity configuration
    quantity = models.PositiveIntegerField(default=1,
                                          help_text="Quantity of this product in the combo")
    
    # Order and display
    sort_order = models.PositiveIntegerField(default=0,
                                            help_text="Display order within combo")
    
    # Optional item-specific configuration
    is_required = models.BooleanField(default=True,
                                     help_text="Is this item required in the combo")
    item_note = models.CharField(max_length=255, blank=True, null=True,
                                help_text="Special notes for this item")
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'combo_product_items'
        unique_together = ['combo_product', 'product']  # Each product appears once per combo
        ordering = ['sort_order', 'product__msku']
        verbose_name = 'Combo Product Item'
        verbose_name_plural = 'Combo Product Items'
        indexes = [
            models.Index(fields=['combo_product']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"{self.combo_product.combo_sku} → {self.product.msku} (×{self.quantity})"
    
    @property
    def item_total_value(self):
        """Calculate total value of this item in the combo"""
        return self.quantity * (self.product.cost_price or 0)
    
    @property
    def available_stock(self):
        """Get available stock for this product"""
        return self.product.total_stock
    
    @property
    def stock_coverage(self):
        """How many combos can be made with current stock of this item"""
        if self.quantity > 0:
            return self.available_stock // self.quantity
        return 0
    
    def clean(self):
        """Validate the combo item"""
        from django.core.exceptions import ValidationError
        
        # Ensure quantity is positive
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        
        # Ensure product is active
        if not self.product.is_active:
            raise ValidationError(f"Cannot add inactive product to combo: {self.product.msku}")
        
        # Ensure combo is active
        if not self.combo_product.is_active:
            raise ValidationError(f"Cannot add items to inactive combo: {self.combo_product.combo_sku}")
    
    def save(self, *args, **kwargs):
        # Run validation before saving
        self.clean()
        super().save(*args, **kwargs)