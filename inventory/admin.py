from django.contrib import admin

from inventory.models import ProductVariant, StockMovement, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "email")
    search_fields = ("name", "contact_person", "email")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "color_name", "size", "capacity", "quantity_on_hand", "reorder_level", "is_active")
    list_filter = ("product__category", "is_active", "color_name")
    search_fields = ("sku", "product__name", "color_name", "location")
    autocomplete_fields = ("product", "supplier")
    readonly_fields = ("quantity_on_hand",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "variant", "movement_type", "quantity", "balance_before", "balance_after", "user")
    list_filter = ("movement_type", "created_at")
    search_fields = ("variant__sku", "notes", "order__number")
    readonly_fields = (
        "variant",
        "movement_type",
        "quantity",
        "balance_before",
        "balance_after",
        "order",
        "user",
        "notes",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
