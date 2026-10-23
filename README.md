# LUMIAR — Virtual Jewellery & Eyewear Try-On

LUMIAR is a web-based Augmented Reality (AR) application that lets users browse and virtually try on jewellery and sunglasses in real time using their web camera.

Everything runs directly inside the browser using client-side AI, providing a fast, smooth, and privacy-friendly virtual try-on experience without needing any app installation.

---

## Key Features Implemented

### 1. Interactive Product Catalog
- **Browse Products:** View available earrings and sunglasses with high-quality images, titles, and prices.
- **Category Filters:** Easily filter products by **All**, **Earrings**, or **Shades**.
- **Hero Showcase Carousel:** An interactive image carousel highlighting featured collections with automatic cycling and navigation controls.
- **Instant Try-On Navigation:** Click **"Try On"** on any product card to immediately load it into the AR fitting room.

### 2. Client-Side Face Landmark Detection (MediaPipe)
- **Zero App Installation:** Works directly in any modern web browser.
- **Real-Time 3D Face Tracking:** Powered by **Google MediaPipe Face Landmarker**, tracking key facial landmarks at 30+ FPS.
- **100% Privacy Protected:** Camera video frames are processed entirely on your local device inside the browser. No video or photo data is ever sent to or stored on a server.
- **Camera Controls:** Simple buttons to start and stop camera access anytime with clear status indicators.

### 3. Realistic Jewellery Scaling & Placement
- **Physical Dimension Support:** Product metadata includes real-world measurements (`width_mm` and `height_mm`).
- **Automatic Face-Scale Estimation:** Calculates distance between facial features (such as eye corners and temple width) to determine the user's distance from the camera.
- **Accurate Aspect Ratio:** Preserves original product proportions so jewellery and eyewear look natural without stretching.
- **Specific Feature Anchoring:**
  - **Earrings:** Automatically anchored to the left and right earlobe landmarks, tilting naturally with head movements.
  - **Sunglasses (Shades):** Centered on the bridge of the nose and aligned horizontally across the eyes and temples.

### 4. Try-On Capture & Details
- **Product Overview Panel:** Displays the selected item's image, title, category, price, and dimensions right next to the live camera feed.
- **Capture Look:** Take a snapshot of your virtual try-on preview to review your look.
- **Seamless Product Switching:** Quickly switch between designs without restarting the camera feed.

---

## Tech Stack

- **Backend:** Python, Flask, Gunicorn
- **Computer Vision:** Google MediaPipe Tasks Vision (`FaceLandmarker`)
- **Rendering & AR:** Three.js, HTML5 Canvas, WebGL
- **Frontend:** HTML5, Modern CSS (Responsive & Mobile-Friendly), Vanilla JavaScript

---

## Project Structure

```text
Ahi-ar/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── routes/
│   └── jewellery.py            # API routes and page controllers
├── service/
│   └── jewelleryService.py     # Product scanning and physical metadata
├── static/
│   ├── images/
│   │   ├── jewellery/          # Original catalog images (earrings, shades)
│   │   └── processed/          # Transparent PNG cutouts for AR overlay
│   └── js/
│       ├── ar.js               # AR loop, camera streaming & MediaPipe setup
│       ├── earrings.js         # Earlobe tracking and earring positioning
│       ├── glasses.js          # Sunglasses alignment and bridge tracking
│       ├── dashboard.js        # Catalog filtering & carousel logic
│       └── try_on.js           # Try-on page product info & UI lifecycle
└── templates/
    ├── dashboard.html          # Storefront catalog page
    └── try_on.html             # Virtual AR try-on room
```

---

## How to Run Locally

### 1. Clone the repository
```bash
git clone https://github.com/khushibagora12/pioneers_bizznnovate.git
cd pioneers_bizznnovate
```

### 2. Set up virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
Allow camera access when prompted on the try-on page to begin testing!
