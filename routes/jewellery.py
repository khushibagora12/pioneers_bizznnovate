from flask import Blueprint, jsonify, render_template, request, url_for
from service.jewelleryService import share_jewellery_data
from flask import current_app
from pathlib import Path

jewellery = Blueprint('jewellery', __name__)

@jewellery.route('/jewellery')
def jewellery_data():
    jewellery_items = share_jewellery_data()
    print("Jewellery data fetched:", jewellery_items) 
    return jsonify(jewellery_items), 200

@jewellery.route('/api/try_on/<category>/<product_id>')
def try_on_jewellery(category, product_id):
    category = category.lower()

    category_map = {
        "earrings": ("Earrings", "earrings"),
        "shades": ("Shades", "shades"),
    }

    if category not in category_map:
        return jsonify({
            "success": False,
            "error": "Unsupported category"
        }), 400

    data_key, folder_name = category_map[category]
    products = share_jewellery_data().get(data_key, [])

    product = next(
        (item for item in products if str(item["id"]) == str(product_id)),
        None
    )

    if product is None:
        return jsonify({
            "success": False,
            "error": "Product not found"
        }), 404

    # Use the actual filename, e.g. ej2.png, not 2.png.
    filename = Path(product["image"]).stem + ".png"

    image_path = (
        Path(current_app.root_path)
        / "static" / "images" / "processed"
        / folder_name / filename
    )

    if not image_path.is_file():
        return jsonify({
            "success": False,
            "error": f"Processed image not found: {folder_name}/{filename}"
        }), 404

    image_url = url_for(
        "static",
        filename=f"images/processed/{folder_name}/{filename}"
    )

    return jsonify({
        "success": True,
        "image": image_url,
        "image_url": image_url
    }), 200

    

@jewellery.route('/try-on')
def try_on_page():
    return render_template(
        'try_on.html',
        category=request.args.get('category', ''),
        product_id=request.args.get('product', '')
    )