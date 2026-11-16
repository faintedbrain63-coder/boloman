from django import template

register = template.Library()


@register.filter
def toast_class(tags):
    first = (tags or "info").split()[0]
    return {"error": "danger", "debug": "secondary"}.get(first, first)


@register.filter
def peso(value):
    try:
        return f"₱{value:,.2f}"
    except (TypeError, ValueError):
        return "—"


@register.filter
def order_badge_class(status):
    return {
        "NEW": "badge-info",
        "PROCESSING": "badge-progress",
        "FOR_DELIVERY": "badge-low",
        "SHIPPED": "badge-shipped",
        "COMPLETED": "badge-in",
        "CANCELLED": "badge-out",
    }.get(status, "badge-neutral")


@register.filter
def movement_badge_class(movement_type):
    return {
        "STOCK_IN": "badge-in",
        "SALE": "badge-info",
        "RETURN": "badge-shipped",
        "ADJUSTMENT": "badge-low",
        "CANCELLATION": "badge-out",
    }.get(movement_type, "badge-neutral")
