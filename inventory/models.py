from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from inventory.constants import size_label
from store.models import Product


class Supplier(models.Model):
    name = models.CharField(max_length=120)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    IN_STOCK = "in"
    LOW_STOCK = "low"
    OUT_OF_STOCK = "out"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color_name = models.CharField(max_length=40)
    color_hex = models.CharField(max_length=7, default="#111827")
    size = models.CharField(max_length=10, blank=True, default="")
    capacity = models.CharField(max_length=10, blank=True, default="")
    sku = models.CharField(max_length=40, unique=True)
    quantity_on_hand = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    cost_price = models.DecimalField(
        "Cost price",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Leave blank to use the product cost price.",
    )
    selling_price = models.DecimalField(
        "Selling price",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Leave blank to use the product selling price.",
    )
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name="variants")
    location = models.CharField("Location / bin", max_length=40, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["product__name", "color_name", "size", "capacity"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "color_name", "size", "capacity"],
                name="unique_variant_option",
            ),
            models.CheckConstraint(condition=Q(quantity_on_hand__gte=0), name="variant_qty_nonnegative"),
        ]

    def __str__(self):
        return f"{self.sku} · {self.product.name} · {self.option_label}"

    @property
    def unit_cost(self):
        if self.cost_price is not None:
            return self.cost_price
        return self.product.cost_price

    @property
    def price(self):
        if self.selling_price is not None:
            return self.selling_price
        return self.product.base_price

    @property
    def option_label(self):
        bits = [self.color_name]
        if self.size:
            bits.append(size_label(self.size))
        if self.capacity:
            bits.append(self.capacity)
        return " / ".join(bits)

    @property
    def stock_status(self):
        if self.quantity_on_hand <= 0:
            return self.OUT_OF_STOCK
        if self.quantity_on_hand <= self.reorder_level:
            return self.LOW_STOCK
        return self.IN_STOCK

    @property
    def stock_label(self):
        return {
            self.IN_STOCK: "In Stock",
            self.LOW_STOCK: "Low Stock",
            self.OUT_OF_STOCK: "Out of Stock",
        }[self.stock_status]


class StockMovement(models.Model):
    STOCK_IN = "STOCK_IN"
    SALE = "SALE"
    RETURN = "RETURN"
    ADJUSTMENT = "ADJUSTMENT"
    CANCELLATION = "CANCELLATION"
    TYPES = [
        (STOCK_IN, "Stock In"),
        (SALE, "Sale"),
        (RETURN, "Return"),
        (ADJUSTMENT, "Adjustment"),
        (CANCELLATION, "Cancellation"),
    ]

    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=TYPES)
    quantity = models.IntegerField(help_text="Positive adds stock. Negative removes stock.")
    balance_before = models.PositiveIntegerField()
    balance_after = models.PositiveIntegerField()
    order = models.ForeignKey(
        "orders.Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity:+d} {self.variant.sku}"
