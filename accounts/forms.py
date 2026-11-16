from django import forms

from allauth.account.forms import (
    ChangePasswordForm,
    LoginForm,
    ResetPasswordForm,
    ResetPasswordKeyForm,
    SetPasswordForm,
    SignupForm,
)

from core.forms import BootstrapFormMixin, style_form


class ProfileForm(BootstrapFormMixin, forms.Form):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"placeholder": "Juan"}))
    last_name = forms.CharField(
        max_length=150, required=False, widget=forms.TextInput(attrs={"placeholder": "Dela Cruz"})
    )
    phone = forms.CharField(max_length=40, widget=forms.TextInput(attrs={"placeholder": "09XX XXX XXXX"}))
    address_line = forms.CharField(
        label="Street address",
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "123 Mabini Street"}),
    )
    city = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"placeholder": "Quezon City"}))
    province = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"placeholder": "Metro Manila"}))
    postal_code = forms.CharField(
        max_length=20, required=False, widget=forms.TextInput(attrs={"placeholder": "1100"})
    )


class _PlaceholderAccountForm:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)


class BolomanLoginForm(_PlaceholderAccountForm, LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs["placeholder"] = "name@email.com"
        self.fields["password"].widget.attrs["placeholder"] = "Enter your password"


class BolomanSignupForm(_PlaceholderAccountForm, SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["placeholder"] = "name@email.com"
        self.fields["password1"].widget.attrs["placeholder"] = "Create a password"
        self.fields["password2"].widget.attrs["placeholder"] = "Repeat the password"


class BolomanResetPasswordForm(_PlaceholderAccountForm, ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "email" in self.fields:
            self.fields["email"].widget.attrs["placeholder"] = "name@email.com"


class BolomanResetPasswordKeyForm(_PlaceholderAccountForm, ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs["placeholder"] = "Create a new password"
        self.fields["password2"].widget.attrs["placeholder"] = "Repeat the new password"


class BolomanChangePasswordForm(_PlaceholderAccountForm, ChangePasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["oldpassword"].widget.attrs["placeholder"] = "Current password"
        self.fields["password1"].widget.attrs["placeholder"] = "Create a new password"
        self.fields["password2"].widget.attrs["placeholder"] = "Repeat the new password"


class BolomanSetPasswordForm(_PlaceholderAccountForm, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs["placeholder"] = "Create a password"
        self.fields["password2"].widget.attrs["placeholder"] = "Repeat the password"
