(() => {
    const keyInput = document.getElementById("adminKey");
    const connectBtn = document.getElementById("connectBtn");
    const refreshBtn = document.getElementById("refreshBtn");
    const refreshFrictionBtn = document.getElementById("refreshFrictionBtn");
    const refreshLinksBtn = document.getElementById("refreshLinksBtn");
    const affiliateForm = document.getElementById("affiliateForm");
    const linkForm = document.getElementById("linkForm");
    const statusBox = document.getElementById("connectionStatus");
    const modelSelect = document.getElementById("modelSelect");
    const fmt = value => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(value || 0));
    const money = value => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0));
    let adminKey = sessionStorage.getItem("ahi_admin_key") || "";
    if (adminKey) keyInput.value = adminKey;

    function setStatus(text, kind = "") {
        statusBox.textContent = text;
        statusBox.className = `status ${kind}`;
        statusBox.style.display = text ? "block" : "none";
    }

    async function api(path, options = {}) {
        const response = await fetch(path, {
            ...options,
            headers: { "X-Admin-Key": adminKey, ...(options.headers || {}) },
            credentials: "same-origin"
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
        return data;
    }

    function setText(id, value) { document.getElementById(id).textContent = value; }

    function renderAttribution(data) {
        const body = document.getElementById("attributionRows");
        body.replaceChildren();
        if (!data.affiliates.length) {
            body.innerHTML = '<tr><td colspan="6" class="empty">No attributed paid orders yet. Create referral links, test a tracked journey, then place an order.</td></tr>';
            return;
        }
        data.affiliates.forEach(item => {
            const row = document.createElement("tr");
            [item.affiliate_name, fmt(item.real_credited_orders), money(item.real_attributed_revenue), money(item.real_commission), money(item.demo_attributed_revenue), money(item.demo_commission)].forEach(value => {
                const cell = document.createElement("td"); cell.textContent = value; row.append(cell);
            });
            body.append(row);
        });
    }

    function renderFriction(data) {
        const body = document.getElementById("frictionRows");
        body.replaceChildren();
        if (!data.products.length) {
            body.innerHTML = '<tr><td colspan="7" class="empty">No product interactions recorded yet.</td></tr>';
            return;
        }
        data.products.forEach(item => {
            const row = document.createElement("tr");
            const values = [item.product_id, `${fmt(item.product_views)} / ${fmt(item.unique_product_viewers)}`, fmt(item.try_on_starts), `${fmt(item.product_view_to_try_on_rate_percent)}%`, `${fmt(item.purchasing_try_ons)} (${fmt(item.demo_purchasing_try_ons)} demo / ${fmt(item.real_purchasing_try_ons)} real)`, `${fmt(item.try_on_to_purchase_rate_percent)}%`];
            values.forEach(value => { const cell = document.createElement("td"); cell.textContent = value; row.append(cell); });
            const flag = document.createElement("td");
            const pill = document.createElement("span");
            pill.className = `pill ${item.status === "potential_friction" ? "warn" : item.status === "within_baseline" ? "good" : ""}`;
            pill.textContent = item.status.replaceAll("_", " ");
            flag.append(pill); row.append(flag); body.append(row);
        });
    }

    function renderOrders(data) {
        const body = document.getElementById("orderRows");
        body.replaceChildren();
        if (!data.orders.length) {
            body.innerHTML = '<tr><td colspan="7" class="empty">No orders yet. Add a product to the bag and test checkout.</td></tr>';
            return;
        }
        data.orders.forEach(order => {
            const row = document.createElement("tr");
            const date = order.created_at ? new Date(order.created_at).toLocaleString() : "—";
            const orderType = order.is_test ? "DEMO / TEST" : (order.status === "paid" ? "REAL / NON-TEST" : "NOT PAID");
            const values = [String(order.id).slice(0, 8), order.customer_name || "Guest", `${fmt(order.item_quantity)} item(s)`, money(order.subtotal), order.status, orderType, date];
            values.forEach((value, index) => {
                const cell = document.createElement("td"); cell.textContent = value;
                if (index === 5 && order.is_test) { const pill = document.createElement("span"); pill.className = "pill warn"; pill.textContent = value; cell.replaceChildren(pill); }
                if (index === 4) { const pill = document.createElement("span"); pill.className = `pill ${order.status === "paid" ? "good" : order.status === "pending" ? "warn" : ""}`; pill.textContent = value; cell.replaceChildren(pill); }
                row.append(cell);
            });
            body.append(row);
        });
    }

    function setFormMessage(id, text, kind = "") {
        const element = document.getElementById(id);
        element.textContent = text;
        element.className = `status ${kind}`;
        element.style.display = text ? "block" : "none";
    }

    async function loadAffiliateManagement() {
        const [affiliateData, linkData] = await Promise.all([
            api("/api/admin/affiliates"),
            api("/api/admin/referral-links")
        ]);
        const select = document.getElementById("linkAffiliate");
        select.replaceChildren();
        const activeAffiliates = affiliateData.affiliates.filter(item => Number(item.active) === 1);
        if (!activeAffiliates.length) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Create an affiliate first";
            select.append(option);
        } else {
            activeAffiliates.forEach(affiliate => {
                const option = document.createElement("option");
                option.value = String(affiliate.id);
                option.textContent = `${affiliate.name} (${affiliate.code})`;
                select.append(option);
            });
        }
        const body = document.getElementById("referralLinkRows");
        body.replaceChildren();
        if (!linkData.referral_links.length) {
            body.innerHTML = '<tr><td colspan="5" class="empty">No referral links yet. Create one above.</td></tr>';
        } else {
            linkData.referral_links.forEach(link => {
                const row = document.createElement("tr");
                const affiliate = document.createElement("td"); affiliate.textContent = link.affiliate_name;
                const source = document.createElement("td"); source.textContent = `${link.source}${link.campaign ? ` / ${link.campaign}` : ""}`;
                const destination = document.createElement("td"); destination.textContent = link.destination_path;
                const urlCell = document.createElement("td");
                const urlText = document.createElement("div"); urlText.textContent = link.referral_url; urlText.style.overflowWrap = "anywhere"; urlText.style.maxWidth = "300px";
                const copy = document.createElement("button"); copy.type = "button"; copy.className = "btn secondary"; copy.textContent = "Copy link"; copy.style.marginTop = "7px";
                copy.addEventListener("click", async () => {
                    try {
                        await navigator.clipboard.writeText(link.referral_url);
                        copy.textContent = "Copied ✓";
                    } catch {
                        window.prompt("Copy this referral URL", link.referral_url);
                    }
                });
                urlCell.append(urlText, copy);
                const stateCell = document.createElement("td");
                const pill = document.createElement("span"); pill.className = `pill ${Number(link.active) === 1 ? "good" : ""}`; pill.textContent = Number(link.active) === 1 ? "Active" : "Inactive"; stateCell.append(pill);
                row.append(affiliate, source, destination, urlCell, stateCell);
                body.append(row);
            });
        }
    }

    function enableManagement(enabled) {
        [affiliateForm, linkForm].forEach(form => {
            form.querySelectorAll("input,select,button").forEach(control => { control.disabled = !enabled; });
        });
        refreshLinksBtn.disabled = !enabled;
    }

    affiliateForm.addEventListener("submit", async event => {
        event.preventDefault();
        const submit = affiliateForm.querySelector("button[type='submit']");
        submit.disabled = true;
        try {
            const data = {
                code: document.getElementById("affiliateCode").value.trim(),
                name: document.getElementById("affiliateName").value.trim(),
                commission_rate: Number(document.getElementById("affiliateRate").value) / 100
            };
            await api("/api/admin/affiliates", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });
            affiliateForm.reset();
            document.getElementById("affiliateRate").value = "10";
            setFormMessage("affiliateMessage", "Affiliate created.", "ok");
            await loadAffiliateManagement();
        } catch (error) {
            setFormMessage("affiliateMessage", error.message, "error");
        } finally {
            submit.disabled = !adminKey;
        }
    });

    linkForm.addEventListener("submit", async event => {
        event.preventDefault();
        const submit = linkForm.querySelector("button[type='submit']");
        submit.disabled = true;
        try {
            const data = {
                affiliate_id: Number(document.getElementById("linkAffiliate").value),
                source: document.getElementById("linkSource").value,
                campaign: document.getElementById("linkCampaign").value.trim(),
                destination_path: document.getElementById("linkDestination").value.trim()
            };
            const result = await api("/api/admin/referral-links", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });
            setFormMessage("linkMessage", `Referral URL created: ${result.referral_url}`, "ok");
            await loadAffiliateManagement();
        } catch (error) {
            setFormMessage("linkMessage", error.message, "error");
        } finally {
            submit.disabled = !adminKey;
        }
    });

    refreshLinksBtn.addEventListener("click", async () => {
        try { await loadAffiliateManagement(); setStatus("Affiliate and referral-link data refreshed.", "ok"); }
        catch (error) { setStatus(error.message, "error"); }
    });

    async function loadDashboard() {
        adminKey = keyInput.value.trim();
        if (!adminKey) { setStatus("Enter your admin API key.", "error"); return; }
        connectBtn.disabled = refreshBtn.disabled = refreshFrictionBtn.disabled = true;
        setStatus("Loading analytics…");
        try {
            const model = modelSelect.value;
            const [overview, attribution, friction, orders] = await Promise.all([
                api("/api/admin/analytics/overview"),
                api(`/api/admin/analytics/attribution?model=${encodeURIComponent(model)}`),
                api("/api/admin/analytics/scale-friction"),
                api("/api/admin/orders")
            ]);
            await loadAffiliateManagement();
            enableManagement(true);
            sessionStorage.setItem("ahi_admin_key", adminKey);
            setText("kpiReferrals", fmt(overview.referral_touchpoints));
            const views = overview.product_events.reduce((sum, row) => sum + Number(row.product_views || 0), 0);
            const tryons = overview.product_events.reduce((sum, row) => sum + Number(row.try_on_starts || 0), 0);
            setText("kpiViews", fmt(views));
            setText("kpiTryons", fmt(tryons));
            setText("kpiOrders", fmt(overview.total_orders));
            setText("kpiRevenue", money(overview.real_revenue));
            setText("kpiDemoRevenue", money(overview.demo_revenue));
            setText("kpiRealOrders", fmt(overview.real_paid_orders));
            setText("kpiPending", fmt(overview.pending_orders));
            setText("kpiOrdersCaption", `${fmt(overview.real_paid_orders)} real paid · ${fmt(overview.demo_paid_orders)} demo paid · ${fmt(overview.pending_orders)} pending`);
            renderAttribution(attribution);
            renderFriction(friction);
            renderOrders(orders);
            setStatus("Connected. Analytics are loaded from the Flask backend.", "ok");
        } catch (error) {
            sessionStorage.removeItem("ahi_admin_key");
            enableManagement(false);
            setStatus(error.message || "Could not load analytics. Check the admin key and backend logs.", "error");
        } finally {
            connectBtn.disabled = false;
            refreshBtn.disabled = false;
            refreshFrictionBtn.disabled = false;
        }
    }

    connectBtn.addEventListener("click", loadDashboard);
    refreshBtn.addEventListener("click", loadDashboard);
    refreshFrictionBtn.addEventListener("click", loadDashboard);
    modelSelect.addEventListener("change", () => { if (adminKey) loadDashboard(); });
    keyInput.addEventListener("keydown", event => { if (event.key === "Enter") loadDashboard(); });
    enableManagement(false);
    if (adminKey) loadDashboard();
})();
