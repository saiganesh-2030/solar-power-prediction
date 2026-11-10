/**
 * Frontend application entry point.
 *
 * References:
 * - docs/ARCHITECTURE_AND_API.md section 7
 * - docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 3
 */

import { initRouter } from "./router.js";
import { renderFilterBar } from "./components/filterBar.js";
import { get, isMockMode } from "./api/client.js";

// 1. Theme Management (Light / Dark)
function initTheme() {
  const saved = localStorage.getItem("solar_theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);

  const toggleBtn = document.getElementById("theme-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("solar_theme", next);
    });
  }
}

// 2. Fetch System Metadata to Update Header Badge
async function updateMetaBadge() {
  const badge = document.getElementById("data-source-badge");
  if (!badge) return;

  if (isMockMode()) {
    badge.textContent = "Mock Fixtures";
    badge.title = "Frontend running in standalone mock mode (VITE_USE_MOCK=true)";
    return;
  }

  try {
    const meta = await get("/meta");
    const src = meta.data?.source || "artifacts";
    badge.textContent = src === "stub" ? "Stub Data" : "Real Artifacts";
    badge.title = `Backend source: ${src}`;
  } catch (err) {
    badge.textContent = "Backend Offline";
    badge.title = err.message || "Failed to reach FastAPI backend";
  }
}

// 3. Application Bootstrap
function bootstrap() {
  initTheme();

  const filterMount = document.getElementById("filter-bar-mount");
  if (filterMount) {
    renderFilterBar(filterMount);
  }

  const appContent = document.getElementById("app-content");
  if (appContent) {
    initRouter(appContent);
  }

  updateMetaBadge();
}

window.addEventListener("DOMContentLoaded", bootstrap);

