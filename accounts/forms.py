from django import forms

from core.forms import BootstrapFormMixin


class ProfileForm(BootstrapFormMixin, forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=40)
    address_line = forms.CharField(label="Street address", max_length=255)
    city = forms.CharField(max_length=80)
    province = forms.CharField(max_length=80)
    postal_code = forms.CharField(max_length=20, required=False)
