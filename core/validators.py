"""Shared upload checks for product photos and payment screenshots."""

import os

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_image_file(uploaded):
    if uploaded.size > MAX_IMAGE_BYTES:
        raise ValidationError("Image must be 5 MB or smaller.")

    extension = os.path.splitext(uploaded.name or "")[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError("Upload a JPEG, PNG, or WebP image.")

    content_type = getattr(uploaded, "content_type", "") or ""
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Upload a JPEG, PNG, or WebP image.")

    try:
        uploaded.seek(0)
        image = Image.open(uploaded)
        image.verify()
        uploaded.seek(0)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("That file is not a valid image.") from exc
