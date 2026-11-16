from django.core.paginator import Paginator
from django.db.models import Count, F, Min, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render

from inventory.constants import CAP_SIZES, MUG_CAPACITIES, SHIRT_SIZES, TUMBLER_CAPACITIES, size_label
from store.models import Category, Product

OPTION_ORDER = {
    code: index
    for index, code in enumerate([*SHIRT_SIZES, *CAP_SIZES, *MUG_CAPACITIES, *TUMBLER_CAPACITIES])
}

SORTS = {
    "newest": "Newest arrivals",
    "price_asc": "Price: low to high",
    "price_desc": "Price: high to low",
}


def _catalog():
    return (
        Product.objects.filter(is_active=True, category__is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")
        .annotate(
            sort_price=Coalesce(
                Min(
                    Coalesce("variants__selling_price", "base_price"),
                    filter=Q(variants__is_active=True),
                ),
                F("base_price"),
            ),
            stock_sum=Coalesce(
                Sum("variants__quantity_on_hand", filter=Q(variants__is_active=True)),
                0,
            ),
        )
    )


def product_list(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    in_stock = request.GET.get("in_stock", "") == "1"
    sort = request.GET.get("sort", "newest")
    if sort not in SORTS:
        sort = "newest"

    products = _catalog()
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(short_description__icontains=query) | Q(description__icontains=query)
        )
    current_category = None
    if category_slug:
        current_category = Category.objects.filter(slug=category_slug, is_active=True).first()
        if current_category:
            products = products.filter(category=current_category)
    if in_stock:
        products = products.filter(stock_sum__gt=0)

    if sort == "price_asc":
        products = products.order_by("sort_price", "name")
    elif sort == "price_desc":
        products = products.order_by("-sort_price", "name")
    else:
        products = products.order_by("-created_at")

    categories = (
        Category.objects.filter(is_active=True)
        .annotate(item_count=Count("products", filter=Q(products__is_active=True)))
        .order_by("display_order", "name")
    )

    page = Paginator(products, 12).get_page(request.GET.get("page"))
    return render(
        request,
        "store/product_list.html",
        {
            "page": page,
            "query": query,
            "in_stock": in_stock,
            "sort": sort,
            "sorts": SORTS,
            "current_category": current_category,
            "categories": categories,
            "total_catalog_count": Product.objects.filter(is_active=True, category__is_active=True).count(),
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images", "variants"),
        slug=slug,
        is_active=True,
        category__is_active=True,
    )
    variants = sorted(
        (variant for variant in product.variants.all() if variant.is_active),
        key=lambda v: (v.color_name.lower(), OPTION_ORDER.get(v.size or v.capacity, 99), v.size, v.capacity),
    )
    payload = {
        "variants": [
            {
                "id": variant.id,
                "color": variant.color_name,
                "hex": variant.color_hex,
                "size": variant.size,
                "sizeLabel": size_label(variant.size) if variant.size else "",
                "capacity": variant.capacity,
                "stock": variant.quantity_on_hand,
                "price": f"{variant.price:.2f}",
                "sku": variant.sku,
                "reorder": variant.reorder_level,
            }
            for variant in variants
        ]
    }
    return render(
        request,
        "store/product_detail.html",
        {
            "product": product,
            "variants": variants,
            "variant_payload": payload,
            "related": _catalog().filter(category=product.category).exclude(pk=product.pk)[:4],
        },
    )
