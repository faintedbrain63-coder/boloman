"""Procedural studio-lit product renderer using Pillow lighting & blur masks."""

import io
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


def _font(size, bold=True):
    paths = (
        ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]
        if bold
        else ["/System/Library/Fonts/Helvetica.ttc"]
    )
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _studio_backdrop(size=1000):
    """Create a realistic radial studio cyclorama background."""
    base = Image.new("RGBA", (size, size), (230, 236, 244, 255))
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((80, 50, size - 80, size - 130), fill=(255, 255, 255, 245))
    glow = glow.filter(ImageFilter.GaussianBlur(95))
    base = Image.alpha_composite(base, glow)

    # Subtle floor horizon plane
    floor = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(floor)
    fdraw.rectangle((0, int(size * 0.77), size, size), fill=(214, 222, 233, 120))
    floor = floor.filter(ImageFilter.GaussianBlur(28))
    return Image.alpha_composite(base, floor)


def _lit_fill(size, base_rgb, cylindrical=False):
    """Generate a smooth directional or cylindrical studio-lit color layer."""
    r, g, b = base_rgb
    grad = Image.new("RGBA", (size, size), (r, g, b, 255))
    light = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(light)

    if cylindrical:
        # Cylindrical highlight left-center, core shadow right
        ldraw.rectangle((300, 80, 440, 900), fill=(255, 255, 255, 88))
        ldraw.rectangle((560, 80, 740, 900), fill=(0, 8, 20, 95))
        light = light.filter(ImageFilter.GaussianBlur(46))
    else:
        # Top-left softbox key light + bottom-right falloff
        ldraw.ellipse((140, 80, 620, 580), fill=(255, 255, 255, 68))
        ldraw.ellipse((460, 460, 920, 920), fill=(4, 10, 24, 85))
        light = light.filter(ImageFilter.GaussianBlur(75))

    return Image.alpha_composite(grad, light)


def _apply_drape_folds(layer, coords_list):
    """Add soft realistic fabric drape shadows."""
    folds = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(folds)
    for x0, y0, x1, y1, width, alpha in coords_list:
        d.line([(x0, y0), (x1, y1)], fill=(6, 12, 24, alpha), width=width)
    folds = folds.filter(ImageFilter.GaussianBlur(18))
    return Image.alpha_composite(layer, folds)


def render_product_png(product_name, category_code, variant_index=0):
    S = 1000
    palettes = {
        "CTN": [(17, 94, 89), (23, 32, 48), (136, 28, 36)],
        "SUB": [(24, 68, 178), (88, 28, 135), (13, 110, 102)],
        "DRI": [(194, 65, 12), (14, 116, 144), (22, 101, 52)],
        "MUG": [(20, 28, 44), (15, 118, 110), (146, 52, 24)],
        "TUM": [(19, 78, 74), (30, 58, 138), (39, 50, 66)],
        "CAP": [(26, 54, 93), (20, 27, 41), (124, 45, 18)],
    }
    rgb = palettes.get(category_code, [(17, 94, 89)])[variant_index % 3]
    canvas = _studio_backdrop(S)

    # Contact + ambient floor shadow
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse((240, 770, 760, 845), fill=(15, 23, 42, 95))
    sdraw.ellipse((300, 785, 700, 825), fill=(15, 23, 42, 115))
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(28)))

    mask = Image.new("L", (S, S), 0)
    mdraw = ImageDraw.Draw(mask)

    if category_code in {"CTN", "SUB", "DRI"}:
        # Tailored garment silhouette with curved hem & angled sleeves
        body_pts = [
            (328, 185), (410, 152), (500, 178), (590, 152), (672, 185),
            (815, 335), (728, 422), (662, 366),
            (668, 768), (500, 784), (332, 768),
            (338, 366), (272, 422), (185, 335),
        ]
        mdraw.polygon(body_pts, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(1.5))

        lit = _lit_fill(S, rgb, cylindrical=False)
        lit = _apply_drape_folds(
            lit,
            [
                (365, 350, 355, 745, 26, 58),
                (635, 350, 645, 745, 28, 68),
                (455, 420, 445, 755, 18, 34),
                (555, 380, 568, 755, 20, 42),
                (338, 355, 290, 405, 22, 65),
                (662, 355, 710, 405, 22, 72),
            ],
        )

        detail = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        dd = ImageDraw.Draw(detail)

        # Inner neck cavity + collar rib
        dd.pieslice((406, 128, 594, 232), start=0, end=180, fill=(10, 15, 26, 220))
        dd.arc((402, 124, 598, 238), start=8, end=172, fill=(255, 255, 255, 95), width=10)

        # Polo placket for polo items
        if "polo" in product_name.lower() or "collared" in product_name.lower():
            dd.rounded_rectangle((482, 220, 518, 365), radius=8, fill=(10, 15, 26, 95))
            for by in (252, 296, 338):
                dd.ellipse((494, by - 6, 506, by + 6), fill=(241, 245, 249, 210))
            dd.polygon([(404, 154), (478, 236), (434, 254), (376, 190)], fill=(255, 255, 255, 48))
            dd.polygon([(596, 154), (522, 236), (566, 254), (624, 190)], fill=(0, 0, 0, 48))

        # Sublimation athletic diagonal graphics
        if category_code == "SUB":
            dd.polygon([(332, 520), (668, 390), (668, 455), (332, 585)], fill=(56, 189, 248, 125))
            dd.polygon([(332, 600), (668, 470), (668, 505), (332, 635)], fill=(249, 115, 22, 165))

        # Crisp chest print graphic
        dd.rounded_rectangle((408, 305, 592, 450), radius=18, fill=(255, 255, 255, 26), outline=(255, 255, 255, 130), width=3)
        dd.rounded_rectangle((442, 336, 558, 350), radius=7, fill=(251, 146, 60, 235))
        dd.text((500, 386), "BOLOMAN", fill=(255, 255, 255, 245), font=_font(28, True), anchor="mm")
        dd.text((500, 418), "CUSTOM STUDIO", fill=(226, 232, 240, 210), font=_font(16, False), anchor="mm")

        lit = Image.alpha_composite(lit, detail)
        garment = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        garment.paste(lit, (0, 0), mask)

        # Drop shadow behind garment
        drop = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        drop.paste((15, 23, 42, 75), (0, 18), mask)
        canvas = Image.alpha_composite(canvas, drop.filter(ImageFilter.GaussianBlur(24)))
        canvas = Image.alpha_composite(canvas, garment)

    elif category_code == "MUG":
        # Glossy 3D Ceramic Mug
        handle = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        hd = ImageDraw.Draw(handle)
        hd.arc((545, 315, 765, 645), start=265, end=95, fill=(*rgb, 255), width=48)
        hd.arc((555, 328, 752, 632), start=275, end=85, fill=(255, 255, 255, 70), width=10)
        canvas = Image.alpha_composite(canvas, handle)

        mdraw.rounded_rectangle((265, 235, 645, 760), radius=54, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(1.2))
        lit = _lit_fill(S, rgb, cylindrical=True)

        detail = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        dd = ImageDraw.Draw(detail)
        # Glossy vertical ceramic highlight
        spec = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(spec).rounded_rectangle((312, 265, 348, 725), radius=16, fill=(255, 255, 255, 115))
        lit = Image.alpha_composite(lit, spec.filter(ImageFilter.GaussianBlur(8)))

        # Crisp wrap print band
        dd.rounded_rectangle((330, 365, 588, 595), radius=22, fill=(255, 255, 255, 238))
        dd.rounded_rectangle((365, 415, 553, 431), radius=8, fill=(*rgb, 255))
        dd.text((459, 476), "STUDIO MUG", fill=(15, 23, 42, 245), font=_font(28, True), anchor="mm")
        dd.text((459, 516), "FULL-WRAP PRINT", fill=(100, 116, 139, 235), font=_font(17, False), anchor="mm")
        lit = Image.alpha_composite(lit, detail)

        mug_body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        mug_body.paste(lit, (0, 0), mask)
        canvas = Image.alpha_composite(canvas, mug_body)

        # Ceramic top rim & inner coffee/glaze well
        rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rim)
        rd.ellipse((265, 204, 645, 268), fill=(241, 245, 249, 255), outline=(203, 213, 225, 255), width=4)
        rd.ellipse((284, 214, 626, 258), fill=(51, 65, 85, 255))
        canvas = Image.alpha_composite(canvas, rim)

    elif category_code == "TUM":
        # Insulated Powder-Coated Tumbler + Brushed Steel Collar + Clear Lid
        straw = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        std = ImageDraw.Draw(straw)
        std.rounded_rectangle((486, 95, 514, 205), radius=10, fill=(148, 163, 184, 230))
        std.line([(495, 102), (495, 198)], fill=(255, 255, 255, 160), width=4)
        canvas = Image.alpha_composite(canvas, straw)

        mdraw.polygon([(345, 235), (655, 235), (612, 775), (388, 775)], fill=255)
        mdraw.ellipse((388, 748, 612, 796), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(1.2))

        lit = _lit_fill(S, rgb, cylindrical=True)
        detail = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        dd = ImageDraw.Draw(detail)
        # Brushed stainless steel rim & base band
        dd.rectangle((335, 235, 665, 272), fill=(203, 213, 225, 255))
        dd.rectangle((375, 742, 625, 798), fill=(180, 192, 208, 255))
        # Laser-engraved silver badge
        dd.rounded_rectangle((418, 375, 582, 565), radius=18, outline=(226, 232, 240, 210), width=3)
        dd.text((500, 452), "BOLOMAN", fill=(241, 245, 249, 245), font=_font(26, True), anchor="mm")
        dd.text((500, 490), "LASER ETCHED", fill=(203, 213, 225, 220), font=_font(16, False), anchor="mm")

        spec = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(spec).polygon([(388, 245), (422, 245), (442, 765), (412, 765)], fill=(255, 255, 255, 92))
        lit = Image.alpha_composite(lit, detail)
        lit = Image.alpha_composite(lit, spec.filter(ImageFilter.GaussianBlur(9)))

        body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        body.paste(lit, (0, 0), mask)
        canvas = Image.alpha_composite(canvas, body)

        # Smoked translucent lid
        lid = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lid)
        ld.rounded_rectangle((338, 182, 662, 240), radius=18, fill=(15, 23, 42, 235))
        ld.line([(365, 198), (635, 198)], fill=(255, 255, 255, 95), width=4)
        canvas = Image.alpha_composite(canvas, lid)

    else:
        # Structured Embroidered Baseball Cap
        mdraw.pieslice((215, 255, 785, 765), start=180, end=360, fill=255)
        crown_mask = mask.filter(ImageFilter.GaussianBlur(1.5))
        lit = _lit_fill(S, rgb, cylindrical=False)

        seams = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        sd = ImageDraw.Draw(seams)
        sd.arc((375, 255, 625, 765), start=185, end=355, fill=(0, 0, 0, 75), width=5)
        # Raised 3D embroidery crest
        sd.rounded_rectangle((392, 365, 608, 468), radius=20, fill=(255, 255, 255, 28), outline=(255, 255, 255, 175), width=4)
        sd.text((500, 418), "BOLOMAN", fill=(255, 255, 255, 250), font=_font(28, True), anchor="mm")
        lit = Image.alpha_composite(lit, seams)

        crown = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        crown.paste(lit, (0, 0), crown_mask)
        canvas = Image.alpha_composite(canvas, crown)

        # Top button + curved stitched visor
        visor = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        vd = ImageDraw.Draw(visor)
        vd.ellipse((482, 240, 518, 266), fill=rgb, outline=(255, 255, 255, 65), width=2)
        visor_rgb = (max(0, rgb[0] - 14), max(0, rgb[1] - 14), max(0, rgb[2] - 14))
        vd.pieslice((145, 455, 765, 635), start=0, end=180, fill=(*visor_rgb, 255))
        vd.arc((168, 470, 742, 616), start=10, end=170, fill=(255, 255, 255, 75), width=3)
        canvas = Image.alpha_composite(canvas, visor)

    out = canvas.convert("RGB")
    buffer = io.BytesIO()
    out.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
