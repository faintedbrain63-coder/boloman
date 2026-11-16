from django import forms

from core.forms import BootstrapFormMixin
from core.validators import validate_image_file
from orders.models import Payment


class CheckoutForm(BootstrapFormMixin, forms.Form):
    recipient_name = forms.CharField(max_length=160, label="Recipient name")
    phone = forms.CharField(max_length=40)
    address_line = forms.CharField(max_length=255, label="Street address")
    city = forms.CharField(max_length=80)
    province = forms.CharField(max_length=80)
    postal_code = forms.CharField(max_length=20, required=False)
    quantity = forms.IntegerField(min_value=1)
    customization_notes = forms.CharField(
        required=False,
        label="Customization notes",
        help_text="Name and number to print, design notes, or anything we should know.",
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
    )
    payment_method = forms.ChoiceField(
        choices=Payment.METHODS,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial=Payment.COD,
    )
    gcash_reference = forms.CharField(required=False, max_length=80, label="GCash reference number")
    screenshot = forms.ImageField(required=False, validators=[validate_image_file], label="Payment screenshot")
    save_profile = forms.BooleanField(required=False, initial=True, label="Save this as my delivery address")

    def __init__(self, *args, variant=None, **kwargs):
        self.variant = variant
        super().__init__(*args, **kwargs)

    def clean_customization_notes(self):
        return (self.cleaned_data.get("customization_notes") or "")[:500]

    def clean(self):
        data = super().clean()
        if data.get("payment_method") == Payment.GCASH:
            if not (data.get("gcash_reference") or "").strip():
                self.add_error("gcash_reference", "Enter the GCash reference number from your receipt.")
            if not data.get("screenshot"):
                self.add_error("screenshot", "Upload a screenshot of the GCash payment.")
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
