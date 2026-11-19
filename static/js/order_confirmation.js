(async () => {
    const orderId = document.body.dataset.orderId;
    const heading = document.getElementById("heading");
    const subheading = document.getElementById("subheading");
    const notice = document.getElementById("notice");
    const itemsEl = document.getElementById("items");

    const money = amount => new Intl.NumberFormat("en-IN", {
        style: "currency", currency: "INR"
    }).format(Number(amount || 0));

    try {
        const response = await fetch(`/api/store/orders/${encodeURIComponent(orderId)}`, {
            credentials: "same-origin"
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Order not found");
        const order = data.order;
        heading.textContent = order.status === "paid" ? "Thank you for your order." : "Your order request is received.";
        subheading.textContent = order.status === "paid"
            ? "Your order has been recorded successfully."
            : "Your order is awaiting payment/confirmation. The site has no live payment provider connected yet.";
        if (order.is_test) {
            notice.hidden = false;
            notice.textContent = "Demo order only — no real payment was taken. This transaction is marked as test data in the admin analytics dashboard.";
        } else if (order.status !== "paid") {
            notice.hidden = false;
            notice.textContent = "This is an order request, not a completed payment. A real checkout/payment integration is required before treating it as paid revenue.";
        }
        itemsEl.replaceChildren();
        data.items.forEach(item => {
            const row = document.createElement("div");
            row.className = "item";
            const left = document.createElement("span");
            left.textContent = `${item.product_id} × ${item.quantity}`;
            const right = document.createElement("strong");
            right.textContent = money(Number(item.unit_price) * Number(item.quantity));
            row.append(left, right);
            itemsEl.append(row);
        });
        document.getElementById("total").textContent = money(order.subtotal);
    } catch (error) {
        heading.textContent = "We couldn't load your order.";
        subheading.textContent = error.message;
    }
})();
