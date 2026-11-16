from django import forms

from core.models import ContactMessage, SiteSettings


def style_form(form):
    """Add Bootstrap classes and a placeholder to every text-like field."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect, forms.HiddenInput)):
            continue
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            widget.attrs.setdefault("class", "form-select")
        elif isinstance(widget, (forms.FileInput, forms.ClearableFileInput)):
            widget.attrs.setdefault("class", "form-control")
        else:
            widget.attrs.setdefault("class", "form-control")
            if widget.attrs.get("type") == "color" or widget.attrs.get("placeholder"):
                continue
            label = str(field.label or "").strip()
            if label:
                widget.attrs["placeholder"] = label


class BootstrapFormMixin:
    """Add Bootstrap classes once fields exist, including after prefix changes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def apply_bootstrap(self):
        style_form(self)


class ContactForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Juan Dela Cruz"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@email.com"}),
            "phone": forms.TextInput(attrs={"placeholder": "09XX XXX XXXX"}),
            "subject": forms.TextInput(attrs={"placeholder": "Team jerseys for 30 players"}),
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Quantity, sizes, and the date you need them"}),
        }
        labels = {
            "phone": "Phone (optional)",
        }


class SiteSettingsForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "business_name",
            "tagline",
            "phone",
            "email",
            "address",
            "map_embed_url",
            "gcash_number",
            "gcash_account_name",
            "gcash_qr",
        ]
        labels = {"gcash_qr": "GCash QR code"}
        help_texts = {
            "gcash_qr": "JPEG, PNG, or WebP from your GCash app, up to 5 MB. Customers scan this at checkout.",
        }
        widgets = {
            "business_name": forms.TextInput(attrs={"placeholder": "Boloman Prints"}),
            "tagline": forms.Textarea(attrs={"rows": 2, "placeholder": "Custom shirts, mugs, and caps"}),
            "phone": forms.TextInput(attrs={"placeholder": "09XX XXX XXXX"}),
            "email": forms.EmailInput(attrs={"placeholder": "hello@boloman.ph"}),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Studio street, city, province"}),
            "map_embed_url": forms.URLInput(attrs={"placeholder": "https://maps.google.com/…"}),
            "gcash_number": forms.TextInput(attrs={"placeholder": "09XX XXX XXXX"}),
            "gcash_account_name": forms.TextInput(attrs={"placeholder": "Name on the GCash account"}),
            "gcash_qr": forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def clean_gcash_number(self):
        raw = (self.cleaned_data.get("gcash_number") or "").strip()
        compact = raw.replace(" ", "").replace("-", "")
        if compact.startswith("+63") and len(compact) == 13 and compact[1:].isdigit():
            compact = "0" + compact[3:]
        if not (len(compact) == 11 and compact.startswith("09") and compact.isdigit()):
            raise forms.ValidationError("Enter an 11-digit PH mobile number starting with 09 (or +639).")
        return compact
