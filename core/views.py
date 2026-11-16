from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render

from core.forms import ContactForm
from inventory.models import ProductVariant
from store.models import Category, Product


def home(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Message received. Our production team will get back to you shortly.")
            return redirect("/#contact")
    else:
        form = ContactForm()

    featured = list(
        Product.objects.filter(is_active=True, is_featured=True, category__is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")[:8]
    )
    if len(featured) < 4:
        featured = list(
            Product.objects.filter(is_active=True, category__is_active=True)
            .select_related("category")
            .prefetch_related("images", "variants")[:8]
        )

    categories = list(
        Category.objects.filter(is_active=True)
        .annotate(item_count=Count("products", filter=Q(products__is_active=True)))
        .prefetch_related("products__images")
        .order_by("display_order", "name")
    )
    for cat in categories:
        sample = next((p for p in cat.products.all() if p.is_active and p.primary_image), None)
        cat.sample_image_url = sample.primary_image.image.url if sample else None

    return render(
        request,
        "core/home.html",
        {
            "form": form,
            "featured": featured,
            "categories": categories,
            "product_count": Product.objects.filter(is_active=True).count(),
            "variant_count": ProductVariant.objects.filter(is_active=True).count(),
            "total_units": ProductVariant.objects.filter(is_active=True).aggregate(total=Sum("quantity_on_hand"))["total"] or 0,
            "color_count": ProductVariant.objects.filter(is_active=True).values("color_name").distinct().count(),
            "category_count": len(categories),
        },
    )
