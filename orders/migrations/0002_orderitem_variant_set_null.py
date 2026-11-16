import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_initial"),
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="variant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="order_items",
                to="inventory.productvariant",
            ),
        ),
    ]
