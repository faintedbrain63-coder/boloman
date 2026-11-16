from django import forms

from core.models import ContactMessage, SiteSettings


class BootstrapFormMixin:
    """Add Bootstrap classes once fields exist, including after prefix changes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                continue
            elif isinstance(widget, forms.RadioSelect):
                continue
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            elif isinstance(widget, forms.FileInput):
                widget.attrs.setdefault("class", "form-control")
            else:
                widget.attrs.setdefault("class", "form-control")


class ContactForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
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
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "tagline": forms.Textarea(attrs={"rows": 2}),
        }
