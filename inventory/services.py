from django.db import transaction

from inventory.models import ProductVariant, StockMovement


class InsufficientStock(Exception):
    def __init__(self, available, requested):
        self.available = available
        self.requested = requested
        super().__init__(f"Only {available} in stock (requested {requested}).")


ADDING = {StockMovement.STOCK_IN, StockMovement.RETURN, StockMovement.CANCELLATION}


def move_stock(*, variant, quantity, movement_type, user=None, order=None, notes=""):
    """Change on-hand stock and write a ledger row. Quantity is signed."""
    quantity = int(quantity)
    if quantity == 0:
        raise ValueError("Quantity cannot be zero.")
    if movement_type in ADDING and quantity < 0:
        raise ValueError("This movement type must add stock.")
    if movement_type == StockMovement.SALE and quantity > 0:
        raise ValueError("A sale must remove stock.")

    actor = user if user is not None and getattr(user, "is_authenticated", False) else None

    with transaction.atomic():
        locked = ProductVariant.objects.select_for_update().get(pk=variant.pk)
        before = locked.quantity_on_hand
        after = before + quantity
        if after < 0:
            raise InsufficientStock(available=before, requested=abs(quantity))
        locked.quantity_on_hand = after
        locked.save(update_fields=["quantity_on_hand"])
        return StockMovement.objects.create(
            variant=locked,
            movement_type=movement_type,
            quantity=quantity,
            balance_before=before,
            balance_after=after,
            order=order,
            user=actor,
            notes=notes,
        )
