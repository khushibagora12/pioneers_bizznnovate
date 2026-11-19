/* Lightweight local cart. Checkout prices are always revalidated by Flask. */
(() => {
    const CART_KEY = "ahi_store_cart_v1";

    function read() {
        try {
            const value = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
            return Array.isArray(value) ? value : [];
        } catch {
            return [];
        }
    }

    function write(items) {
        localStorage.setItem(CART_KEY, JSON.stringify(items));
        updateCount();
        window.dispatchEvent(new CustomEvent("ahi-cart-updated", { detail: { items } }));
    }

    function currentTryOn(productId) {
        try {
            const current = JSON.parse(sessionStorage.getItem("ahi_last_try_on") || "null");
            return current && current.productId === productId ? current.tryOnId : null;
        } catch {
            return null;
        }
    }

    function add(product, quantity = 1) {
        const productId = `${String(product.category).toLowerCase()}:${String(product.id)}`;
        const items = read();
        const tryOnId = currentTryOn(productId);
        const existing = items.find(item => item.productId === productId);

        if (existing) {
            existing.quantity = Math.min(10, (Number(existing.quantity) || 1) + quantity);
            if (tryOnId) existing.tryOnId = tryOnId;
            existing.name = product.name;
            existing.image = product.image;
            existing.category = String(product.category).toLowerCase();
        } else {
            items.push({
                productId,
                category: String(product.category).toLowerCase(),
                id: String(product.id),
                name: product.name,
                image: product.image,
                quantity: Math.min(10, Math.max(1, quantity)),
                tryOnId
            });
        }
        write(items);
        return items;
    }

    function updateQuantity(productId, quantity) {
        const items = read();
        const item = items.find(entry => entry.productId === productId);
        if (!item) return items;
        const next = Number(quantity);
        if (!Number.isInteger(next) || next < 1) {
            write(items.filter(entry => entry.productId !== productId));
            return read();
        }
        item.quantity = Math.min(10, next);
        write(items);
        return items;
    }

    function remove(productId) {
        const items = read().filter(item => item.productId !== productId);
        write(items);
        return items;
    }

    function clear() {
        write([]);
    }

    function count() {
        return read().reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);
    }

    function updateCount() {
        const badge = document.getElementById("cartCount");
        if (badge) badge.textContent = String(count());
    }

    let toastTimer;
    function notify(message) {
        const toast = document.getElementById("storeToast");
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add("visible");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 2400);
    }

    window.AHICart = { read, add, updateQuantity, remove, clear, count, updateCount, notify };
    document.addEventListener("DOMContentLoaded", updateCount);
    window.addEventListener("storage", updateCount);
    window.addEventListener("ahi-cart-updated", updateCount);
})();
