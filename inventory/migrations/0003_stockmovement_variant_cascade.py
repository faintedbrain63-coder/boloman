import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockmovement",
            name="variant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="movements",
                to="inventory.productvariant",
            ),
        ),
    ]
