from django.contrib import admin, messages
from django.utils import timezone

from inventory.services import InsufficientStock
from orders.models import Order, OrderItem, OrderStatusHistory, Payment
from orders.services import DuplicateGCashReference, PaymentVerificationRequired, set_order_status


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "variant",
        "product_name",
        "color_name",
        "size",
        "capacity",
        "sku",
        "unit_price",
        "quantity",
        "customization_notes",
    )

    def has_add_permission(self, request, obj=None):
        return False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("from_status", "to_status", "changed_by", "note", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = ("method", "gcash_reference", "screenshot", "amount", "is_verified", "verified_by", "verified_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at", "payment__method")
    search_fields = ("number", "recipient_name", "phone", "user__email")
    readonly_fields = ("number", "user", "subtotal", "total", "created_at", "updated_at")
    inlines = [OrderItemInline, PaymentInline, OrderStatusHistoryInline]

    def save_model(self, request, obj, form, change):
        if not change:
            super().save_model(request, obj, form, change)
            return
        previous = Order.objects.get(pk=obj.pk)
        new_status = obj.status
        obj.status = previous.status
        super().save_model(request, obj, form, change)
        if previous.status != new_status:
            try:
                set_order_status(obj, new_status, request.user, note="Updated in Django admin")
            except (InsufficientStock, PaymentVerificationRequired, DuplicateGCashReference) as exc:
                self.message_user(request, str(exc), level=messages.ERROR)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "amount", "is_verified", "gcash_reference", "created_at")
    list_filter = ("method", "is_verified")
    search_fields = ("order__number", "gcash_reference")
    readonly_fields = ("order", "method", "amount", "created_at")

    def save_model(self, request, obj, form, change):
        if obj.is_verified and obj.order.status == Order.CANCELLED:
            obj.is_verified = False
            self.message_user(request, "Cancelled orders cannot be marked verified.", level=messages.ERROR)
        elif obj.is_verified and not obj.verified_at:
            obj.verified_by = obj.verified_by or request.user
            obj.verified_at = timezone.now()
        super().save_model(request, obj, form, change)
