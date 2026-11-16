SHIRT_SIZES = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]
CAP_SIZES = ["ADJ", "FIT"]
MUG_CAPACITIES = ["11oz", "15oz"]
TUMBLER_CAPACITIES = ["20oz", "30oz"]

SIZE_LABELS = {
    "XS": "XS",
    "S": "S",
    "M": "M",
    "L": "L",
    "XL": "XL",
    "2XL": "2XL",
    "3XL": "3XL",
    "ADJ": "Adjustable",
    "FIT": "Fitted",
}

COLOR_CODES = {
    "black": "BLK",
    "white": "WHT",
    "navy": "NVY",
    "red": "RED",
    "royal blue": "RBL",
    "maroon": "MRN",
    "heather gray": "GRY",
    "gray": "GRY",
    "grey": "GRY",
    "forest green": "GRN",
    "green": "GRN",
    "yellow": "YEL",
    "pink": "PNK",
    "gold": "GLD",
    "orange": "ORG",
    "purple": "PUR",
    "sky blue": "SKY",
}


def color_code(name):
    key = (name or "").strip().lower()
    if key in COLOR_CODES:
        return COLOR_CODES[key]
    cleaned = "".join(char for char in key if char.isalnum())
    return (cleaned[:3] or "CLR").upper()


def size_label(code):
    return SIZE_LABELS.get(code, code)
