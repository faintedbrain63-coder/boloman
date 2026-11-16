from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory
from django.utils.text import slugify

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
            "description",
            "cost_price",
            "base_price",
            "is_featured",
            "is_active",
        ]
        labels = {
            "cost_price": "Cost price",
            "base_price": "Selling price",
        }
        help_texts = {
            "cost_price": "What you pay when you buy this product. Inventory value uses this cost.",
            "base_price": "What the customer pays when you sell this product. Variants use it unless a color or size has its own selling price.",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Cotton Round Neck"}),
            "slug": forms.TextInput(attrs={"placeholder": "cotton-round-neck"}),
            "description": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Fabric, print area, and what the customer should know"}
            ),
            "cost_price": forms.NumberInput(attrs={"placeholder": "120.00", "step": "0.01"}),
            "base_price": forms.NumberInput(attrs={"placeholder": "280.00", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = Category.objects.filter(is_active=True)
        if self.instance.pk and self.instance.category_id:
            categories = Category.objects.filter(Q(is_active=True) | Q(pk=self.instance.category_id))
        self.fields["category"].queryset = categories.order_by("display_order", "name")
        self.fields["cost_price"].required = True
        self.fields["base_price"].required = True
        if not self.is_bound and not self.instance.pk:
            self.initial["cost_price"] = ""

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        if not slug:
            return ""
        slug = slugify(slug)
        if not slug:
            raise forms.ValidationError("Use letters or numbers in the address.")
        taken = Product.objects.filter(slug=slug)
        if self.instance.pk:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("That address is already used by another product.")
        return slug


class ProductImageForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "is_primary"]
        widgets = {"alt_text": forms.TextInput(attrs={"placeholder": "e.g. Front view, black shirt"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].required = False
        self.fields["image"].widget = forms.FileInput(attrs={"class": "form-control"})
        self.fields["alt_text"].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned
        if not self.instance.pk and not cleaned.get("image"):
            self.add_error("image", "Upload a photo, or leave this row blank.")
        return cleaned


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
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Cotton Shirts"}),
            "slug": forms.TextInput(attrs={"placeholder": "cotton-shirts"}),
            "code": forms.TextInput(attrs={"placeholder": "CTN"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "What belongs in this category"}),
            "icon": forms.TextInput(attrs={"placeholder": "bi-tag"}),
            "display_order": forms.NumberInput(attrs={"placeholder": "0"}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        if not slug:
            return ""
        slug = slugify(slug)
        if not slug:
            raise forms.ValidationError("Use letters or numbers in the address.")
        taken = Category.objects.filter(slug=slug)
        if self.instance.pk:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("That address is already used by another category.")
        return slug

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip().upper()
        if not code:
            raise forms.ValidationError("Enter a short SKU code.")
        if not code.isalnum():
            raise forms.ValidationError("Use letters and numbers only, for example CTN.")
        taken = Category.objects.filter(code__iexact=code)
        if self.instance.pk:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("That SKU code is already used.")
        if self.instance.pk and self.instance.code != code and self.instance.products.exists():
            raise forms.ValidationError(
                "This code is already printed on existing SKUs. Add a new category instead of changing it."
            )
        return code

    def clean(self):
        data = super().clean()
        variant_type = data.get("variant_type")
        if (
            self.instance.pk
            and variant_type
            and variant_type != self.instance.variant_type
            and self.instance.products.exists()
        ):
            self.add_error(
                "variant_type",
                "Products already use this sizing rule. Create a new category to use a different one.",
            )
        return data


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
        self.fields["cost_price"].required = False
        self.fields["selling_price"].required = False
        if self.product is not None:
            self.fields["cost_price"].help_text = (
                f"Leave blank to use the product cost of ₱{self.product.cost_price:,.2f}."
            )
            self.fields["selling_price"].help_text = (
                f"Leave blank to use the product selling price of ₱{self.product.base_price:,.2f}."
            )
        self.fields["color_name"].widget.attrs["placeholder"] = "e.g. Black"
        self.fields["location"].widget.attrs["placeholder"] = "e.g. A-12"
        self.fields["cost_price"].widget.attrs["placeholder"] = "Leave blank to use the product cost"
        self.fields["selling_price"].widget.attrs["placeholder"] = "Leave blank to use the product selling price"
        self.fields["reorder_level"].widget.attrs["placeholder"] = "5"
        self.fields["opening_quantity"].widget.attrs["placeholder"] = "0"
        self.fields["reason"].widget.attrs["placeholder"] = "Why this stock is being added"
        self.apply_bootstrap()
        if self.instance.pk:
            self.fields["opening_quantity"].widget = forms.HiddenInput()
            self.fields["reason"].widget = forms.HiddenInput()

    def clean(self):
        data = super().clean()
        variant_type = self.product.category.variant_type
        if variant_type == Category.DRINKWARE:
            data["size"] = ""
            allowed = MUG_CAPACITIES if self.product.category.code == "MUG" else TUMBLER_CAPACITIES
            if not data.get("capacity"):
                self.add_error("capacity", "Choose a capacity.")
            elif data["capacity"] not in allowed:
                self.add_error("capacity", "Choose a valid capacity.")
        else:
            data["capacity"] = ""
            allowed = SHIRT_SIZES if variant_type == Category.SHIRT else CAP_SIZES
            if not data.get("size"):
                self.add_error("size", "Choose a size.")
            elif data["size"] not in allowed:
                self.add_error("size", "Choose a valid size.")
        opening = data.get("opening_quantity") or 0
        if not self.instance.pk and opening > 0 and not (data.get("reason") or "").strip():
            self.add_error("reason", "Enter a reason for the opening stock.")
        color = " ".join((data.get("color_name") or "").split())
        if color:
            data["color_name"] = color.title()
        if color and self.product is not None:
            taken = ProductVariant.objects.filter(
                product=self.product,
                color_name__iexact=data["color_name"],
                size=data.get("size") or "",
                capacity=data.get("capacity") or "",
            )
            if self.instance.pk:
                taken = taken.exclude(pk=self.instance.pk)
            if taken.exists():
                self.add_error("color_name", "This color and option already exists for this product.")
        return data


class VariantMatrixForm(BootstrapFormMixin, forms.Form):
    colors = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Black, #111827\nWhite, #ffffff"}),
        help_text="One color per line: Black, #111827",
    )
    sizes = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)
    capacities = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)
    quantity = forms.IntegerField(min_value=0, initial=10, widget=forms.NumberInput(attrs={"placeholder": "10"}))
    reorder_level = forms.IntegerField(min_value=0, initial=5, widget=forms.NumberInput(attrs={"placeholder": "5"}))
    cost_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        label="Cost price",
        help_text="Leave blank to use the product cost price.",
        widget=forms.NumberInput(attrs={"placeholder": "Leave blank to use the product cost", "step": "0.01"}),
    )
    selling_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        label="Selling price",
        help_text="Leave blank to use the product selling price.",
        widget=forms.NumberInput(attrs={"placeholder": "Leave blank to use the product selling price", "step": "0.01"}),
    )
    location = forms.CharField(
        max_length=40, required=False, widget=forms.TextInput(attrs={"placeholder": "e.g. A-12"})
    )
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), required=False)
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Opening stock for these colors and sizes"}),
        required=False,
    )

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
        self.fields["cost_price"].help_text = f"Leave blank to use the product cost of ₱{product.cost_price:,.2f}."
        self.fields["selling_price"].help_text = (
            f"Leave blank to use the product selling price of ₱{product.base_price:,.2f}."
        )
        self.apply_bootstrap()

    def clean(self):
        data = super().clean()
        colors = []
        seen = set()
        for line in (data.get("colors") or "").splitlines():
            text = line.strip()
            if not text:
                continue
            if "," in text:
                name, hex_value = text.split(",", 1)
            else:
                name, hex_value = text, "#111827"
            name = " ".join(name.split()).title()
            hex_value = hex_value.strip() or "#111827"
            if not name:
                continue
            if not hex_value.startswith("#"):
                hex_value = f"#{hex_value}"
            if len(hex_value) not in {4, 7}:
                raise forms.ValidationError(f"“{hex_value}” is not a hex color. Use #111827.")
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
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
    quantity = forms.IntegerField(
        min_value=1, label="Quantity to add", widget=forms.NumberInput(attrs={"placeholder": "10"})
    )
    unit_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        label="Cost price for this delivery",
        help_text="What you paid per unit. Leave blank to keep the cost already on this SKU.",
        widget=forms.NumberInput(attrs={"placeholder": "120.00", "step": "0.01"}),
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Received from the supplier"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["variant"].queryset = ProductVariant.objects.select_related("product").order_by("sku")
        self.fields["variant"].empty_label = "Select a variant"
        self.fields["variant"].widget.attrs["data-search"] = "on"
        self.fields["variant"].widget.attrs["data-search-placeholder"] = "Search SKU, product, or color"


class AdjustmentForm(BootstrapFormMixin, forms.Form):
    variant = VariantChoiceField(queryset=ProductVariant.objects.none())
    quantity = forms.IntegerField(
        label="Quantity change",
        help_text="Positive adds stock. Negative removes stock. The balance cannot go below zero.",
        widget=forms.NumberInput(attrs={"placeholder": "+5 or -2"}),
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Count correction after a stock take"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["variant"].queryset = ProductVariant.objects.select_related("product").order_by("sku")
        self.fields["variant"].empty_label = "Select a variant"
        self.fields["variant"].widget.attrs["data-search"] = "on"
        self.fields["variant"].widget.attrs["data-search-placeholder"] = "Search SKU, product, or color"

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity == 0:
            raise forms.ValidationError("Enter a quantity other than zero.")
        return quantity


class OrderStatusForm(BootstrapFormMixin, forms.Form):
    status = forms.ChoiceField(choices=Order.STATUS_CHOICES)
    note = forms.CharField(
        max_length=255,
        required=False,
        label="Note for the history",
        widget=forms.TextInput(attrs={"placeholder": "Optional note for the order history"}),
    )
