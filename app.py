from flask import Flask, render_template
from routes.jewellery import jewellery

app = Flask(__name__)

app.register_blueprint(jewellery)

# Register referral tracking, attribution, demo-order and analytics routes
# on the SAME Flask app as the storefront and AR feature.
from ahi_attribution.integration import register_attribution
register_attribution(app)

@app.route('/')
def home():
    return render_template('dashboard.html')

if __name__ == "__main__":
    app.run(debug=True)