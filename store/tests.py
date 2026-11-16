from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from inventory.models import ProductVariant
from store.models import Category, Product
from store.views import _catalog


class CatalogPriceTests(TestCase):
    def test_sort_price_matches_the_lowest_active_price(self):
        category = Category.objects.create(name="Shirts", code="CTN", variant_type=Category.SHIRT)
        cheap = Product.objects.create(
            category=category, name="Cheap Tee", description="A tee.", base_price=Decimal("199.00")
        )
        dear = Product.objects.create(
            category=category, name="Dear Tee", description="A tee.", base_price=Decimal("80.00")
        )
        ProductVariant.objects.create(
            product=cheap, color_name="Black", color_hex="#111111", size="M", sku="CTN-BLK-M", selling_price=Decimal("50.00")
        )
        ProductVariant.objects.create(
            product=cheap,
            color_name="White",
            color_hex="#ffffff",
            size="M",
            sku="CTN-WHT-M",
            selling_price=None,
        )
        ProductVariant.objects.create(
            product=dear, color_name="Navy", color_hex="#001f3f", size="L", sku="CTN-NVY-L"
        )

        ordered = list(_catalog().order_by("sort_price", "name"))
        self.assertEqual([product.name for product in ordered], ["Cheap Tee", "Dear Tee"])
        for product in ordered:
            self.assertEqual(product.sort_price, product.from_price)

        named = self.client.get(reverse("store:product_list"), {"sort": "name"})
        self.assertEqual([item.name for item in named.context["page"].object_list], ["Cheap Tee", "Dear Tee"])
        oldest = self.client.get(reverse("store:product_list"), {"sort": "oldest"})
        self.assertEqual([item.name for item in oldest.context["page"].object_list], ["Cheap Tee", "Dear Tee"])
