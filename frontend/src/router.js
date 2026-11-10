/**
 * Hash-based client-side router.
 *
 * Supported routes:
 * - #/           (Dashboard Overview)
 * - #/prediction (Solar Power Prediction)
 * - #/models     (Model Performance)
 * - #/anomalies  (Anomaly Detection)
 * - #/weather    (Weather Analysis)
 * - #/history    (Historical Analysis)
 * - #/finance    (Financial Impact Analysis)
 *
 * References:
 * - docs/ARCHITECTURE_AND_API.md section 7
 */

import * as dashboardPage from "./pages/dashboard/index.js";
import * as predictionPage from "./pages/prediction/index.js";
import * as modelsPage from "./pages/models/index.js";
import * as anomaliesPage from "./pages/anomalies/index.js";
import * as weatherPage from "./pages/weather/index.js";
import * as historyPage from "./pages/history/index.js";
import * as financePage from "./pages/finance/index.js";

const routes = {
  "/": dashboardPage,
  "/prediction": predictionPage,
  "/models": modelsPage,
  "/anomalies": anomaliesPage,
  "/weather": weatherPage,
  "/history": historyPage,
  "/finance": financePage,
};

let currentPage = null;

export function initRouter(container) {
  async function handleHashChange() {
    const rawHash = window.location.hash || "#/";
    // Strip leading hash and query parameters for route matching
    const cleanHash = rawHash.replace(/^#/, "").split("?")[0] || "/";
    const path = cleanHash.startsWith("/") ? cleanHash : `/${cleanHash}`;

    const targetPage = routes[path] || routes["/"];

    // Update active class on nav links
    document.querySelectorAll("nav a[data-route]").forEach((link) => {
      const linkRoute = link.getAttribute("data-route");
      if (linkRoute === path || (path === "/" && linkRoute === "/")) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    if (currentPage && typeof currentPage.destroy === "function") {
      try {
        currentPage.destroy();
      } catch (err) {
        console.error("Error destroying page:", err);
      }
    }

    container.innerHTML = "";
    currentPage = targetPage;

    if (currentPage && typeof currentPage.render === "function") {
      try {
        await currentPage.render(container, { path });
      } catch (err) {
        console.error("Error rendering page:", err);
        container.innerHTML = `
          <div class="banner banner-error">
            <h3>Unable to load view</h3>
            <p>${err.message || "An unexpected error occurred."}</p>
          </div>
        `;
      }
    }
  }

  window.addEventListener("hashchange", handleHashChange);
  handleHashChange();
}

