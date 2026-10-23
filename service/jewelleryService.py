from pathlib import Path

JEWELLERY_BASE_DIR = Path(__file__).resolve().parent.parent / "static/images/jewellery"

JEWELLERY_METADATA = {
    "ej1": {"name": "Gold Hoop Earrings", "price": 49.99, "width_mm": 25, "height_mm": 30},
    "ej2": {"name": "Elegant Earrings", "price": 49.99, "width_mm": 25, "height_mm": 30},
    "sj1": {"name": "Aviator Sunglasses", "price": 49.99, "width_mm": 140, "height_mm": 50},
    "sj2": {"name": "Stylish Sunglasses", "price": 49.99, "width_mm": 140, "height_mm": 50},
}

def share_jewellery_data():
    data = {}

    for category in ["earrings", "shades"]:
        items = []
        folder = JEWELLERY_BASE_DIR / category

        if folder.exists():
            images = sorted(
                f for f in folder.iterdir()
                if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
            )

            for idx, file in enumerate(images, start=1):
                meta = JEWELLERY_METADATA.get(file.stem.lower(), {})

                items.append({
                    "id": idx,
                    "name": meta.get("name", file.stem.title()),
                    "image": f"/static/images/jewellery/{category}/{file.name}",
                    "price": meta.get("price", 49.99),
                    "width_mm": meta.get("width_mm"),
                    "height_mm": meta.get("height_mm"),
                })

        data[category.title()] = items

    return data