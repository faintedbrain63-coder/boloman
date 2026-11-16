from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventory.models import ProductVariant, StockMovement
from inventory.services import InsufficientStock, move_stock
from orders.models import Order
from orders.services import next_order_number, place_order, set_order_status
from store.models import Category, Product


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
        self.assertEqual(first.items.get().customization_notes, "Print Ana on the front")
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
