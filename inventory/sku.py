from inventory.constants import color_code
from inventory.models import ProductVariant


def build_sku(product, color_name, size="", capacity=""):
    parts = [product.category.code.upper(), color_code(color_name)]
    if size:
        parts.append(size.upper())
    if capacity:
        parts.append(capacity.upper().replace(" ", ""))
    base = "-".join(parts)
    sku = base
    number = 2
    while ProductVariant.objects.filter(sku=sku).exists():
        sku = f"{base}-{number}"
        number += 1
    return sku
