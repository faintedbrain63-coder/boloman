from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from core.models import SiteSettings
from inventory.models import ProductVariant, StockMovement
from inventory.services import InsufficientStock, move_stock
from orders.models import Order, Payment
from orders.services import (
    DuplicateGCashReference,
    PaymentVerificationRequired,
    next_order_number,
    place_order,
    set_order_status,
)
from store.models import Category, Product


def _receipt_png(name="receipt.png"):
    buf = BytesIO()
    Image.new("RGB", (16, 16), "white").save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class OrderFlowTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Mugs", code="MUG", variant_type=Category.DRINKWARE)
        product = Product.objects.create(
            category=category,
            name="Photo Mug",
            description="A mug.",
            base_price=Decimal("199.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            color_name="White",
            color_hex="#ffffff",
            capacity="11oz",
            sku="MUG-WHT-11OZ",
            quantity_on_hand=0,
            reorder_level=5,
            cost_price=Decimal("80.00"),
        )
        move_stock(variant=self.variant, quantity=4, movement_type=StockMovement.STOCK_IN, notes="Opening")
        self.user = get_user_model().objects.create_user(username="ana", email="ana@example.com", password="pass12345")

    def _order(self, quantity=2):
        return place_order(
            user=self.user,
            variant=self.variant,
            quantity=quantity,
            customization_notes="Print Ana on the front",
            recipient_name="Ana Cruz",
            phone="09170000000",
            address="123 Print Street, Quezon City",
            payment_method="COD",
        )

    def test_order_deducts_stock_and_numbers_are_unique(self):
        first = self._order()
        second = self._order(quantity=1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.quantity_on_hand, 1)
        self.assertNotEqual(first.number, second.number)
        self.assertTrue(first.number.startswith("ORD-"))
        item = first.items.get()
        self.assertEqual(item.customization_notes, "Print Ana on the front")
        self.assertEqual(item.category_name, "Mugs")
        self.assertEqual(first.subtotal, item.line_total)
        self.assertEqual(first.total, item.unit_price * item.quantity)
        self.assertEqual(first.payment.amount, first.total)
        self.assertEqual(first.status_history.get().to_status, Order.NEW)
        self.assertTrue(StockMovement.objects.filter(order=first, movement_type=StockMovement.SALE).exists())

    def test_cannot_oversell(self):
        with self.assertRaises(InsufficientStock):
            self._order(quantity=5)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.quantity_on_hand, 4)

    def test_cancel_restores_stock(self):
        order = self._order(quantity=3)
        set_order_status(order, Order.CANCELLED, self.user, note="Changed my mind")
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.quantity_on_hand, 4)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertEqual(order.status_history.count(), 2)

    def test_daily_sequence_increments(self):
        first = next_order_number()
        second = next_order_number()
        self.assertEqual(int(second[-4:]) - int(first[-4:]), 1)

    def test_checkout_cod_ignores_leftover_gcash_inputs_and_records_cash_flow(self):
        self.client.force_login(self.user)
        bad_file = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
        response = self.client.post(
            reverse("orders:checkout"),
            {
                "variant": self.variant.pk,
                "recipient_name": "Ana Cruz",
                "phone": "09171234567",
                "address_line": "123 Mabini Street",
                "city": "Quezon City",
                "province": "Metro Manila",
                "postal_code": "1100",
                "quantity": 2,
                "customization_notes": "Back print",
                "payment_method": Payment.COD,
                "gcash_reference": "LEFTOVER",
                "screenshot": bad_file,
                "save_profile": "on",
            },
        )
        order = Order.objects.get()
        self.assertRedirects(response, reverse("orders:confirmation", args=[order.number]))
        self.assertEqual(order.payment.method, Payment.COD)
        self.assertEqual(order.payment.gcash_reference, "")
        self.assertFalse(bool(order.payment.screenshot))
        self.assertFalse(order.payment.is_verified)

    def test_checkout_gcash_validates_receipt_prevents_duplicate_ref_and_guards_verified_cancel(self):
        settings_row = SiteSettings.load()
        settings_row.gcash_number = "09171234567"
        settings_row.gcash_account_name = "Boloman Prints"
        settings_row.save()

        self.client.force_login(self.user)
        missing = self.client.post(
            reverse("orders:checkout"),
            {
                "variant": self.variant.pk,
                "recipient_name": "Ana Cruz",
                "phone": "09171234567",
                "address_line": "123 Mabini Street",
                "city": "Quezon City",
                "province": "Metro Manila",
                "quantity": 1,
                "payment_method": Payment.GCASH,
                "gcash_reference": "12",
            },
        )
        self.assertEqual(missing.status_code, 200)
        self.assertContains(missing, "valid GCash reference number")
        self.assertContains(missing, "Upload a screenshot")

        placed = self.client.post(
            reverse("orders:checkout"),
            {
                "variant": self.variant.pk,
                "recipient_name": "Ana Cruz",
                "phone": "09171234567",
                "address_line": "123 Mabini Street",
                "city": "Quezon City",
                "province": "Metro Manila",
                "quantity": 1,
                "payment_method": Payment.GCASH,
                "gcash_reference": "9012 3456 7890",
                "screenshot": _receipt_png(),
            },
        )
        first = Order.objects.get()
        self.assertRedirects(placed, reverse("orders:confirmation", args=[first.number]))
        self.assertEqual(first.payment.method, Payment.GCASH)
        self.assertEqual(first.payment.gcash_reference, "9012 3456 7890")
        self.assertTrue(bool(first.payment.screenshot))

        # Duplicate active reference is rejected at both form and service layers.
        dup = self.client.post(
            reverse("orders:checkout"),
            {
                "variant": self.variant.pk,
                "recipient_name": "Ana Cruz",
                "phone": "09171234567",
                "address_line": "123 Mabini Street",
                "city": "Quezon City",
                "province": "Metro Manila",
                "quantity": 1,
                "payment_method": Payment.GCASH,
                "gcash_reference": "9012 3456 7890",
                "screenshot": _receipt_png("receipt2.png"),
            },
        )
        self.assertEqual(dup.status_code, 200)
        self.assertContains(dup, "already been used")
        with self.assertRaises(DuplicateGCashReference):
            place_order(
                user=self.user,
                variant=self.variant,
                quantity=1,
                customization_notes="",
                recipient_name="Ana Cruz",
                phone="09171234567",
                address="123 Mabini Street",
                payment_method=Payment.GCASH,
                gcash_reference="9012 3456 7890",
                screenshot=_receipt_png("receipt3.png"),
            )

        # Unverified GCash cannot jump into production.
        with self.assertRaises(PaymentVerificationRequired):
            set_order_status(first, Order.PROCESSING, self.user, "Start print")

        # Once verified, customer cannot self-cancel without staff handling refund.
        first.payment.is_verified = True
        first.payment.verified_at = timezone.now()
        first.payment.save(update_fields=["is_verified", "verified_at"])
        cancel_resp = self.client.post(reverse("orders:cancel", args=[first.number]))
        self.assertRedirects(cancel_resp, reverse("orders:detail", args=[first.number]))
        first.refresh_from_db()
        self.assertEqual(first.status, Order.NEW)

    def test_customer_must_login_first_and_returns_to_step_by_step_gcash_checkout(self):
        settings_row = SiteSettings.load()
        settings_row.gcash_number = "09171234567"
        settings_row.gcash_account_name = "Boloman Prints"
        settings_row.save()

        product_page = self.client.get(self.variant.product.get_absolute_url())
        self.assertContains(product_page, "Sign In First to Buy Online")

        checkout_url = f"{reverse('orders:checkout')}?variant={self.variant.pk}&qty=2&notes=TEAM+26"
        anon_get = self.client.get(checkout_url)
        self.assertEqual(anon_get.status_code, 302)
        self.assertIn(reverse("account_login"), anon_get["Location"])

        login_page = self.client.get(anon_get["Location"])
        self.assertContains(login_page, "Step 1 of 4")
        self.assertContains(login_page, "Photo Mug × 2")
        self.assertContains(login_page, "₱398.00")

        anon_post = self.client.post(
            reverse("orders:checkout"),
            {
                "variant": self.variant.pk,
                "quantity": 2,
                "customization_notes": "TEAM 26",
                "payment_method": Payment.COD,
            },
        )
        self.assertEqual(anon_post.status_code, 302)
        self.assertIn(reverse("account_login"), anon_post["Location"])
        self.assertEqual(Order.objects.count(), 0)

        logged_in = self.client.post(
            reverse("account_login"),
            {
                "login": "ana@example.com",
                "password": "pass12345",
                "next": checkout_url,
            },
        )
        self.assertRedirects(logged_in, checkout_url)

        checkout_page = self.client.get(checkout_url)
        self.assertContains(checkout_page, "₱398.00")
        self.assertContains(checkout_page, "TEAM 26")
        self.assertContains(checkout_page, "Option 1 · Scan GCash QR Code")
        self.assertContains(checkout_page, "Option 2 · Enter Owner's GCash Number")
        self.assertContains(checkout_page, "09171234567")
        self.assertContains(checkout_page, "Boloman Prints")

