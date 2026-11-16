import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import CustomerProfile
from core.forms import SiteSettingsForm
from core.models import ContactMessage, SiteSettings
from dashboard.decorators import staff_required
from dashboard.forms import (
    AdjustmentForm,
    CategoryForm,
    ImageFormSet,
    OrderStatusForm,
    ProductForm,
    StockInForm,
    VariantForm,
    VariantMatrixForm,
)
from inventory.models import ProductVariant, StockMovement
from inventory.services import InsufficientStock, move_stock
from inventory.sku import build_sku
from orders.models import Order, OrderItem, Payment
from orders.services import set_order_status
from store.models import Category, Product

User = get_user_model()


def _page(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


@staff_required
def overview(request):
    start = timezone.now() - timedelta(days=29)
    sales_total = Order.objects.exclude(status=Order.CANCELLED).aggregate(total=Sum("total"))["total"] or 0
    status_rows = Order.objects.values("status").annotate(count=Count("id"))
    status_map = {row["status"]: row["count"] for row in status_rows}
    daily = {
        row["day"]: float(row["total"] or 0)
        for row in (
            Order.objects.exclude(status=Order.CANCELLED)
            .filter(created_at__gte=start)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total"))
        )
    }
    labels = []
    series = []
    today = timezone.localdate()
    for offset in range(29, -1, -1):
        day = today - timedelta(days=offset)
        labels.append(day.strftime("%b %d"))
        series.append(daily.get(day, 0))

    sold = OrderItem.objects.exclude(order__status=Order.CANCELLED)
    top_products = list(
        sold.values("product_name")
        .annotate(qty=Sum("quantity"), revenue=Sum(F("unit_price") * F("quantity")))
        .order_by("-qty")[:5]
    )
    top_categories = list(
        sold.values(name=F("variant__product__category__name"))
        .annotate(qty=Sum("quantity"), revenue=Sum(F("unit_price") * F("quantity")))
        .exclude(name=None)
        .order_by("-qty")[:6]
    )
    return render(
        request,
        "dashboard/overview.html",
        {
            "sales_total": sales_total,
            "order_count": Order.objects.count(),
            "customer_count": User.objects.filter(is_staff=False).count(),
            "pending_gcash": Payment.objects.filter(method=Payment.GCASH, is_verified=False).count(),
            "status_labels": [label for _code, label in Order.STATUS_CHOICES],
            "status_counts": [status_map.get(code, 0) for code, _label in Order.STATUS_CHOICES],
            "chart_labels": labels,
            "chart_series": series,
            "top_products": top_products,
            "top_categories": top_categories,
            "recent_orders": Order.objects.select_related("user", "payment")[:8],
            "low_stock": ProductVariant.objects.filter(quantity_on_hand__gt=0, quantity_on_hand__lte=F("reorder_level"))
            .select_related("product")[:8],
            "out_of_stock": ProductVariant.objects.filter(quantity_on_hand=0, is_active=True).select_related("product")[:8],
        },
    )


@staff_required
def product_list(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.select_related("category").prefetch_related("variants")
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    return render(request, "dashboard/product_list.html", {"page": _page(request, products), "query": query})


@staff_required
def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        formset = ImageFormSet(request.POST, request.FILES, instance=product or Product())
        if form.is_valid() and formset.is_valid():
            product = form.save()
            formset.instance = product
            formset.save()
            images = list(product.images.all())
            primaries = [image for image in images if image.is_primary]
            if len(primaries) > 1:
                for image in primaries[1:]:
                    image.is_primary = False
                    image.save(update_fields=["is_primary"])
            elif images and not primaries:
                images[0].is_primary = True
                images[0].save(update_fields=["is_primary"])
            messages.success(request, "Product saved.")
            return redirect("dashboard:product_edit", pk=product.pk)
    else:
        form = ProductForm(instance=product)
        formset = ImageFormSet(instance=product or Product())
    return render(request, "dashboard/product_form.html", {"form": form, "formset": formset, "product": product})


@staff_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
        messages.success(request, "Product deleted.")
    except ProtectedError:
        messages.error(request, "This product has orders, so it was kept. Mark it inactive instead.")
    return redirect("dashboard:products")


@staff_required
def category_list(request):
    return render(request, "dashboard/category_list.html", {"categories": Category.objects.all()})


@staff_required
def category_edit(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category saved.")
        return redirect("dashboard:categories")
    return render(request, "dashboard/category_form.html", {"form": form, "category": category})


@staff_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    try:
        category.delete()
        messages.success(request, "Category deleted.")
    except ProtectedError:
        messages.error(request, "This category still has products.")
    return redirect("dashboard:categories")


@staff_required
def variant_list(request, product_pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=product_pk)
    variants = product.variants.select_related("supplier")
    return render(request, "dashboard/variant_list.html", {"product": product, "variants": variants})


@staff_required
def variant_edit(request, pk=None, product_pk=None):
    variant = get_object_or_404(ProductVariant.objects.select_related("product__category"), pk=pk) if pk else None
    product = variant.product if variant else get_object_or_404(Product.objects.select_related("category"), pk=product_pk)
    form = VariantForm(request.POST or None, instance=variant, product=product)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        saved.product = product
        saved.size = form.cleaned_data.get("size") or ""
        saved.capacity = form.cleaned_data.get("capacity") or ""
        creating = saved.pk is None
        if creating:
            saved.quantity_on_hand = 0
            saved.sku = build_sku(product, saved.color_name, saved.size, saved.capacity)
        saved.save()
        opening = form.cleaned_data.get("opening_quantity") or 0
        if creating and opening:
            move_stock(
                variant=saved,
                quantity=opening,
                movement_type=StockMovement.STOCK_IN,
                user=request.user,
                notes=form.cleaned_data["reason"].strip(),
            )
        messages.success(request, "Variant saved.")
        return redirect("dashboard:variants", product_pk=product.pk)
    return render(request, "dashboard/variant_form.html", {"form": form, "product": product, "variant": variant})


@staff_required
def variant_generate(request, product_pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=product_pk)
    form = VariantMatrixForm(request.POST or None, product=product)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        created = 0
        sizes = data.get("sizes") or [""]
        capacities = data.get("capacities") or [""]
        if product.category.variant_type == Category.DRINKWARE:
            sizes = [""]
        else:
            capacities = [""]
        for color_name, color_hex in data["parsed_colors"]:
            for size in sizes:
                for capacity in capacities:
                    exists = product.variants.filter(color_name=color_name, size=size or "", capacity=capacity or "").exists()
                    if exists:
                        continue
                    variant = ProductVariant.objects.create(
                        product=product,
                        color_name=color_name,
                        color_hex=color_hex,
                        size=size or "",
                        capacity=capacity or "",
                        sku=build_sku(product, color_name, size or "", capacity or ""),
                        quantity_on_hand=0,
                        reorder_level=data["reorder_level"],
                        cost_price=data["cost_price"],
                        selling_price=data.get("selling_price"),
                        supplier=data.get("supplier"),
                        location=data.get("location") or "",
                    )
                    if data["quantity"]:
                        move_stock(
                            variant=variant,
                            quantity=data["quantity"],
                            movement_type=StockMovement.STOCK_IN,
                            user=request.user,
                            notes=data["reason"].strip(),
                        )
                    created += 1
        messages.success(request, f"Created {created} variant{'s' if created != 1 else ''}.")
        return redirect("dashboard:variants", product_pk=product.pk)
    return render(request, "dashboard/variant_generate.html", {"form": form, "product": product})


@staff_required
@require_POST
def variant_delete(request, pk):
    variant = get_object_or_404(ProductVariant, pk=pk)
    product_pk = variant.product_id
    try:
        variant.delete()
        messages.success(request, "Variant deleted.")
    except ProtectedError:
        messages.error(request, "This variant has stock history or orders. Mark it inactive instead.")
    return redirect("dashboard:variants", product_pk=product_pk)


def _filtered_orders(request):
    orders = Order.objects.select_related("user", "payment")
    status = request.GET.get("status", "")
    method = request.GET.get("method", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    query = request.GET.get("q", "").strip()
    if status:
        orders = orders.filter(status=status)
    if method:
        orders = orders.filter(payment__method=method)
    if start:
        orders = orders.filter(created_at__date__gte=start)
    if end:
        orders = orders.filter(created_at__date__lte=end)
    if query:
        orders = orders.filter(Q(number__icontains=query) | Q(recipient_name__icontains=query) | Q(user__email__icontains=query))
    return orders, {"status": status, "method": method, "start": start, "end": end, "q": query}


@staff_required
def order_list(request):
    orders, filters = _filtered_orders(request)
    summary = {
        "total": Order.objects.count(),
        "new": Order.objects.filter(status=Order.NEW).count(),
        "active": Order.objects.filter(status__in=[Order.PROCESSING, Order.FOR_DELIVERY, Order.SHIPPED]).count(),
        "unverified_gcash": Payment.objects.filter(method=Payment.GCASH, is_verified=False).count(),
    }
    return render(
        request,
        "dashboard/order_list.html",
        {
            "page": _page(request, orders),
            "filters": filters,
            "statuses": Order.STATUS_CHOICES,
            "methods": Payment.METHODS,
            "summary": summary,
        },
    )


@staff_required
def order_detail(request, number):
    order = get_object_or_404(
        Order.objects.select_related("user", "payment", "payment__verified_by").prefetch_related(
            "items__variant", "status_history__changed_by"
        ),
        number=number,
    )
    form = OrderStatusForm(initial={"status": order.status})
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "status":
            form = OrderStatusForm(request.POST)
            if form.is_valid():
                try:
                    set_order_status(order, form.cleaned_data["status"], request.user, form.cleaned_data["note"])
                except InsufficientStock as exc:
                    messages.error(request, f"Not enough stock to reopen this order. Only {exc.available} left.")
                else:
                    messages.success(request, "Status updated.")
                    return redirect("dashboard:order_detail", number=order.number)
        elif action == "verify":
            payment = order.payment
            if payment.method == Payment.GCASH and not payment.is_verified:
                payment.is_verified = True
                payment.verified_by = request.user
                payment.verified_at = timezone.now()
                payment.save(update_fields=["is_verified", "verified_by", "verified_at"])
                messages.success(request, "GCash payment marked as verified.")
            return redirect("dashboard:order_detail", number=order.number)
    return render(request, "dashboard/order_detail.html", {"order": order, "form": form})


@staff_required
def customer_list(request):
    query = request.GET.get("q", "").strip()
    customers = User.objects.select_related("profile").annotate(order_count=Count("orders")).order_by("-date_joined")
    if query:
        customers = customers.filter(
            Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(username__icontains=query)
        )
    page = _page(request, customers)
    for customer in page.object_list:
        profile, _created = CustomerProfile.objects.get_or_create(user=customer)
        customer.profile = profile
    return render(request, "dashboard/customer_list.html", {"page": page, "query": query})


@staff_required
def message_list(request):
    messages_qs = ContactMessage.objects.all()
    state = request.GET.get("state", "")
    if state == "unread":
        messages_qs = messages_qs.filter(is_read=False)
    elif state == "read":
        messages_qs = messages_qs.filter(is_read=True)
    return render(request, "dashboard/message_list.html", {"page": _page(request, messages_qs), "state": state})


@staff_required
@require_POST
def message_toggle(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    message.is_read = not message.is_read
    message.save(update_fields=["is_read"])
    return redirect("dashboard:messages")


@staff_required
def site_settings_view(request):
    settings_row = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, instance=settings_row)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Site settings saved.")
        return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html", {"form": form})


def _inventory_queryset(request):
    variants = ProductVariant.objects.select_related("product__category", "supplier").order_by(
        "product__category__display_order", "product__name", "color_name", "size", "capacity"
    )
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")
    if query:
        variants = variants.filter(Q(sku__icontains=query) | Q(product__name__icontains=query) | Q(color_name__icontains=query))
    if category:
        variants = variants.filter(product__category__slug=category)
    if status == "low":
        variants = variants.filter(quantity_on_hand__gt=0, quantity_on_hand__lte=F("reorder_level"))
    elif status == "out":
        variants = variants.filter(quantity_on_hand=0)
    elif status == "in":
        variants = variants.filter(quantity_on_hand__gt=F("reorder_level"))
    return variants, {"q": query, "category": category, "status": status}


@staff_required
def inventory_list(request):
    variants, filters = _inventory_queryset(request)
    all_variants = ProductVariant.objects.all()
    summary = {
        "skus": all_variants.count(),
        "units": all_variants.aggregate(total=Sum("quantity_on_hand"))["total"] or 0,
        "low": all_variants.filter(quantity_on_hand__gt=0, quantity_on_hand__lte=F("reorder_level")).count(),
        "out": all_variants.filter(quantity_on_hand=0).count(),
    }
    return render(
        request,
        "dashboard/inventory.html",
        {
            "page": _page(request, variants, 25),
            "filters": filters,
            "categories": Category.objects.filter(is_active=True),
            "summary": summary,
        },
    )


@staff_required
def inventory_export(request):
    variants, _filters = _inventory_queryset(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="boloman-inventory.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["SKU", "Product", "Category", "Color", "Size", "Capacity", "On hand", "Reorder level", "Status", "Cost", "Price", "Supplier", "Location"]
    )
    for variant in variants:
        writer.writerow(
            [
                variant.sku,
                variant.product.name,
                variant.product.category.name,
                variant.color_name,
                variant.size,
                variant.capacity,
                variant.quantity_on_hand,
                variant.reorder_level,
                variant.stock_label,
                variant.cost_price,
                variant.price,
                variant.supplier.name if variant.supplier else "",
                variant.location,
            ]
        )
    return response


@staff_required
def stock_in(request):
    initial = {}
    variant_id = request.GET.get("variant")
    if variant_id:
        initial["variant"] = variant_id
    form = StockInForm(request.POST or None, initial=None if request.method == "POST" else initial)
    if request.method == "POST" and form.is_valid():
        variant = form.cleaned_data["variant"]
        if form.cleaned_data.get("unit_cost") is not None:
            variant.cost_price = form.cleaned_data["unit_cost"]
            variant.save(update_fields=["cost_price"])
        move_stock(
            variant=variant,
            quantity=form.cleaned_data["quantity"],
            movement_type=StockMovement.STOCK_IN,
            user=request.user,
            notes=form.cleaned_data["reason"].strip(),
        )
        messages.success(request, f"Stock added to {variant.sku}.")
        return redirect("dashboard:inventory")
    return render(request, "dashboard/stock_form.html", {"form": form, "title": "Stock in", "lead": "Receive new units and record why they arrived."})


@staff_required
def stock_adjust(request):
    initial = {}
    variant_id = request.GET.get("variant")
    if variant_id:
        initial["variant"] = variant_id
    form = AdjustmentForm(request.POST or None, initial=None if request.method == "POST" else initial)
    if request.method == "POST" and form.is_valid():
        variant = form.cleaned_data["variant"]
        try:
            move_stock(
                variant=variant,
                quantity=form.cleaned_data["quantity"],
                movement_type=StockMovement.ADJUSTMENT,
                user=request.user,
                notes=form.cleaned_data["reason"].strip(),
            )
        except InsufficientStock as exc:
            form.add_error("quantity", f"That would take stock below zero. Only {exc.available} on hand.")
        else:
            messages.success(request, f"Adjustment recorded for {variant.sku}.")
            return redirect("dashboard:inventory")
    return render(
        request,
        "dashboard/stock_form.html",
        {"form": form, "title": "Adjust stock", "lead": "Correct a count. A reason is required and is stored in the ledger."},
    )


@staff_required
def movement_list(request):
    movements = StockMovement.objects.select_related("variant__product__category", "user", "order")
    query = request.GET.get("q", "").strip()
    movement_type = request.GET.get("type", "")
    category = request.GET.get("category", "")
    if query:
        movements = movements.filter(Q(variant__sku__icontains=query) | Q(notes__icontains=query) | Q(order__number__icontains=query))
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    if category:
        movements = movements.filter(variant__product__category__slug=category)
    return render(
        request,
        "dashboard/movements.html",
        {
            "page": _page(request, movements, 30),
            "query": query,
            "movement_type": movement_type,
            "category_slug": category,
            "types": StockMovement.TYPES,
            "categories": Category.objects.filter(is_active=True),
        },
    )
