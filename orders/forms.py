from django import forms
from django.core.exceptions import ValidationError

from core.forms import BootstrapFormMixin
from core.models import SiteSettings
from core.validators import validate_image_file
from orders.models import Order, Payment


class CheckoutForm(BootstrapFormMixin, forms.Form):
    recipient_name = forms.CharField(
        max_length=160,
        label="Recipient name",
        widget=forms.TextInput(attrs={"placeholder": "Juan Dela Cruz"}),
    )
    phone = forms.CharField(max_length=40, widget=forms.TextInput(attrs={"placeholder": "09XX XXX XXXX"}))
    address_line = forms.CharField(
        max_length=255,
        label="Street address",
        widget=forms.TextInput(attrs={"placeholder": "123 Mabini Street"}),
    )
    city = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"placeholder": "Quezon City"}))
    province = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"placeholder": "Metro Manila"}))
    postal_code = forms.CharField(
        max_length=20, required=False, widget=forms.TextInput(attrs={"placeholder": "1100"})
    )
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"placeholder": "1"}))
    customization_notes = forms.CharField(
        required=False,
        label="Customization notes",
        help_text="Name and number to print, design notes, or anything we should know.",
        widget=forms.Textarea(
            attrs={"rows": 3, "maxlength": 500, "placeholder": "Name, jersey number, and where to print"}
        ),
    )
    payment_method = forms.ChoiceField(
        choices=Payment.METHODS,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial=Payment.COD,
    )
    gcash_reference = forms.CharField(
        required=False,
        max_length=80,
        label="GCash reference number",
        widget=forms.TextInput(attrs={"placeholder": "Reference number on the receipt"}),
    )
    screenshot = forms.FileField(
        required=False,
        label="Payment screenshot",
        widget=forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
    )
    save_profile = forms.BooleanField(required=False, initial=True, label="Save this as my delivery address")

    def __init__(self, *args, variant=None, **kwargs):
        self.variant = variant
        super().__init__(*args, **kwargs)

    def clean_customization_notes(self):
        return (self.cleaned_data.get("customization_notes") or "")[:500]

    def clean(self):
        data = super().clean()
        if data.get("payment_method") == Payment.GCASH:
            settings_row = SiteSettings.load()
            if not (settings_row.gcash_number or "").strip() and not settings_row.gcash_qr:
                self.add_error(
                    "payment_method",
                    "GCash is not set up right now. Choose Cash on Delivery or message the shop.",
                )
            ref = " ".join((data.get("gcash_reference") or "").split())
            if not ref:
                self.add_error("gcash_reference", "Enter the GCash reference number from your receipt.")
            elif sum(ch.isalnum() for ch in ref) < 4 or not all(ch.isalnum() or ch in " -#" for ch in ref):
                self.add_error("gcash_reference", "Enter a valid GCash reference number from your receipt.")
            elif (
                Payment.objects.filter(method=Payment.GCASH, gcash_reference__iexact=ref)
                .exclude(order__status=Order.CANCELLED)
                .exists()
            ):
                self.add_error(
                    "gcash_reference",
                    "This GCash reference number has already been used on another order.",
                )
            else:
                data["gcash_reference"] = ref

            uploaded = data.get("screenshot")
            if not uploaded:
                self.add_error("screenshot", "Upload a screenshot of the GCash payment.")
            else:
                try:
                    validate_image_file(uploaded)
                except ValidationError as exc:
                    self.add_error("screenshot", exc)
        else:
            data["gcash_reference"] = ""
            data["screenshot"] = None
            self.errors.pop("gcash_reference", None)
            self.errors.pop("screenshot", None)
        quantity = data.get("quantity")
        if self.variant and quantity and quantity > self.variant.quantity_on_hand:
            self.add_error("quantity", f"Only {self.variant.quantity_on_hand} left for this option.")
        return data

    @property
    def delivery_address(self):
        data = self.cleaned_data
        return ", ".join(
            part
            for part in [data.get("address_line"), data.get("city"), data.get("province"), data.get("postal_code")]
            if part
        )
