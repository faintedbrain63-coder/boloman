from django.conf import settings
from django.db import models


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=40, blank=True)
    address_line = models.CharField("Street address", max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    province = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email or self.user.username

    @property
    def full_address(self):
        parts = [self.address_line, self.city, self.province, self.postal_code]
        return ", ".join(part for part in parts if part)
