from django import forms
from django.forms import inlineformset_factory

from core.forms import BootstrapFormMixin
from inventory.constants import CAP_SIZES, MUG_CAPACITIES, SHIRT_SIZES, TUMBLER_CAPACITIES, size_label
from inventory.models import ProductVariant, Supplier
from orders.models import Order
from store.models import Category, Product, ProductImage


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "category",
            "name",
            "slug",
            "short_description",
            "description",
            "base_price",
            "is_featured",
            "is_active",
        ]
        widgets = {
            "short_description": forms.Textarea(attrs={"rows": 2}),
            "description": forms.Textarea(attrs={"rows": 6}),
        }


class ProductImageForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "sort_order", "is_primary"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].required = False
        self.fields["alt_text"].required = False


ImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=1,
    can_delete=True,
)


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "code", "description", "icon", "variant_type", "display_order", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class VariantForm(BootstrapFormMixin, forms.ModelForm):
    opening_quantity = forms.IntegerField(
        min_value=0,
        initial=0,
        required=False,
        label="Opening quantity",
        help_text="Only used when you create the variant. Later changes go through stock in or adjustment.",
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Required when the opening quantity is greater than zero.",
    )

    class Meta:
        model = ProductVariant
        fields = [
            "color_name",
            "color_hex",
            "size",
            "capacity",
            "selling_price",
            "cost_price",
            "reorder_level",
            "supplier",
            "location",
            "is_active",
        ]

    def __init__(self, *args, product=None, **kwargs):
        self.product = product or getattr(kwargs.get("instance"), "product", None)
        super().__init__(*args, **kwargs)
        self.fields["color_hex"].widget = forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"})
        variant_type = self.product.category.variant_type if self.product else Category.SHIRT
        if variant_type == Category.SHIRT:
            choices = [(size, size_label(size)) for size in SHIRT_SIZES]
            self.fields["size"].widget = forms.Select(choices=choices)
            self.fields["capacity"].widget = forms.HiddenInput()
        elif variant_type == Category.CAP:
            choices = [(size, size_label(size)) for size in CAP_SIZES]
            self.fields["size"].widget = forms.Select(choices=choices)
            self.fields["capacity"].widget = forms.HiddenInput()
        else:
            capacities = MUG_CAPACITIES if self.product and self.product.category.code == "MUG" else TUMBLER_CAPACITIES
            self.fields["capacity"].widget = forms.Select(choices=[(item, item) for item in capacities])
            self.fields["size"].widget = forms.HiddenInput()
        self.fields["selling_price"].required = False
        self.apply_bootstrap()
        if self.instance.pk:
            self.fields["opening_quantity"].widget = forms.HiddenInput()
            self.fields["reason"].widget = forms.HiddenInput()

    def clean(self):
        data = super().clean()
        variant_type = self.product.category.variant_type
        if variant_type == Category.DRINKWARE:
            data["size"] = ""
            if not data.get("capacity"):
                self.add_error("capacity", "Choose a capacity.")
        else:
            data["capacity"] = ""
            if not data.get("size"):
                self.add_error("size", "Choose a size.")
        opening = data.get("opening_quantity") or 0
        if not self.instance.pk and opening > 0 and not (data.get("reason") or "").strip():
            self.add_error("reason", "Enter a reason for the opening stock.")
        return data


class VariantMatrixForm(BootstrapFormMixin, forms.Form):
    colors = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="One color per line: Black, #111827",
    )
    sizes = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)
    capacities = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)
    quantity = forms.IntegerField(min_value=0, initial=10)
    reorder_level = forms.IntegerField(min_value=0, initial=5)
    cost_price = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    selling_price = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    location = forms.CharField(max_length=40, required=False)
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), required=False)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, product=None, **kwargs):
        self.product = product
        super().__init__(*args, **kwargs)
        variant_type = product.category.variant_type
        if variant_type == Category.SHIRT:
            self.fields["sizes"].choices = [(size, size_label(size)) for size in SHIRT_SIZES]
            self.fields["capacities"].widget = forms.MultipleHiddenInput()
        elif variant_type == Category.CAP:
            self.fields["sizes"].choices = [(size, size_label(size)) for size in CAP_SIZES]
            self.fields["capacities"].widget = forms.MultipleHiddenInput()
        else:
            capacities = MUG_CAPACITIES if product.category.code == "MUG" else TUMBLER_CAPACITIES
            self.fields["capacities"].choices = [(item, item) for item in capacities]
            self.fields["sizes"].widget = forms.MultipleHiddenInput()
        self.apply_bootstrap()

    def clean(self):
        data = super().clean()
        colors = []
        for line in (data.get("colors") or "").splitlines():
            text = line.strip()
            if not text:
                continue
            if "," in text:
                name, hex_value = text.split(",", 1)
            else:
                name, hex_value = text, "#111827"
            name = name.strip()
            hex_value = hex_value.strip() or "#111827"
            if not name:
                continue
            if not hex_value.startswith("#") or len(hex_value) not in {4, 7}:
                raise forms.ValidationError(f"“{hex_value}” is not a hex color. Use #111827.")
            colors.append((name, hex_value))
        if not colors:
            self.add_error("colors", "Add at least one color.")
        data["parsed_colors"] = colors
        variant_type = self.product.category.variant_type
        if variant_type == Category.DRINKWARE and not data.get("capacities"):
            self.add_error("capacities", "Pick at least one capacity.")
        if variant_type != Category.DRINKWARE and not data.get("sizes"):
            self.add_error("sizes", "Pick at least one size.")
        if (data.get("quantity") or 0) > 0 and not (data.get("reason") or "").strip():
            self.add_error("reason", "A reason is required when you add stock.")
        return data


class VariantChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.sku} · {obj.product.name} · {obj.option_label} · {obj.quantity_on_hand} on hand"


class StockInForm(BootstrapFormMixin, forms.Form):
    variant = VariantChoiceField(queryset=ProductVariant.objects.none())
    quantity = forms.IntegerField(min_value=1, label="Quantity to add")
    unit_cost = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, label="New cost price")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["variant"].queryset = ProductVariant.objects.select_related("product").order_by("sku")


class AdjustmentForm(BootstrapFormMixin, forms.Form):
    variant = VariantChoiceField(queryset=ProductVariant.objects.none())
    quantity = forms.IntegerField(
        label="Quantity change",
        help_text="Positive adds stock. Negative removes stock. The balance cannot go below zero.",
    )
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["variant"].queryset = ProductVariant.objects.select_related("product").order_by("sku")

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity == 0:
            raise forms.ValidationError("Enter a quantity other than zero.")
        return quantity


class OrderStatusForm(BootstrapFormMixin, forms.Form):
    status = forms.ChoiceField(choices=Order.STATUS_CHOICES)
    note = forms.CharField(max_length=255, required=False, label="Note for the history")
