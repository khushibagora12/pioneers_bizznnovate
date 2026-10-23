from flask import Flask, render_template
from routes.jewellery import jewellery

app = Flask(__name__)

app.register_blueprint(jewellery)

@app.route('/')
def home():
    return render_template('dashboard.html')

if __name__ == "__main__":
    app.run(debug=True)