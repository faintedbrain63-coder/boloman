from collections import Counter

from django.db import migrations


def backfill_product_cost(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    for product in Product.objects.all():
        costs = [cost for cost in product.variants.values_list("cost_price", flat=True) if cost is not None]
        if not costs:
            continue
        product.cost_price = Counter(costs).most_common(1)[0][0]
        product.save(update_fields=["cost_price"])


def clear_product_cost(apps, schema_editor):
    apps.get_model("store", "Product").objects.update(cost_price=0)


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0003_product_cost_and_selling_prices"),
        ("inventory", "0005_product_cost_and_selling_prices"),
    ]

    operations = [
        migrations.RunPython(backfill_product_cost, clear_product_cost),
    ]
