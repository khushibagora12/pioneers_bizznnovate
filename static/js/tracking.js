/* AHI Jewellery analytics bridge. This sends interaction metadata only. */
(() => {
    const ACTIVE_TRY_ON_KEY = "ahi_active_try_on";
    const LAST_TRY_ON_KEY = "ahi_last_try_on";

    function productKey(category, productId) {
        return `${String(category || "").toLowerCase()}:${String(productId)}`;
    }

    async function sendEvent({ eventType, productId, tryOnId = null, metadata = {} }) {
        try {
            const response = await fetch("/api/track/events", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                keepalive: true,
                body: JSON.stringify({
                    eventId: crypto.randomUUID(),
                    eventType,
                    productId,
                    tryOnId,
                    metadata
                })
            });
            if (!response.ok) {
                console.warn("Analytics event was not recorded:", eventType, response.status);
            }
        } catch (error) {
            // Analytics must never prevent the AR experience from working.
            console.warn("Analytics request failed:", eventType, error);
        }
    }

    function trackProductView({ category, productId }) {
        return sendEvent({
            eventType: "product_view",
            productId: productKey(category, productId),
            metadata: { category: String(category).toLowerCase() }
        });
    }

    function startTryOn({ category, productId }) {
        const tryOn = {
            tryOnId: crypto.randomUUID(),
            productId: productKey(category, productId),
            category: String(category).toLowerCase(),
            startedAt: new Date().toISOString()
        };

        try {
            sessionStorage.setItem(ACTIVE_TRY_ON_KEY, JSON.stringify(tryOn));
            sessionStorage.setItem(LAST_TRY_ON_KEY, JSON.stringify(tryOn));
        } catch (error) {
            console.warn("Could not save current try-on context:", error);
        }

        void sendEvent({
            eventType: "try_on_started",
            productId: tryOn.productId,
            tryOnId: tryOn.tryOnId,
            metadata: { category: tryOn.category, mode: "live_camera" }
        });

        return tryOn;
    }

    function getLastTryOn() {
        try {
            return JSON.parse(sessionStorage.getItem(LAST_TRY_ON_KEY) || "null");
        } catch {
            return null;
        }
    }

    window.AHITracking = {
        trackProductView,
        startTryOn,
        getLastTryOn,
        productKey
    };
})();
