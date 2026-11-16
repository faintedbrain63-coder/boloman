import io
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from core.models import SiteSettings
from core.studio_render import render_product_png
from inventory.models import ProductVariant, StockMovement, Supplier
from inventory.services import move_stock
from inventory.sku import build_sku
from orders.models import Order, OrderItem, OrderStatusHistory, Payment
from store.models import Category, Product, ProductImage

CATEGORIES = [
    ("Cotton Shirts", "cotton-shirts", "CTN", Category.SHIRT, "Soft cotton tees and polos, ready for names, numbers, or a front logo.", "bi-bookmark-heart", 1),
    ("Sublimated Shirts", "sublimated-shirts", "SUB", Category.SHIRT, "Full-color dye-sublimation jerseys that stay bright wash after wash.", "bi-palette", 2),
    ("Drifit Shirts", "drifit-shirts", "DRI", Category.SHIRT, "Lightweight moisture-wicking shirts for events, runs, and team days.", "bi-lightning-charge", 3),
    ("Mugs", "mugs", "MUG", Category.DRINKWARE, "Photo mugs and logo mugs for gifts, offices, and giveaways.", "bi-cup-hot", 4),
    ("Tumblers", "tumblers", "TUM", Category.DRINKWARE, "Insulated tumblers printed with a name, logo, or full wrap.", "bi-cup-straw", 5),
    ("Baseball Caps", "baseball-caps", "CAP", Category.CAP, "Embroidered and printed caps in adjustable and fitted sizes.", "bi-emoji-sunglasses", 6),
]

COLORS = [
    ("Black", "#111827"),
    ("White", "#f4f4f5"),
    ("Navy", "#1e3a5f"),
    ("Red", "#b91c1c"),
    ("Heather Gray", "#6b7280"),
]
SHIRT_SIZES = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]
CAP_SIZES = ["ADJ", "FIT"]

PRODUCTS = {
    "CTN": [
        ("Classic Cotton Tee", "classic-cotton-tee", "350.00", True, "Everyday cotton shirt for names, numbers, or a small chest logo.", "A 160gsm cotton tee we screen print or DTF. Add the name and number in the order notes and pick the ink color there too."),
        ("Heavyweight Cotton Polo", "heavyweight-cotton-polo", "550.00", False, "A polo with room for an embroidered company mark.", "Collar and placket stay neat under embroidery. Popular for uniforms and family reunions."),
        ("Cotton Round Neck", "cotton-round-neck", "399.00", False, "A slightly heavier round neck for campus and barkada prints.", "Works for one-color backs or a full front graphic. Tell us the print placement in the notes."),
    ],
    "SUB": [
        ("Full-Sublimation Jersey", "full-sublimation-jersey", "650.00", True, "Edge-to-edge color for teams that want the whole shirt designed.", "Dye-sublimated polyester. Send the design notes — names and numbers can be part of the print."),
        ("Sublimated Esports Jersey", "sublimated-esports-jersey", "699.00", False, "A cut made for squads, with room for a gamer tag.", "Light polyester that takes full-color artwork. Put the tag and number in the customization notes."),
        ("Custom Sublimated Polo", "custom-sublimated-polo", "720.00", False, "A polo covered in your pattern, not just a logo on the chest.", "Useful when the design is the shirt. Include color callouts in the notes."),
    ],
    "DRI": [
        ("Drifit Event Shirt", "drifit-event-shirt", "450.00", True, "The shirt we print for fun runs, school fairs, and company outings.", "Moisture-wicking fabric with a print that stays put when people actually sweat."),
        ("Drifit Training Tee", "drifit-training-tee", "480.00", False, "A training shirt for team names across the back.", "Add the roster name in the notes. We print one shirt per order line."),
        ("Drifit Collared Shirt", "drifit-collared-shirt", "520.00", False, "A collared drifit for staff who want a logo and a cooler fabric.", "Embroidery or DTF both work. Say which one you want in the notes."),
    ],
    "MUG": [
        ("Ceramic Photo Mug", "ceramic-photo-mug", "199.00", True, "An 11oz or 15oz mug for a photo, a quote, or both.", "Wrap or one-side print. Describe the artwork in the notes and we'll match it to the capacity you pick."),
        ("Magic Color-Changing Mug", "magic-color-mug", "249.00", False, "The print shows up when the mug is hot.", "Best for a single surprise graphic. Mention the hidden message in the notes."),
        ("Corporate Logo Mug", "corporate-logo-mug", "220.00", False, "A clean mug for the office, with your mark and nothing else.", "White or colored bodies. Put the logo placement — left, right, or wrap — in the notes."),
    ],
    "TUM": [
        ("Stainless Tumbler", "stainless-tumbler", "399.00", True, "A powder-coated tumbler for names, logos, or a full wrap.", "20oz or 30oz. Laser or UV print depending on the color you choose."),
        ("Slim Travel Tumbler", "slim-travel-tumbler", "429.00", False, "A slimmer tumbler that still fits a lid and a printed name.", "Good for giveaways. Include the name spelling exactly as it should appear."),
        ("Team Tumbler", "team-tumbler", "459.00", False, "A tumbler for squads that want the same design in two sizes.", "Tell us if the design is a wrap or a front patch."),
    ],
    "CAP": [
        ("Embroidered Dad Cap", "embroidered-dad-cap", "250.00", True, "An unstructured cap with an embroidered front mark.", "Adjustable or fitted. Describe the thread color in the notes if it isn't obvious."),
        ("Structured Baseball Cap", "structured-baseball-cap", "280.00", False, "A structured crown for schools and ball clubs.", "Embroidery holds the shape. Add the lettering — arched or straight — in the notes."),
        ("Printed Trucker Cap", "printed-trucker-cap", "230.00", False, "A foam-front trucker with a printed or patch logo.", "Say whether you want a print or a woven patch."),
    ],
}

BACKGROUNDS = {
    "CTN": (15, 118, 110),
    "SUB": (30, 64, 175),
    "DRI": (194, 65, 12),
    "MUG": (17, 24, 39),
    "TUM": (22, 101, 52),
    "CAP": (30, 58, 95),
}


def opening_qty(product_index, color_index, option_index):
    number = (product_index * 17 + color_index * 5 + option_index * 3) % 23
    if number == 0:
        return 0
    if number < 4:
        return number + 1
    return 8 + number


class Command(BaseCommand):
    help = "Load the six print-shop categories, sample products, variants, and opening stock."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete previously seeded catalog rows before loading.")
        parser.add_argument("--refresh-images", action="store_true", help="Regenerate studio placeholder images for seeded products.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()
        self._refresh_images = bool(options.get("refresh_images"))

        supplier, _created = Supplier.objects.get_or_create(
            name="Metro Print Supply Co.",
            defaults={
                "contact_person": "Rina Cruz",
                "phone": "09180001111",
                "email": "supply@metroprint.example",
                "notes": "Blanks and drinkware for Boloman's print floor.",
            },
        )
        if not SiteSettings.objects.filter(pk=1).exists():
            SiteSettings.objects.create(pk=1, **SiteSettings.defaults())

        Site.objects.update_or_create(id=1, defaults={"domain": "localhost:8000", "name": "Boloman Prints"})

        for name, slug, code, variant_type, description, icon, order in CATEGORIES:
            category, _created = Category.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "slug": slug,
                    "description": description,
                    "icon": icon,
                    "variant_type": variant_type,
                    "display_order": order,
                },
            )
            for index, spec in enumerate(PRODUCTS[code]):
                self._ensure_product(category, supplier, index, spec)

        self._ensure_staff()
        self.stdout.write(self.style.SUCCESS("Demo catalog is ready."))

    def _reset(self):
        codes = [row[2] for row in CATEGORIES]
        categories = Category.objects.filter(code__in=codes)
        products = Product.objects.filter(category__in=categories)
        variants = ProductVariant.objects.filter(product__in=products)
        order_ids = list(OrderItem.objects.filter(variant__in=variants).values_list("order_id", flat=True))
        StockMovement.objects.filter(variant__in=variants).delete()
        OrderItem.objects.filter(order_id__in=order_ids).delete()
        Payment.objects.filter(order_id__in=order_ids).delete()
        OrderStatusHistory.objects.filter(order_id__in=order_ids).delete()
        StockMovement.objects.filter(order_id__in=order_ids).delete()
        Order.objects.filter(id__in=order_ids).delete()
        variants.delete()
        ProductImage.objects.filter(product__in=products).delete()
        products.delete()
        categories.delete()
        self.stdout.write("Removed the previous demo catalog.")

    def _ensure_product(self, category, supplier, index, spec):
        name, slug, price, featured, short, description = spec
        price = Decimal(price)
        product, created = Product.objects.get_or_create(
            slug=slug,
            defaults={
                "category": category,
                "name": name,
                "short_description": short,
                "description": description,
                "cost_price": (price * Decimal("0.45")).quantize(Decimal("0.01")),
                "base_price": price,
                "is_featured": featured,
                "is_active": True,
            },
        )
        if created or not product.images.exists() or getattr(self, "_refresh_images", False):
            product.images.all().delete()
            self._make_image(product, category.code, index)
        if product.variants.exists():
            return
        if category.variant_type == Category.CAP:
            options = [(size, "") for size in CAP_SIZES]
        elif category.variant_type == Category.DRINKWARE:
            capacities = ["11oz", "15oz"] if category.code == "MUG" else ["20oz", "30oz"]
            options = [("", capacity) for capacity in capacities]
        else:
            options = [(size, "") for size in SHIRT_SIZES]
        for color_index, (color_name, color_hex) in enumerate(COLORS):
            for option_index, (size, capacity) in enumerate(options):
                selling = None
                if capacity in {"15oz", "30oz"}:
                    selling = price + (Decimal("50.00") if capacity == "15oz" else Decimal("80.00"))
                variant = ProductVariant.objects.create(
                    product=product,
                    color_name=color_name,
                    color_hex=color_hex,
                    size=size,
                    capacity=capacity,
                    sku=build_sku(product, color_name, size, capacity),
                    quantity_on_hand=0,
                    reorder_level=5,
                    cost_price=(price * Decimal("0.45")).quantize(Decimal("0.01")),
                    selling_price=selling,
                    supplier=supplier,
                    location=f"{category.code}-{index + 1:02d}",
                )
                quantity = opening_qty(index, color_index, option_index)
                if quantity:
                    move_stock(
                        variant=variant,
                        quantity=quantity,
                        movement_type=StockMovement.STOCK_IN,
                        notes="Opening stock from demo seed",
                    )

    def _make_image(self, product, code, index=0):
        studio_path = Path(settings.BASE_DIR) / "static" / "img" / "studio" / f"{product.slug}.jpg"
        if studio_path.exists():
            primary = ProductImage(product=product, alt_text=f"{product.name} studio photo", is_primary=True, sort_order=0)
            primary.image.save(f"{product.slug}-studio.jpg", ContentFile(studio_path.read_bytes()), save=True)
            blueprint_bytes = render_product_png(product.name, code, index)
            secondary = ProductImage(product=product, alt_text=f"{product.name} print blueprint", is_primary=False, sort_order=1)
            secondary.image.save(f"{product.slug}-blueprint.png", ContentFile(blueprint_bytes), save=True)
        else:
            png_bytes = render_product_png(product.name, code, index)
            photo = ProductImage(product=product, alt_text=product.name, is_primary=True, sort_order=0)
            photo.image.save(f"{product.slug}.png", ContentFile(png_bytes), save=True)

    def _ensure_staff(self):
        if not settings.DEBUG:
            return
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            return
        User.objects.create_superuser(
            username="admin",
            email="admin@boloman.ph",
            password="BolomanAdmin!2026",
        )
        self.stdout.write("Created staff login admin@boloman.ph / BolomanAdmin!2026 — change this password.")
