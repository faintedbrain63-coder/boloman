from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.validators import validate_image_file


class Category(models.Model):
    SHIRT = "shirt"
    CAP = "cap"
    DRINKWARE = "drinkware"
    VARIANT_TYPES = [
        (SHIRT, "Shirt (sizes XS–3XL)"),
        (CAP, "Cap (adjustable / fitted)"),
        (DRINKWARE, "Drinkware (capacity)"),
    ]

    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True, blank=True)
    code = models.CharField(max_length=8, unique=True, help_text="Short code used in SKUs, e.g. CTN.")
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, default="bi-tag", help_text="Bootstrap Icons class.")
    variant_type = models.CharField(max_length=20, choices=VARIANT_TYPES, default=SHIRT)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        if not self.slug:
            base = slugify(self.name)[:50] or "category"
            slug = base
            number = 2
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{number}"
                number += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product_list") + f"?category={self.slug}"

    @property
    def placeholder(self):
        return {
            "MUG": "img/mug.svg",
            "TUM": "img/tumbler.svg",
            "CAP": "img/cap.svg",
        }.get(self.code, "img/shirt.svg")


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.CharField(max_length=220, blank=True)
    description = models.TextField()
    cost_price = models.DecimalField(
        "Cost price",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="What you pay when you buy this product.",
    )
    base_price = models.DecimalField(
        "Selling price",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="What the customer pays when you sell this product.",
    )
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:50] or "product"
            slug = base
            number = 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{number}"
                number += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product_detail", kwargs={"slug": self.slug})

    @property
    def primary_image(self):
        images = list(self.images.all())
        for image in images:
            if image.is_primary:
                return image
        return images[0] if images else None

    @property
    def from_price(self):
        prices = [variant.price for variant in self.variants.all() if variant.is_active]
        if prices:
            return min(prices)
        return self.base_price

    @property
    def color_swatches(self):
        seen = set()
        swatches = []
        for variant in self.variants.all():
            if not variant.is_active or variant.color_name in seen:
                continue
            seen.add(variant.color_name)
            swatches.append({"name": variant.color_name, "hex": variant.color_hex})
        return swatches

    @property
    def total_stock(self):
        return sum(variant.quantity_on_hand for variant in self.variants.all() if variant.is_active)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/%Y/%m/", validators=[validate_image_file])
    alt_text = models.CharField(max_length=160, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.alt_text or f"Image for {self.product.name}"

    def delete(self, *args, **kwargs):
        name = self.image.name if self.image else ""
        storage = self.image.storage if self.image else None
        result = super().delete(*args, **kwargs)
        if name and storage and storage.exists(name):
            storage.delete(name)
        return result
