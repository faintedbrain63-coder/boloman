from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from .models import Product


@receiver(pre_delete, sender=Product)
def remember_product_files(sender, instance, **kwargs):
    instance._media_paths = [
        image.image.name for image in instance.images.all() if image.image and image.image.name
    ]


@receiver(post_delete, sender=Product)
def remove_product_files(sender, instance, **kwargs):
    paths = list(getattr(instance, "_media_paths", []))

    def purge():
        for path in paths:
            if default_storage.exists(path):
                default_storage.delete(path)

    transaction.on_commit(purge)
