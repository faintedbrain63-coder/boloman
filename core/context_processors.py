from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.db.models import F

from core.models import ContactMessage, SiteSettings
from inventory.models import ProductVariant
from orders.models import Order, Payment
from store.models import Category


def _pending_checkout(request):
    next_url = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if not next_url.startswith("/orders/checkout"):
        return None
    query = parse_qs(urlsplit(next_url).query)
    raw_variant = (query.get("variant") or [""])[0].strip()
    if not raw_variant.isdigit():
        return None
    variant = (
        ProductVariant.objects.select_related("product", "product__category")
        .prefetch_related("product__images")
        .filter(pk=int(raw_variant), is_active=True, product__is_active=True)
        .first()
    )
    if variant is None:
        return None
    try:
        qty = max(1, int((query.get("qty") or ["1"])[0]))
    except ValueError:
        qty = 1
    if variant.quantity_on_hand > 0:
        qty = min(qty, variant.quantity_on_hand)
    notes = ((query.get("notes") or [""])[0] or "").strip()[:140]
    return {
        "variant": variant,
        "product": variant.product,
        "qty": qty,
        "notes": notes,
        "total": variant.price * Decimal(qty),
    }


def shop(request):
    google_app = settings.SOCIALACCOUNT_PROVIDERS.get("google", {}).get("APP", {})
    data = {
        "site_settings": SiteSettings.load(),
        "nav_categories": Category.objects.filter(is_active=True).order_by("display_order", "name"),
        "google_login_enabled": bool(google_app.get("client_id")),
    }
    user = request.user
    if not user.is_authenticated and request.path.startswith("/accounts/"):
        pending = _pending_checkout(request)
        if pending is not None:
            data["pending_checkout"] = pending
    if user.is_authenticated and user.is_staff and request.path.startswith("/dashboard"):
        data["dash_unread"] = ContactMessage.objects.filter(is_read=False).count()
        data["dash_pending_gcash"] = (
            Payment.objects.filter(method=Payment.GCASH, is_verified=False)
            .exclude(order__status=Order.CANCELLED)
            .count()
        )
        data["dash_new_orders"] = Order.objects.filter(status=Order.NEW).count()
        data["dash_low_stock"] = ProductVariant.objects.filter(
            is_active=True,
            quantity_on_hand__lte=F("reorder_level"),
        ).count()
    return data
