from pathlib import Path
import re

JEWELLERY_BASE_DIR = Path(__file__).resolve().parent.parent / "static" / "images" / "jewellery"

JEWELLERY_METADATA = {
    # Earrings
    "ej1": {
        "name": "Gold Hoop Earrings", 
        "price": 49.99,
        "width_mm": 25,
        "height_mm": 30,
    },
    "ej2": {
        "name": "Elegant Earrings", 
        "price": 49.99,
        "width_mm": 25,
        "height_mm": 30
    },
    # Shades
    "sj1": {
        "name": "Aviator Sunglasses", 
        "price": 49.99,
        "width_mm": 140,
        "height_mm": 50
    },
    "sj2": {
        "name": "Stylish Sunglasses",
        "price": 49.99,
        "width_mm": 140,
        "height_mm": 50
    },
}
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _natural_sort_key(path):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', path.name)]


def share_jewellery_data():
    categories = [
        ("Earrings", "earrings"),
        ("Shades", "shades"),
    ]

    data = {}

    for display_category, folder_name in categories:
        category_dir = JEWELLERY_BASE_DIR / folder_name
        items = []

        if category_dir.is_dir():
            image_files = sorted(
                [
                    f for f in category_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
                ],
                key=_natural_sort_key
            )

            for idx, file in enumerate(image_files, start=1):
                stem = file.stem.lower()
                meta = JEWELLERY_METADATA.get(stem, {})
                name = meta.get("name") or stem.replace("_", " ").title()
                price = meta.get("price", 49.99)
                width_mm = meta.get("width_mm")
                height_mm = meta.get("height_mm")
                items.append({
                    "id": idx,
                    "name": name,
                    "image": f"/static/images/jewellery/{folder_name}/{file.name}",
                    "price": price,
                    "width_mm": width_mm,
                    "height_mm": height_mm,
                })

        data[display_category] = items

    return data