
document.addEventListener('DOMContentLoaded', async () => {
    const config = window.AR_PAGE_CONFIG || {};

    const category = String(config.category || '').toLowerCase();
    const productId = String(config.productId || '');

    const productImage = document.getElementById('productImage');
    const productName = document.getElementById('productName');
    const productCategory = document.getElementById('productCategory');
    const productPrice = document.getElementById('productPrice');
    const changeProduct = document.getElementById('changeProduct');
    const captureButton = document.getElementById('captureButton');
    const status = document.getElementById('status');

    const categoryLabels = {
        earrings: 'Earrings',
        necklaces: 'Necklaces',
        shades: 'Shades'
    };

    function setStatus(message) {
        if (status) status.textContent = message;
    }

    try {
        if (!productId || !categoryLabels[category]) {
            throw new Error('Invalid product or category.');
        }

        productName.textContent = 'Loading product...';
        productCategory.textContent = categoryLabels[category];

        // Fetch product information.
        const productsResponse = await fetch('/jewellery');

        if (!productsResponse.ok) {
            throw new Error('Unable to fetch product details.');
        }

        const allProducts = await productsResponse.json();

        const sourceCategory = {
            earrings: 'Earrings',
            necklaces: 'Necklaces',
            shades: 'Shades'
        }[category];

        const categoryProducts = allProducts[sourceCategory] || [];

        const product = categoryProducts.find(
            item => String(item.id) === productId
        );

        if (!product) {
            throw new Error('Selected product was not found.');
        }

        // Fetch the AR-ready image URL.

        const arResponse = await fetch(
            `/api/try_on/${encodeURIComponent(category)}/${encodeURIComponent(productId)}`
        );

        const arData = await arResponse.json();

        if (!arResponse.ok || !arData.success || !arData.image_url) {
            throw new Error(arData.error || 'Unable to load processed image.');
        }

        const image = new Image();

        await new Promise((resolve, reject) => {
            image.onload = resolve;
            image.onerror = () => reject(
                new Error(`Could not load processed image: ${arData.image_url}`)
            );
            image.src = arData.image_url;
        });

        productImage.src = arData.image_url;
        productImage.alt = product.name || 'Selected product';
        productImage.hidden = false;

        productName.textContent = product.name || 'Selected design';
        productPrice.textContent =
            product.price != null ? `₹${product.price}` : '';

        document.title = `${product.name || 'Virtual Try-On'} | LUMIAR`;

        window.AR_PRODUCT = {
            category,
            productId,
            imageUrl: arData.image_url,
            image
        };

        window.dispatchEvent(
            new CustomEvent('ar-product-ready', {
                detail: window.AR_PRODUCT
            })
        );

        setStatus('Product loaded. Start the camera to try it on.');

        if (captureButton) {
            captureButton.disabled = true;
        }

        console.log('Product page loaded:', window.AR_PRODUCT);

    } catch (error) {
        console.error('Product page error:', error);

        productName.textContent = 'Unable to load product';
        productCategory.textContent = categoryLabels[category] || '';
        productPrice.textContent = '';

        setStatus(error.message || 'Could not load product.');

        if (captureButton) captureButton.disabled = true;
    }

    // Return to the product dashboard.
    changeProduct?.addEventListener('click', () => {
        window.location.href = '/';
    });
});