# LumiAR

LumiAR is a Flask-based web app for browsing and virtually trying on jewellery and eyewear products. The project showcases a product catalog with category filters and a try-on page that loads processed product images for preview.

## Project Overview

This repository contains a lightweight e-commerce style storefront for:
- Earrings
- Shades (sunglasses)

Users can:
- View all products in a dashboard
- Filter products by category
- Open a try-on page for a selected product
- Fetch product data via API endpoints

## Tech Stack

- Python
- Flask
- HTML
- CSS
- JavaScript
- Static image assets

## Repository Structure

```text
pioneers_bizznnovate/
├── app.py
├── README.md
├── requirements.txt
├── routes/
│   └── jewellery.py
├── service/
│   └── jewelleryService.py
├── static/
│   ├── images/
│   │   ├── jewellery/
│   │   └── processed/
│   └── js/
│       └── dashboard.js
├── templates/
│   ├── dashboard.html
│   └── try_on.html
└── .gitignore
