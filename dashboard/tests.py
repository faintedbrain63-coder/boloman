from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from dashboard.forms import CategoryForm, ImageFormSet, ProductForm, ProductImageForm, VariantForm
from inventory.models import ProductVariant, StockMovement
from inventory.services import move_stock
from orders.models import Order
from orders.services import place_order, set_order_status
from store.models import Category, Product


class SalesAndInventoryTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Mugs", code="MUG", variant_type=Category.DRINKWARE)
        self.product = Product.objects.create(
            category=self.category,
            name="Photo Mug",
            description="A mug.",
            base_price=Decimal("199.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color_name="White",
            color_hex="#ffffff",
            capacity="11oz",
            sku="MUG-WHT-11OZ",
            quantity_on_hand=0,
            reorder_level=5,
            cost_price=Decimal("80.00"),
        )
        move_stock(variant=self.variant, quantity=10, movement_type=StockMovement.STOCK_IN, notes="Opening")
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff", email="staff@boloman.ph", password="pass12345", is_staff=True
        )
        self.customer = User.objects.create_user(username="ana", email="ana@example.com", password="pass12345")
        self.client.force_login(self.staff)

    def _order(self, method="COD", quantity=2):
        return place_order(
            user=self.customer,
            variant=self.variant,
            quantity=quantity,
            customization_notes="Front print",
            recipient_name="Ana Cruz",
            phone="09170000000",
            address="123 Print Street",
            payment_method=method,
            gcash_reference="REF123" if method == "GCASH" else "",
        )

    def test_revenue_keeps_centavos_and_ignores_cancelled_orders(self):
        order = self._order()
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.context["sales_total"], Decimal("398.00"))
        self.assertEqual(len(response.context["chart_series"]), 30)
        self.assertEqual(response.context["chart_series"][-1], 398.0)
        self.assertEqual(response.context["top_products"][0]["revenue"], Decimal("398.00"))
        self.assertEqual(response.context["top_categories"][0]["name"], "Mugs")
        self.assertEqual(response.context["top_categories"][0]["revenue"], Decimal("398.00"))

        self.variant.delete()
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.context["top_categories"][0]["name"], "Mugs")
        self.assertEqual(response.context["top_categories"][0]["revenue"], Decimal("398.00"))

        set_order_status(order, Order.CANCELLED, self.staff, "Cancelled")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.context["sales_total"], Decimal("0.00"))
        self.assertEqual(sum(response.context["chart_series"]), 0)
        self.assertEqual(response.context["top_categories"], [])

    def test_cancelled_gcash_is_not_pending_and_cannot_be_verified(self):
        order = self._order(method="GCASH")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.context["pending_gcash"], 1)
        listed = self.client.get(reverse("dashboard:orders") + "?method=GCASH&verified=pending")
        self.assertContains(listed, order.number)

        set_order_status(order, Order.CANCELLED, self.staff, "Cancelled")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.context["pending_gcash"], 0)
        self.assertEqual(self.client.get(reverse("dashboard:orders")).context["summary"]["unverified_gcash"], 0)
        listed = self.client.get(reverse("dashboard:orders") + "?method=GCASH&verified=pending")
        self.assertNotContains(listed, order.number)

        self.client.post(reverse("dashboard:order_detail", args=[order.number]), {"action": "verify"})
        order.payment.refresh_from_db()
        self.assertFalse(order.payment.is_verified)

    def test_stock_alerts_skip_hidden_products_and_inventory_cards_follow_filters(self):
        self.variant.quantity_on_hand = 2
        self.variant.reorder_level = 5
        self.variant.save(update_fields=["quantity_on_hand", "reorder_level"])
        hidden = Product.objects.create(
            category=self.category, name="Hidden Mug", description="Hidden.", base_price=Decimal("150.00"), is_active=False
        )
        ProductVariant.objects.create(
            product=hidden,
            color_name="Black",
            color_hex="#111111",
            capacity="15oz",
            sku="MUG-BLK-15OZ",
            quantity_on_hand=0,
            reorder_level=5,
        )
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual([item.sku for item in response.context["low_stock"]], ["MUG-WHT-11OZ"])
        self.assertEqual(list(response.context["out_of_stock"]), [])

        inventory = self.client.get(reverse("dashboard:inventory") + "?status=out")
        self.assertEqual(inventory.context["summary"]["skus"], 1)
        self.assertEqual(inventory.context["summary"]["units"], 0)
        self.assertEqual(inventory.context["summary"]["out"], 1)
        self.assertEqual(inventory.context["summary"]["low"], 0)

        products = self.client.get(reverse("dashboard:products"))
        row = next(item for item in products.context["page"].object_list if item.pk == self.product.pk)
        self.assertEqual(row.sku_count, 1)
        self.assertEqual(row.units_on_hand, 2)

    def test_product_and_category_forms_reject_bad_values(self):
        product = ProductForm(
            data={
                "category": self.category.pk,
                "name": "New Mug",
                "slug": self.product.slug,
                "description": "A mug.",
                "base_price": "-10.00",
            }
        )
        self.assertNotIn("short_description", product.fields)
        self.assertFalse(product.is_valid())
        self.assertIn("base_price", product.errors)
        self.assertIn("cost_price", product.errors)
        self.assertIn("slug", product.errors)

        duplicate = CategoryForm(
            data={
                "name": "Other Mugs",
                "slug": self.category.slug,
                "code": "mug",
                "icon": "bi-tag",
                "variant_type": Category.DRINKWARE,
                "display_order": 1,
            }
        )
        self.assertFalse(duplicate.is_valid())
        self.assertIn("slug", duplicate.errors)
        self.assertIn("code", duplicate.errors)

        locked = CategoryForm(
            data={
                "name": "Mugs",
                "slug": self.category.slug,
                "code": "CUP",
                "icon": "bi-tag",
                "variant_type": Category.SHIRT,
                "display_order": 0,
                "is_active": "on",
            },
            instance=self.category,
        )
        self.assertFalse(locked.is_valid())
        self.assertIn("code", locked.errors)
        self.assertIn("variant_type", locked.errors)

        twin = Category(name="Mugs", code="CUP2")
        twin.save()
        self.assertNotEqual(twin.slug, self.category.slug)

        self.assertNotIn("sort_order", ProductImageForm().fields)
        image = ProductImageForm(data={"alt_text": "Front", "sort_order": "0", "is_primary": "on"})
        self.assertFalse(image.is_valid())
        self.assertIn("image", image.errors)

        blank = ImageFormSet(
            data={
                "images-TOTAL_FORMS": "1",
                "images-INITIAL_FORMS": "0",
                "images-MIN_NUM_FORMS": "0",
                "images-MAX_NUM_FORMS": "1000",
                "images-0-alt_text": "",
                "images-0-sort_order": "0",
            },
            instance=self.product,
        )
        self.assertTrue(blank.is_valid())

        variant = VariantForm(
            data={
                "color_name": "white",
                "color_hex": "#ffffff",
                "capacity": "11oz",
                "cost_price": "-5",
                "reorder_level": 5,
                "is_active": "on",
            },
            product=self.product,
        )
        self.assertFalse(variant.is_valid())
        self.assertIn("color_name", variant.errors)
        self.assertIn("cost_price", variant.errors)

    def test_blank_variant_prices_use_the_product_cost_and_selling_price(self):
        self.product.cost_price = Decimal("80.00")
        self.product.save(update_fields=["cost_price"])
        self.variant.cost_price = None
        self.variant.selling_price = None
        self.variant.quantity_on_hand = 4
        self.variant.save(update_fields=["cost_price", "selling_price", "quantity_on_hand"])

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.unit_cost, Decimal("80.00"))
        self.assertEqual(self.variant.price, Decimal("199.00"))

        inventory = self.client.get(reverse("dashboard:inventory"))
        self.assertEqual(inventory.context["summary"]["cost_value"], Decimal("320.00"))
        self.assertEqual(inventory.context["summary"]["retail_value"], Decimal("796.00"))

        products = self.client.get(reverse("dashboard:products"))
        row = next(item for item in products.context["page"].object_list if item.pk == self.product.pk)
        self.assertEqual(row.cost_price, Decimal("80.00"))
        self.assertEqual(row.base_price, Decimal("199.00"))
        self.assertEqual(row.stock_cost, Decimal("320.00"))

    def test_staff_can_upload_the_gcash_qr_shown_at_checkout(self):
        from core.models import SiteSettings

        settings_row = SiteSettings.load()
        payload = {
            "business_name": "Boloman Prints",
            "tagline": "Custom shirts",
            "phone": "09171234567",
            "email": "hello@boloman.ph",
            "address": "123 Print Street",
            "map_embed_url": "",
            "gcash_number": "09171234567",
            "gcash_account_name": "Boloman Prints",
        }
        response = self.client.post(
            reverse("dashboard:settings"),
            {**payload, "gcash_qr": _png("gcash-qr.png")},
        )
        self.assertRedirects(response, reverse("dashboard:settings"))
        settings_row.refresh_from_db()
        first_name = settings_row.gcash_qr.name
        self.assertTrue(first_name.endswith(".png"))

        page = self.client.get(reverse("dashboard:settings"))
        self.assertContains(page, settings_row.gcash_qr.url)
        checkout = self.client.get(reverse("orders:checkout"), {"variant": self.variant.pk})
        self.assertContains(checkout, settings_row.gcash_qr.url)
        self.assertContains(checkout, "scan this QR")

        self.client.post(reverse("dashboard:settings"), {**payload, "gcash_qr": _png("gcash-qr-new.png")})
        settings_row.refresh_from_db()
        self.assertNotEqual(settings_row.gcash_qr.name, first_name)
        self.assertFalse(default_storage.exists(first_name))

        rejected = self.client.post(
            reverse("dashboard:settings"),
            {**payload, "gcash_qr": SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertContains(rejected, "JPEG, PNG, or WebP")


def _png(name):
    buffer = BytesIO()
    Image.new("RGB", (12, 12), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")
