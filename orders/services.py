from django.db import IntegrityError, transaction
from django.utils import timezone

from inventory.models import StockMovement
from inventory.services import InsufficientStock, move_stock
from orders.models import Order, OrderItem, OrderSequence, OrderStatusHistory, Payment


class PaymentVerificationRequired(Exception):
    """Raised when an unverified GCash order is moved into production or shipping."""


class DuplicateGCashReference(ValueError):
    """Raised when an active order already uses the same GCash reference number."""


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

    valid_methods = {code for code, _label in Payment.METHODS}
    if payment_method not in valid_methods:
        raise ValueError("Choose a valid payment method.")

    cleaned_ref = " ".join((gcash_reference or "").split())
    if payment_method == Payment.GCASH:
        if not cleaned_ref or sum(ch.isalnum() for ch in cleaned_ref) < 4:
            raise ValueError("Enter a valid GCash reference number.")
        if not screenshot:
            raise ValueError("Upload a screenshot of the GCash payment.")
    else:
        cleaned_ref = ""
        screenshot = None

    with transaction.atomic():
        from inventory.models import ProductVariant

        locked = ProductVariant.objects.select_for_update().select_related("product__category").get(pk=variant.pk)
        if not locked.is_active or not locked.product.is_active:
            raise ProductVariant.DoesNotExist
        if locked.quantity_on_hand < quantity:
            raise InsufficientStock(available=locked.quantity_on_hand, requested=quantity)

        if payment_method == Payment.GCASH and (
            Payment.objects.select_for_update()
            .filter(method=Payment.GCASH, gcash_reference__iexact=cleaned_ref)
            .exclude(order__status=Order.CANCELLED)
            .exists()
        ):
            raise DuplicateGCashReference("This GCash reference number has already been used on another order.")

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
            category_name=locked.product.category.name,
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
            gcash_reference=cleaned_ref,
        )
        if screenshot:
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
        payment = Payment.objects.select_for_update().filter(order=order).first()
        old = order.status
        if old == new_status:
            return order

        actor = user if getattr(user, "is_authenticated", False) else None

        if (
            payment is not None
            and payment.method == Payment.GCASH
            and not payment.is_verified
            and new_status not in {Order.NEW, Order.CANCELLED}
        ):
            raise PaymentVerificationRequired(
                "Verify the GCash payment before moving this order into production or shipping."
            )

        items = list(order.items.select_related("variant"))
        if old != Order.CANCELLED and new_status == Order.CANCELLED:
            for item in items:
                if item.variant_id is None:
                    continue
                move_stock(
                    variant=item.variant,
                    quantity=item.quantity,
                    movement_type=StockMovement.CANCELLATION,
                    user=actor,
                    order=order,
                    notes=note or f"Cancelled {order.number}",
                )
        elif old == Order.CANCELLED and new_status != Order.CANCELLED:
            if (
                payment is not None
                and payment.method == Payment.GCASH
                and payment.gcash_reference
                and Payment.objects.select_for_update()
                .filter(method=Payment.GCASH, gcash_reference__iexact=payment.gcash_reference)
                .exclude(pk=payment.pk)
                .exclude(order__status=Order.CANCELLED)
                .exists()
            ):
                raise DuplicateGCashReference(
                    "Another active order already uses this GCash reference number."
                )
            if any(item.variant_id is None for item in items):
                raise InsufficientStock(available=0, requested=1)
            for item in items:
                move_stock(
                    variant=item.variant,
                    quantity=-item.quantity,
                    movement_type=StockMovement.SALE,
                    user=actor,
                    order=order,
                    notes=note or f"Reopened {order.number}",
                )

        if (
            new_status == Order.COMPLETED
            and payment is not None
            and payment.method == Payment.COD
            and not payment.is_verified
        ):
            payment.is_verified = True
            payment.verified_by = actor
            payment.verified_at = timezone.now()
            payment.save(update_fields=["is_verified", "verified_by", "verified_at"])

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order,
            from_status=old,
            to_status=new_status,
            changed_by=actor,
            note=note,
        )
        return order
