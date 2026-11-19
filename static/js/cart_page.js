(() => {
    const cartItemsEl = document.getElementById("cartItems");
    const emptyStateEl = document.getElementById("emptyState");
    const countEl = document.getElementById("itemCount");
    const subtotalEl = document.getElementById("cartSubtotal");
    const form = document.getElementById("checkoutForm");
    const message = document.getElementById("checkoutMessage");
    const checkoutButton = document.getElementById("checkoutButton");
    const demoCheckout = document.body.dataset.demoCheckout === "true";
    const categoryNames = { earrings: "Earrings", shades: "Shades" };
    let catalogue = new Map();

    function money(value) {
        return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(value || 0));
    }

    function showMessage(text, error = false) {
        message.textContent = text;
        message.style.display = "block";
        message.style.background = error ? "#f6e4e0" : "#f0eadf";
        message.style.color = error ? "#8c3f33" : "#65513a";
    }

    async function loadCatalogue() {
        const response = await fetch("/jewellery");
        if (!response.ok) throw new Error("Unable to load the product catalogue.");
        const data = await response.json();
        for (const [category, apiKey] of Object.entries({ earrings: "Earrings", shades: "Shades" })) {
            (data[apiKey] || []).forEach(product => {
                catalogue.set(`${category}:${product.id}`, { ...product, category, productId: `${category}:${product.id}` });
            });
        }
    }

    function render() {
        const cart = window.AHICart.read();
        cartItemsEl.replaceChildren();
        emptyStateEl.hidden = cart.length > 0;
        cartItemsEl.hidden = cart.length === 0;
        form.querySelectorAll("input,textarea,button").forEach(control => {
            if (control.id !== "checkoutButton") return;
            control.disabled = cart.length === 0;
        });
        let subtotal = 0;
        let itemCount = 0;

        cart.forEach(entry => {
            const product = catalogue.get(entry.productId);
            if (!product) return;
            const quantity = Math.max(1, Number(entry.quantity) || 1);
            subtotal += Number(product.price || 0) * quantity;
            itemCount += quantity;

            const row = document.createElement("article");
            row.className = "cart-row";
            const img = document.createElement("img");
            img.src = product.image;
            img.alt = product.name;
            const info = document.createElement("div");
            const name = document.createElement("h3");
            name.className = "item-name";
            name.textContent = product.name;
            const category = document.createElement("p");
            category.className = "muted";
            category.textContent = categoryNames[entry.category] || entry.category;
            const controls = document.createElement("div");
            controls.className = "item-controls";
            const minus = document.createElement("button");
            minus.className = "qty-btn"; minus.type = "button"; minus.textContent = "−";
            minus.setAttribute("aria-label", `Decrease ${product.name} quantity`);
            minus.addEventListener("click", () => window.AHICart.updateQuantity(entry.productId, quantity - 1));
            const qty = document.createElement("span"); qty.textContent = String(quantity);
            const plus = document.createElement("button");
            plus.className = "qty-btn"; plus.type = "button"; plus.textContent = "+";
            plus.setAttribute("aria-label", `Increase ${product.name} quantity`);
            plus.disabled = quantity >= 10;
            plus.addEventListener("click", () => window.AHICart.updateQuantity(entry.productId, quantity + 1));
            const remove = document.createElement("button");
            remove.className = "remove-btn"; remove.type = "button"; remove.textContent = "Remove";
            remove.addEventListener("click", () => window.AHICart.remove(entry.productId));
            const linePrice = document.createElement("span");
            linePrice.className = "line-price";
            linePrice.textContent = money(Number(product.price || 0) * quantity);
            controls.append(minus, qty, plus, remove, linePrice);
            info.append(name, category, controls);
            row.append(img, info);
            cartItemsEl.append(row);
        });

        countEl.textContent = itemCount ? `(${itemCount} item${itemCount === 1 ? "" : "s"})` : "(0 items)";
        subtotalEl.textContent = money(subtotal);
        window.AHICart.updateCount();
    }

    window.addEventListener("ahi-cart-updated", render);

    form.addEventListener("submit", async event => {
        event.preventDefault();
        const cart = window.AHICart.read();
        if (!cart.length) return showMessage("Your bag is empty.", true);

        checkoutButton.disabled = true;
        checkoutButton.textContent = "Placing order…";
        message.style.display = "none";
        const payload = {
            customerName: document.getElementById("customerName").value.trim(),
            customerEmail: document.getElementById("customerEmail").value.trim(),
            customerPhone: document.getElementById("customerPhone").value.trim(),
            shippingAddress: document.getElementById("shippingAddress").value.trim(),
            items: cart.map(item => ({
                productId: item.productId,
                quantity: Number(item.quantity) || 1,
                tryOnId: item.tryOnId || null
            }))
        };

        try {
            const response = await fetch("/api/store/checkout", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Could not place your order.");
            window.AHICart.clear();
            window.location.href = `/order-confirmation/${encodeURIComponent(data.order_id)}`;
        } catch (error) {
            showMessage(error.message || "Unable to place order. Please try again.", true);
        } finally {
            checkoutButton.disabled = window.AHICart.read().length === 0;
            checkoutButton.textContent = demoCheckout ? "Complete demo order · no charge" : "Submit order request";
        }
    });

    loadCatalogue().then(render).catch(error => showMessage(error.message, true));
})();
