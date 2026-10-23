
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

async function loadProducts() {
    try {
        const response = await fetch("/jewellery");

        if (!response.ok) {
            throw new Error("Failed to fetch products");
        }

        const data = await response.json();

        products = [
            ...(data.Earrings || []).map(item => ({
                ...item,
                category: "earrings"
            })),
            ...(data.Shades || []).map(item => ({
                ...item,
                category: "shades"
            }))
        ];
        renderProducts();
    } catch (error) {
        console.error(error);
        grid.replaceChildren();
        emptyState.textContent = "Unable to load products. Please try again.";
        emptyState.style.display = "block";
    }
}

function renderProducts(category = "all") {
    const filtered = products.filter(product =>
        category === "all" || product.category === category
    );

    title.textContent = categoryNames[category];
    count.textContent = `${filtered.length} product${filtered.length === 1 ? "" : "s"}`;

    grid.replaceChildren();
    emptyState.textContent = "No products found.";
    emptyState.style.display = filtered.length ? "none" : "block";

    filtered.forEach(product => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "product-card";

        const imageBox = document.createElement("div");
        imageBox.className = "product-image";

        const image = document.createElement("img");
        image.src = product.image;
        image.alt = product.name;
        image.loading = "lazy";

        image.onerror = () => {
            imageBox.textContent = "Image unavailable";
        };

        imageBox.appendChild(image);

        const info = document.createElement("div");
        info.className = "product-info";

        const name = document.createElement("h3");
        name.textContent = product.name;

        const categoryLabel = document.createElement("p");
        categoryLabel.textContent = categoryNames[product.category];

        const tryOn = document.createElement("span");
        tryOn.className = "try-on-btn";
        tryOn.textContent = "Try this on";

        info.append(name, categoryLabel, tryOn);
        card.append(imageBox, info);

        card.addEventListener("click", () => {
            const params = new URLSearchParams({
                product: String(product.id),
                category: product.category
            });

            window.location.href = `/try-on?${params}`;
        });

        grid.appendChild(card);
    });
}

document.querySelectorAll(".category-btn").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".category-btn")
            .forEach(item => item.classList.remove("active"));

        button.classList.add("active");
        renderProducts(button.dataset.category);
    });
});

loadProducts();
