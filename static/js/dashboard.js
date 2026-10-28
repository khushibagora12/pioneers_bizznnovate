const grid = document.getElementById("productGrid");
const title = document.getElementById("sectionTitle");
const count = document.getElementById("productCount");
const emptyState = document.getElementById("emptyState");

const categoryNames = {
    all: "All products",
    earrings: "Earrings",
    shades: "Shades"
};

let products = [];

function namespacedProductId(product) {
    return `${String(product.category).toLowerCase()}:${String(product.id)}`;
}

async function loadProducts() {
    try {
        const response = await fetch("/jewellery");
        if (!response.ok) throw new Error("Failed to fetch products");

        const data = await response.json();
        products = [
            ...(data.Earrings || []).map(item => ({ ...item, category: "earrings" })),
            ...(data.Shades || []).map(item => ({ ...item, category: "shades" }))
        ];
        renderProducts();
        window.AHICart?.updateCount();
    } catch (error) {
        console.error(error);
        grid.replaceChildren();
        emptyState.textContent = "Unable to load products. Please try again.";
        emptyState.style.display = "block";
    }
}

function renderProducts(category = "all") {
    const filtered = products.filter(product => category === "all" || product.category === category);
    title.textContent = categoryNames[category];
    count.textContent = `${filtered.length} product${filtered.length === 1 ? "" : "s"}`;
    grid.replaceChildren();
    emptyState.textContent = "No products found.";
    emptyState.style.display = filtered.length ? "none" : "block";

    filtered.forEach(product => {
        const card = document.createElement("article");
        card.className = "product-card";

        const imageBox = document.createElement("div");
        imageBox.className = "product-image";
        const image = document.createElement("img");
        image.src = product.image;
        image.alt = product.name;
        image.loading = "lazy";
        image.onerror = () => { imageBox.textContent = "Image unavailable"; };
        imageBox.appendChild(image);

        const info = document.createElement("div");
        info.className = "product-info";
        const name = document.createElement("h3");
        name.textContent = product.name;
        const categoryLabel = document.createElement("p");
        categoryLabel.textContent = categoryNames[product.category];
        const price = document.createElement("p");
        price.className = "product-price";
        price.textContent = `₹${Number(product.price || 0).toFixed(2)}`;

        const actions = document.createElement("div");
        actions.className = "product-actions-row";

        const tryOn = document.createElement("button");
        tryOn.type = "button";
        tryOn.className = "try-on-btn";
        tryOn.textContent = "Try on";
        tryOn.addEventListener("click", () => {
            const params = new URLSearchParams({ product: String(product.id), category: product.category });
            window.location.href = `/try-on?${params}`;
        });

        const addToBag = document.createElement("button");
        addToBag.type = "button";
        addToBag.className = "add-to-bag-btn";
        addToBag.textContent = "Add to bag";
        addToBag.addEventListener("click", () => {
            window.AHICart?.add(product);
            window.AHICart?.notify(`${product.name} added to your bag`);
        });

        actions.append(tryOn, addToBag);
        info.append(name, categoryLabel, price, actions);
        card.append(imageBox, info);
        grid.appendChild(card);
    });
}

document.querySelectorAll(".category-btn").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".category-btn").forEach(item => {
            item.classList.remove("active");
            item.setAttribute("aria-pressed", "false");
        });
        button.classList.add("active");
        button.setAttribute("aria-pressed", "true");
        renderProducts(button.dataset.category);
    });
});

document.querySelectorAll("[data-nav-category]").forEach(link => {
    link.addEventListener("click", () => {
        const category = link.dataset.navCategory;
        const button = document.querySelector(`.category-btn[data-category="${category}"]`);
        if (button) button.click();
    });
});

loadProducts();
