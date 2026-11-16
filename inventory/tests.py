from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventory.models import ProductVariant, StockMovement
from inventory.services import InsufficientStock, move_stock
from store.models import Category, Product


class StockMovementTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Cotton Shirts", code="CTN", variant_type=Category.SHIRT)
        product = Product.objects.create(
            category=category,
            name="Test Tee",
            description="A tee.",
            base_price=Decimal("350.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            color_name="Black",
            color_hex="#111111",
            size="M",
            sku="CTN-BLK-M",
            quantity_on_hand=0,
            reorder_level=5,
            cost_price=Decimal("100.00"),
        )
        self.user = get_user_model().objects.create_user(username="buyer", email="buyer@example.com", password="pass12345")

    def test_stock_in_writes_a_ledger_row(self):
        movement = move_stock(
            variant=self.variant,
            quantity=10,
            movement_type=StockMovement.STOCK_IN,
            user=self.user,
            notes="Received blanks",
        )
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.quantity_on_hand, 10)
        self.assertEqual(movement.balance_before, 0)
        self.assertEqual(movement.balance_after, 10)
        self.assertEqual(movement.user, self.user)

    def test_stock_cannot_go_below_zero(self):
        move_stock(variant=self.variant, quantity=2, movement_type=StockMovement.STOCK_IN, notes="Start")
        with self.assertRaises(InsufficientStock):
            move_stock(variant=self.variant, quantity=-5, movement_type=StockMovement.ADJUSTMENT, notes="Too many")
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.quantity_on_hand, 2)

    def test_sale_must_remove_stock(self):
        with self.assertRaises(ValueError):
            move_stock(variant=self.variant, quantity=1, movement_type=StockMovement.SALE, notes="Wrong sign")
