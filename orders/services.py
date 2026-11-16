from django.db import IntegrityError, transaction
from django.utils import timezone

from inventory.models import StockMovement
from inventory.services import InsufficientStock, move_stock
from orders.models import Order, OrderItem, OrderSequence, OrderStatusHistory, Payment


def next_order_number():
    today = timezone.localdate()
    with transaction.atomic():
        try:
            with transaction.atomic():
                OrderSequence.objects.create(date=today, last_number=0)
        except IntegrityError:
            pass
        seq = OrderSequence.objects.select_for_update().get(date=today)
        seq.last_number += 1
        seq.save(update_fields=["last_number"])
        return f"ORD-{today:%Y%m%d}-{seq.last_number:04d}"


def place_order(
    *,
    user,
    variant,
    quantity,
    customization_notes,
    recipient_name,
    phone,
    address,
    payment_method,
    gcash_reference="",
    screenshot=None,
):
    quantity = int(quantity)
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    with transaction.atomic():
        from inventory.models import ProductVariant

        locked = ProductVariant.objects.select_for_update().select_related("product").get(pk=variant.pk)
        if not locked.is_active or not locked.product.is_active:
            raise ProductVariant.DoesNotExist
        if locked.quantity_on_hand < quantity:
            raise InsufficientStock(available=locked.quantity_on_hand, requested=quantity)

        unit_price = locked.price
        total = unit_price * quantity
        number = next_order_number()
        order = Order.objects.create(
            number=number,
            user=user,
            recipient_name=recipient_name,
            phone=phone,
            address=address,
            subtotal=total,
            total=total,
        )
        OrderItem.objects.create(
            order=order,
            variant=locked,
            product_name=locked.product.name,
            color_name=locked.color_name,
            color_hex=locked.color_hex,
            size=locked.size,
            capacity=locked.capacity,
            sku=locked.sku,
            unit_price=unit_price,
            quantity=quantity,
            customization_notes=customization_notes.strip(),
        )
        payment = Payment(
            order=order,
            method=payment_method,
            amount=total,
            gcash_reference=gcash_reference.strip() if payment_method == Payment.GCASH else "",
        )
        if payment_method == Payment.GCASH and screenshot:
            payment.screenshot = screenshot
        payment.save()
        move_stock(
            variant=locked,
            quantity=-quantity,
            movement_type=StockMovement.SALE,
            user=user,
            order=order,
            notes=f"Sale for {number}",
        )
        OrderStatusHistory.objects.create(
            order=order,
            from_status="",
            to_status=Order.NEW,
            changed_by=user,
            note="Order placed",
        )
        return order


def set_order_status(order, new_status, user, note=""):
    valid = {code for code, _label in Order.STATUS_CHOICES}
    if new_status not in valid:
        raise ValueError("Unknown status.")

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        old = order.status
        if old == new_status:
            return order

        items = list(order.items.select_related("variant"))
        if old != Order.CANCELLED and new_status == Order.CANCELLED:
            for item in items:
                move_stock(
                    variant=item.variant,
                    quantity=item.quantity,
                    movement_type=StockMovement.CANCELLATION,
                    user=user,
                    order=order,
                    notes=note or f"Cancelled {order.number}",
                )
        elif old == Order.CANCELLED and new_status != Order.CANCELLED:
            for item in items:
                move_stock(
                    variant=item.variant,
                    quantity=-item.quantity,
                    movement_type=StockMovement.SALE,
                    user=user,
                    order=order,
                    notes=note or f"Reopened {order.number}",
                )

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order,
            from_status=old,
            to_status=new_status,
            changed_by=user if getattr(user, "is_authenticated", False) else None,
            note=note,
        )
        return order
