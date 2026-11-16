from django.db.models import F

from core.models import ContactMessage, SiteSettings
from inventory.models import ProductVariant
from orders.models import Order, Payment
from store.models import Category


def shop(request):
    data = {
        "site_settings": SiteSettings.load(),
        "nav_categories": Category.objects.filter(is_active=True).order_by("display_order", "name"),
    }
    user = request.user
    if user.is_authenticated and user.is_staff and request.path.startswith("/dashboard"):
        data["dash_unread"] = ContactMessage.objects.filter(is_read=False).count()
        data["dash_pending_gcash"] = Payment.objects.filter(method=Payment.GCASH, is_verified=False).count()
        data["dash_new_orders"] = Order.objects.filter(status=Order.NEW).count()
        data["dash_low_stock"] = ProductVariant.objects.filter(
            is_active=True,
            quantity_on_hand__lte=F("reorder_level"),
        ).count()
    return data
