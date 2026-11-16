from django.db import migrations


def fill_missing_category_names(apps, schema_editor):
    OrderItem = apps.get_model("orders", "OrderItem")
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")
    by_code = {category.code.upper(): category.name for category in Category.objects.all()}
    by_product = {product.name: product.category.name for product in Product.objects.select_related("category")}
    for item in OrderItem.objects.filter(category_name=""):
        name = ""
        if item.variant_id:
            name = item.variant.product.category.name
        if not name:
            prefix = (item.sku or "").split("-")[0].upper()
            name = by_code.get(prefix, "")
        if not name:
            name = by_product.get(item.product_name, "")
        if name:
            item.category_name = name
            item.save(update_fields=["category_name"])


def clear_category_names(apps, schema_editor):
    apps.get_model("orders", "OrderItem").objects.update(category_name="")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_price_and_category_snapshot"),
        ("store", "0002_price_and_category_snapshot"),
    ]

    operations = [
        migrations.RunPython(fill_missing_category_names, clear_category_names),
    ]
