from decouple import config
from django.core.files.storage import default_storage
from django.db import models

from core.validators import validate_image_file


class SiteSettings(models.Model):
    """Single row of shop contact and payment details, editable by staff."""

    business_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    address = models.TextField()
    map_embed_url = models.URLField(blank=True)
    gcash_number = models.CharField(max_length=40)
    gcash_account_name = models.CharField(max_length=120)
    gcash_qr = models.ImageField(
        upload_to="payments/gcash-qr/",
        blank=True,
        validators=[validate_image_file],
        verbose_name="GCash QR code",
        help_text="Upload the QR code from your GCash app. Customers scan it when they pay.",
    )
    tagline = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        self.pk = 1
        previous = type(self).objects.filter(pk=1).first()
        previous_name = previous.gcash_qr.name if previous and previous.gcash_qr else ""
        super().save(*args, **kwargs)
        current_name = self.gcash_qr.name if self.gcash_qr else ""
        if previous_name and previous_name != current_name:
            default_storage.delete(previous_name)

    @classmethod
    def defaults(cls):
        return {
            "business_name": config("BUSINESS_NAME", default="Boloman Prints"),
            "phone": config("BUSINESS_PHONE", default=""),
            "email": config("BUSINESS_EMAIL", default="hello@boloman.ph"),
            "address": config("BUSINESS_ADDRESS", default=""),
            "gcash_number": config("GCASH_NUMBER", default=""),
            "gcash_account_name": config("GCASH_ACCOUNT_NAME", default=""),
            "tagline": "Custom shirts, mugs, tumblers, and caps — printed for teams, events, and brands.",
        }

    @classmethod
    def load(cls):
        existing = cls.objects.filter(pk=1).first()
        if existing:
            return existing
        return cls.objects.create(pk=1, **cls.defaults())


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=160)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"
