# core/admin.py - Step 2: Basic Admin Interface

from django.contrib import admin
from .models import (Product, Warehouse, Inventory, Marketplace, SKUMapping, 
                     ComboProduct, ComboProductItem, Order, OrderItem, InventoryMovement)

# =============================================================================
# Product Admin
# =============================================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['msku', 'product_name', 'category', 'brand', 'cost_price', 'is_active', 'total_stock']
    list_filter = ['is_active', 'category', 'brand', 'created_at']
    search_fields = ['msku', 'product_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('msku', 'product_name', 'category', 'brand')
        }),
        ('Pricing', {
            'fields': ('cost_price',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_stock(self, obj):
        """Display total stock across all warehouses"""
        return obj.total_stock
    total_stock.short_description = 'Total Stock'


# =============================================================================
# Warehouse Admin  
# =============================================================================

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'location', 'is_active', 'total_products', 'total_stock_value']
    list_filter = ['is_active', 'location', 'created_at']
    search_fields = ['code', 'name', 'location']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Warehouse Information', {
            'fields': ('code', 'name', 'location')
        }),
        ('Contact Information', {
            'fields': ('address', 'contact_person', 'phone', 'email'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_products(self, obj):
        """Display number of products in warehouse"""
        return obj.total_products
    total_products.short_description = 'Products'
    
    def total_stock_value(self, obj):
        """Display total stock units"""
        return f"{obj.total_stock_value:,}"
    total_stock_value.short_description = 'Total Stock'


# =============================================================================
# Inventory Admin
# =============================================================================

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'current_stock', 'available_stock', 
                   'buffer_stock', 'stock_status', 'is_low_stock']
    list_filter = ['warehouse', 'last_updated']
    search_fields = ['product__msku', 'product__product_name', 'warehouse__code']
    readonly_fields = ['last_updated', 'available_stock', 'stock_status']
    
    fieldsets = (
        ('Product & Location', {
            'fields': ('product', 'warehouse')
        }),
        ('Stock Levels', {
            'fields': ('current_stock', 'buffer_stock', 'opening_stock')
        }),
        ('Business Rules', {
            'fields': ('reorder_level', 'max_stock_level'),
            'classes': ('collapse',)
        }),
        ('Status & Tracking', {
            'fields': ('available_stock', 'stock_status', 'last_updated', 'last_stock_count_date'),
            'classes': ('collapse',)
        }),
    )
    
    def available_stock(self, obj):
        """Display available stock"""
        return obj.available_stock
    available_stock.short_description = 'Available'
    
    def stock_status(self, obj):
        """Display stock status with color coding"""
        status = obj.stock_status
        if status == "Out of Stock":
            return f'🔴 {status}'
        elif status == "Low Stock":
            return f'🟡 {status}'
        elif status == "Overstocked":
            return f'🟠 {status}'
        else:
            return f'🟢 {status}'
    stock_status.short_description = 'Status'
    
    def is_low_stock(self, obj):
        """Display stock level indicator"""
        return False if obj.is_low_stock else True
    is_low_stock.short_description = 'Stock OK'
    is_low_stock.boolean = True


# =============================================================================
# Marketplace Admin  
# =============================================================================

@admin.register(Marketplace)
class MarketplaceAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'commission_rate', 'is_active', 'total_skus', 'active_skus']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Marketplace Information', {
            'fields': ('code', 'name', 'commission_rate')
        }),
        ('Configuration', {
            'fields': ('api_endpoint', 'api_key'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_skus(self, obj):
        """Display total SKU mappings"""
        return obj.total_skus
    total_skus.short_description = 'Total SKUs'
    
    def active_skus(self, obj):
        """Display active SKU mappings"""
        return obj.active_skus
    active_skus.short_description = 'Active SKUs'


# =============================================================================
# SKU Mapping Admin
# =============================================================================

@admin.register(SKUMapping)
class SKUMappingAdmin(admin.ModelAdmin):
    list_display = ['sku', 'product', 'marketplace', 'status', 'status_2', 'has_image', 'updated_at']
    list_filter = ['marketplace', 'status', 'status_2', 'updated_at']
    search_fields = ['sku', 'product__msku', 'product__product_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Core Mapping', {
            'fields': ('sku', 'product', 'marketplace')
        }),
        ('Marketplace Data', {
            'fields': ('marketplace_product_url', 'marketplace_price', 'image_url')
        }),
        ('Status', {
            'fields': ('status', 'status_2')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_image(self, obj):
        """Display if product has image"""
        return "📷" if obj.has_image else "❌"
    has_image.short_description = 'Image'
    
    # Optimize queries with select_related
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'marketplace')


# =============================================================================
# Combo Product Admin
# =============================================================================

class ComboProductItemInline(admin.TabularInline):
    """Inline editing of combo items within combo product admin"""
    model = ComboProductItem
    extra = 1
    fields = ['product', 'quantity', 'sort_order', 'is_required', 'item_note']
    autocomplete_fields = ['product']


@admin.register(ComboProduct)
class ComboProductAdmin(admin.ModelAdmin):
    list_display = ['combo_sku', 'combo_name', 'marketplace', 'combo_price', 
                   'total_items', 'total_quantity', 'profit_margin', 'is_active']
    list_filter = ['marketplace', 'is_active', 'is_auto_split', 'created_at']
    search_fields = ['combo_sku', 'combo_name']
    readonly_fields = ['created_at', 'updated_at', 'calculated_cost', 'profit_margin']
    inlines = [ComboProductItemInline]
    
    fieldsets = (
        ('Combo Information', {
            'fields': ('combo_sku', 'combo_name', 'marketplace')
        }),
        ('Pricing & Profitability', {
            'fields': ('combo_price', 'calculated_cost', 'profit_margin')
        }),
        ('Configuration', {
            'fields': ('is_auto_split', 'description', 'combo_image_url')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_items(self, obj):
        """Display number of different products"""
        return obj.total_items
    total_items.short_description = 'Items'
    
    def total_quantity(self, obj):
        """Display total quantity"""
        return obj.total_quantity
    total_quantity.short_description = 'Total Qty'
    
    def profit_margin(self, obj):
        """Display profit margin as percentage"""
        margin = obj.profit_margin
        if margin > 0:
            return f"{margin:.1f}%"
        return "N/A"
    profit_margin.short_description = 'Margin %'
    
    def calculated_cost(self, obj):
        """Display calculated cost"""
        return f"₹{obj.calculated_cost:.2f}"
    calculated_cost.short_description = 'Calculated Cost'


@admin.register(ComboProductItem)
class ComboProductItemAdmin(admin.ModelAdmin):
    list_display = ['combo_product', 'product', 'quantity', 'sort_order', 
                   'is_required', 'available_stock', 'stock_coverage']
    list_filter = ['is_required', 'combo_product__marketplace', 'created_at']
    search_fields = ['combo_product__combo_sku', 'product__msku', 'product__product_name']
    readonly_fields = ['created_at', 'updated_at', 'available_stock', 'stock_coverage']
    autocomplete_fields = ['combo_product', 'product']
    
    fieldsets = (
        ('Combo Relationship', {
            'fields': ('combo_product', 'product')
        }),
        ('Quantity & Order', {
            'fields': ('quantity', 'sort_order', 'is_required')
        }),
        ('Stock Information', {
            'fields': ('available_stock', 'stock_coverage'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('item_note',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def available_stock(self, obj):
        """Display available stock"""
        return f"{obj.available_stock:,}"
    available_stock.short_description = 'Stock'
    
    def stock_coverage(self, obj):
        """Display how many combos can be made"""
        coverage = obj.stock_coverage
        if coverage == 0:
            return "🔴 0"
        elif coverage < 10:
            return f"🟡 {coverage}"
        else:
            return f"🟢 {coverage}"
    stock_coverage.short_description = 'Combo Coverage'
    
    # Optimize queries
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('combo_product', 'product')


# =============================================================================
# Order Management Admin
# =============================================================================

class OrderItemInline(admin.TabularInline):
    """Inline editing of order items within order admin"""
    model = OrderItem
    extra = 1
    fields = ['product', 'quantity', 'unit_price', 'line_total', 'item_status', 
              'picked_quantity', 'shipped_quantity']
    readonly_fields = ['line_total']
    autocomplete_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'order_type', 'status', 'marketplace', 'warehouse', 
                   'order_date', 'total_amount', 'total_items', 'days_since_order']
    list_filter = ['order_type', 'status', 'marketplace', 'warehouse', 'order_date']
    search_fields = ['order_id', 'external_order_id', 'customer_email', 'tracking_number']
    readonly_fields = ['created_at', 'updated_at', 'total_items', 'total_quantity', 'days_since_order']
    autocomplete_fields = ['marketplace', 'warehouse', 'created_by']
    inlines = [OrderItemInline]
    date_hierarchy = 'order_date'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'order_type', 'status', 'order_date')
        }),
        ('Location & Channel', {
            'fields': ('warehouse', 'marketplace')
        }),
        ('Financial Information', {
            'fields': ('total_amount', 'shipping_cost', 'tax_amount')
        }),
        ('Delivery Information', {
            'fields': ('expected_delivery_date', 'actual_delivery_date', 'tracking_number', 'shipping_address')
        }),
        ('External References', {
            'fields': ('external_order_id', 'customer_email', 'customer_phone'),
            'classes': ('collapse',)
        }),
        ('Order Summary', {
            'fields': ('total_items', 'total_quantity', 'days_since_order'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def total_items(self, obj):
        """Display number of different products"""
        return obj.total_items
    total_items.short_description = 'Items'
    
    def days_since_order(self, obj):
        """Display days since order"""
        days = obj.days_since_order
        if days == 0:
            return "Today"
        elif days == 1:
            return "1 day"
        else:
            return f"{days} days"
    days_since_order.short_description = 'Age'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('marketplace', 'warehouse', 'created_by')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'unit_price', 'line_total', 
                   'item_status', 'fulfillment_percentage', 'is_combo_item']
    list_filter = ['item_status', 'is_combo_item', 'order__order_type', 'created_at']
    search_fields = ['order__order_id', 'product__msku', 'product__product_name', 'parent_combo_sku']
    readonly_fields = ['line_total', 'remaining_quantity', 'created_at', 'updated_at']  # Removed fulfillment_percentage from here
    autocomplete_fields = ['order', 'product']
    
    fieldsets = (
        ('Order Relationship', {
            'fields': ('order', 'product')
        }),
        ('Quantity & Pricing', {
            'fields': ('quantity', 'unit_price', 'line_total')
        }),
        ('Fulfillment Tracking', {
            'fields': ('item_status', 'picked_quantity', 'shipped_quantity', 'remaining_quantity')  # Removed fulfillment_percentage from here
        }),
        ('Combo Information', {
            'fields': ('is_combo_item', 'parent_combo_sku'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('item_notes',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def fulfillment_percentage(self, obj):
        """Display fulfillment percentage"""
        # Handle None values safely
        if not obj.quantity or obj.quantity == 0:
            return "N/A"
            
        percentage = obj.fulfillment_percentage
        if percentage == 100:
            return f"🟢 {percentage:.0f}%"
        elif percentage > 50:
            return f"🟡 {percentage:.0f}%"
        elif percentage > 0:
            return f"🟠 {percentage:.0f}%"
        else:
            return f"🔴 {percentage:.0f}%"
    fulfillment_percentage.short_description = 'Fulfilled'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'product')


# =============================================================================
# Inventory Movement Admin
# =============================================================================

@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ['movement_id', 'movement_type', 'product', 'warehouse', 'quantity', 
                   'stock_before', 'stock_after', 'movement_date', 'reference_number']
    list_filter = ['movement_type', 'warehouse', 'movement_date', 'created_at']
    search_fields = ['movement_id', 'product__msku', 'product__product_name', 
                    'reference_number', 'order__order_id']
    readonly_fields = ['created_at', 'absolute_quantity', 'is_inbound', 'is_outbound']
    autocomplete_fields = ['product', 'warehouse', 'order', 'order_item', 'destination_warehouse']
    date_hierarchy = 'movement_date'
    
    fieldsets = (
        ('Movement Information', {
            'fields': ('movement_id', 'movement_type', 'movement_date', 'reference_number')
        }),
        ('Product & Location', {
            'fields': ('product', 'warehouse', 'destination_warehouse')
        }),
        ('Quantity & Stock Levels', {
            'fields': ('quantity', 'absolute_quantity', 'stock_before', 'stock_after', 
                      'is_inbound', 'is_outbound')
        }),
        ('Order References', {
            'fields': ('order', 'order_item'),
            'classes': ('collapse',)
        }),
        ('Cost Information', {
            'fields': ('unit_cost', 'total_cost'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('reason', 'notes'),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def quantity(self, obj):
        """Display quantity with color coding"""
        if obj.quantity > 0:
            return f"🟢 +{obj.quantity}"
        else:
            return f"🔴 {obj.quantity}"
    quantity.short_description = 'Qty Change'
    
    def absolute_quantity(self, obj):
        """Display absolute quantity"""
        return obj.absolute_quantity
    absolute_quantity.short_description = 'Abs Qty'
    
    def is_inbound(self, obj):
        """Display if movement is inbound"""
        return obj.is_inbound
    is_inbound.short_description = 'Inbound'
    is_inbound.boolean = True
    
    def is_outbound(self, obj):
        """Display if movement is outbound"""
        return obj.is_outbound
    is_outbound.short_description = 'Outbound'
    is_outbound.boolean = True
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'warehouse', 'order', 'order_item', 'destination_warehouse', 'created_by'
        )