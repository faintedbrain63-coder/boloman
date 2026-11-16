from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import CustomerProfile
from inventory.models import ProductVariant
from inventory.services import InsufficientStock
from orders.forms import CheckoutForm
from orders.models import Order, Payment
from orders.services import DuplicateGCashReference, place_order, set_order_status


def _owned_order(request, number):
    queryset = Order.objects.prefetch_related("items", "status_history", "payment")
    if request.user.is_staff:
        return get_object_or_404(queryset, number=number)
    return get_object_or_404(queryset, number=number, user=request.user)


def checkout(request):
    if not request.user.is_authenticated:
        next_url = request.get_full_path()
        if "?" not in next_url and request.POST.get("variant"):
            params = QueryDict(mutable=True)
            params["variant"] = request.POST["variant"]
            if request.POST.get("quantity"):
                params["qty"] = request.POST["quantity"]
            if request.POST.get("customization_notes"):
                params["notes"] = request.POST["customization_notes"]
            next_url = f"{request.path}?{params.urlencode()}"
        messages.info(
            request,
            "Please sign in or create an account first to buy online. Your selected item is saved for checkout.",
        )
        return redirect_to_login(next_url)

    raw_variant = (request.POST.get("variant") or request.GET.get("variant") or "").strip()
    if not raw_variant.isdigit():
        messages.info(request, "Choose a product, color, and size first before checking out.")
        return redirect("store:product_list")

    variant = get_object_or_404(
        ProductVariant.objects.select_related("product", "product__category"),
        pk=int(raw_variant),
        is_active=True,
        product__is_active=True,
    )
    profile, _created = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = CheckoutForm(request.POST, request.FILES, variant=variant)
        if form.is_valid():
            data = form.cleaned_data
            try:
                order = place_order(
                    user=request.user,
                    variant=variant,
                    quantity=data["quantity"],
                    customization_notes=data["customization_notes"],
                    recipient_name=data["recipient_name"],
                    phone=data["phone"],
                    address=form.delivery_address,
                    payment_method=data["payment_method"],
                    gcash_reference=data.get("gcash_reference") or "",
                    screenshot=data.get("screenshot"),
                )
            except InsufficientStock as exc:
                form.add_error("quantity", f"Only {exc.available} left in stock.")
            except DuplicateGCashReference as exc:
                form.add_error("gcash_reference", str(exc))
            except ProductVariant.DoesNotExist:
                messages.error(request, "That option is no longer available.")
                return redirect(variant.product.get_absolute_url())
            else:
                if data.get("save_profile"):
                    names = data["recipient_name"].split(None, 1)
                    request.user.first_name = names[0]
                    request.user.last_name = names[1] if len(names) > 1 else ""
                    request.user.save(update_fields=["first_name", "last_name"])
                    profile.phone = data["phone"]
                    profile.address_line = data["address_line"]
                    profile.city = data["city"]
                    profile.province = data["province"]
                    profile.postal_code = data.get("postal_code") or ""
                    profile.save()
                messages.success(request, f"Order {order.number} is placed.")
                return redirect("orders:confirmation", number=order.number)
    else:
        try:
            quantity = max(1, int(request.GET.get("qty") or 1))
        except ValueError:
            quantity = 1
        if variant.quantity_on_hand > 0:
            quantity = min(quantity, variant.quantity_on_hand)
        form = CheckoutForm(
            variant=variant,
            initial={
                "recipient_name": request.user.get_full_name(),
                "phone": profile.phone,
                "address_line": profile.address_line,
                "city": profile.city,
                "province": profile.province,
                "postal_code": profile.postal_code,
                "quantity": quantity,
                "customization_notes": request.GET.get("notes", ""),
                "save_profile": True,
            },
        )

    try:
        active_qty = max(1, int(form["quantity"].value() or 1))
    except (TypeError, ValueError):
        active_qty = 1
    initial_total = variant.price * Decimal(active_qty)

    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "variant": variant,
            "product": variant.product,
            "initial_total": initial_total,
        },
    )


@login_required
def confirmation(request, number):
    order = _owned_order(request, number)
    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def order_list(request):
    orders = request.user.orders.prefetch_related("items", "payment")
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, number):
    order = _owned_order(request, number)
    if not request.user.is_staff and order.user_id != request.user.id:
        order = get_object_or_404(Order, number=number, user=request.user)
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
@require_POST
def cancel_order(request, number):
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), number=number, user=request.user)
        payment = Payment.objects.select_for_update().filter(order=order).first()
        if order.status != Order.NEW:
            messages.error(request, "Only a new order can be cancelled here. Message the shop if you need help.")
        elif payment is not None and payment.is_verified:
            messages.error(
                request,
                "Your payment has already been verified. Message the shop so we can assist with cancellation and refund.",
            )
        else:
            set_order_status(order, Order.CANCELLED, request.user, note="Cancelled by customer")
            messages.success(request, f"{order.number} is cancelled and the stock is back.")
    return redirect("orders:detail", number=order.number)
