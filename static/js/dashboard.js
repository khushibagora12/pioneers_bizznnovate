const grid = document.getElementById("productGrid");
const title = document.getElementById("sectionTitle");
const count = document.getElementById("productCount");
const emptyState = document.getElementById("emptyState");

const categoryNames = {
    all: "All products",
    earrings: "Earrings",
    necklaces: "Necklaces",
    shades: "Shades"
};

let products = [];
console.log("in js")
async function loadProducts() {
    try {
        const response = await fetch("/jewellery");

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        console.log("Products fetched successfully:", data);
        products = [
            ...(data.Earrings ?? []).map(item => ({
                ...item,
                category: "earrings"
            })),
            ...(data.Necklaces ?? []).map(item => ({
                ...item,
                category: "necklaces"
            })),
            ...(data.Shades ?? []).map(item => ({
                ...item,
                category: "shades"
            }))
        ];

        renderProducts();
    }
    catch (error) {
        console.error("Failed to load products:", error);
        grid.replaceChildren();

        const message = document.createElement("p");
        message.textContent = "Unable to load products. Please try again.";
        grid.appendChild(message);
    }
}

function renderProducts(category = "all") {
    const filtered = products.filter(product =>
        category === "all" || product.category === category
    );

    title.textContent = categoryNames[category] ?? "Products";
    count.textContent = `${filtered.length} product${filtered.length === 1 ? "" : "s"}`;

    grid.replaceChildren();
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
        console.log("Rendering product:", product.name, "Image URL:", product.image);

        image.onerror = () => {
            imageBox.textContent = "Image unavailable";
        };
        imageBox.appendChild(image);

        const info = document.createElement("div");
        info.className = "product-info";

        const name = document.createElement("h3");
        name.textContent = product.name;

        const categoryLabel = document.createElement("p");
        categoryLabel.textContent =
            categoryNames[product.category] ?? product.category;

        const tryOn = document.createElement("div");
        tryOn.className = "try-on-btn";
        tryOn.textContent = "Try this on";

        info.append(name, categoryLabel, tryOn);
        card.append(imageBox, info);

        card.addEventListener("click", () => {
            const params = new URLSearchParams({
                product: String(product.id),
                category: product.category
            });

            window.location.href = `/try-on?${params.toString()}`;
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
