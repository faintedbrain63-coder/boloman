from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.urls import reverse

from core.validators import validate_image_file
from inventory.models import ProductVariant


class OrderSequence(models.Model):
    date = models.DateField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.date} #{self.last_number}"


class Order(models.Model):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    FOR_DELIVERY = "FOR_DELIVERY"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (NEW, "New Order"),
        (PROCESSING, "On Process"),
        (FOR_DELIVERY, "For Deliver"),
        (SHIPPED, "Shipped"),
        (COMPLETED, "Order Completed"),
        (CANCELLED, "Cancelled"),
    ]
    FLOW = [NEW, PROCESSING, FOR_DELIVERY, SHIPPED, COMPLETED]

    number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NEW, db_index=True)
    recipient_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40)
    address = models.TextField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    def get_absolute_url(self):
        return reverse("orders:detail", kwargs={"number": self.number})

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def tracker_steps(self):
        if self.status == self.CANCELLED:
            return []
        current = self.FLOW.index(self.status)
        steps = []
        for index, code in enumerate(self.FLOW):
            steps.append(
                {
                    "code": code,
                    "label": dict(self.STATUS_CHOICES)[code],
                    "done": index < current,
                    "current": index == current,
                }
            )
        return steps


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=160)
    category_name = models.CharField(max_length=80, blank=True, default="")
    color_name = models.CharField(max_length=40)
    color_hex = models.CharField(max_length=7, blank=True)
    size = models.CharField(max_length=10, blank=True)
    capacity = models.CharField(max_length=10, blank=True)
    sku = models.CharField(max_length=40)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    customization_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def option_label(self):
        bits = [self.color_name]
        if self.size:
            bits.append(self.size)
        if self.capacity:
            bits.append(self.capacity)
        return " / ".join(bit for bit in bits if bit)


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_status_changes",
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name_plural = "order status history"

    def __str__(self):
        return f"{self.order.number}: {self.from_status or '—'} → {self.to_status}"


class Payment(models.Model):
    COD = "COD"
    GCASH = "GCASH"
    METHODS = [
        (COD, "Cash (Cash on Delivery)"),
        (GCASH, "GCash"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=10, choices=METHODS)
    gcash_reference = models.CharField(max_length=80, blank=True)
    screenshot = models.ImageField(
        upload_to="payments/%Y/%m/",
        blank=True,
        validators=[validate_image_file],
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_payments",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_method_display()} · {self.order.number}"

    def delete(self, *args, **kwargs):
        screenshot_name = self.screenshot.name if self.screenshot else ""
        result = super().delete(*args, **kwargs)
        if screenshot_name:
            transaction.on_commit(lambda: default_storage.exists(screenshot_name) and default_storage.delete(screenshot_name))
        return result
