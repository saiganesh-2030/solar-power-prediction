/**
 * Feature 3 — Anomaly Detection (Owned by Role 2)
 *
 * Persistence-filtered deviation events, calibrated prediction bands, and evidence ladder.
 *
 * References:
 * - docs/PROJECT_HANDBOOK.md section 5 (Feature 3)
 * - docs/roles/ROLE_2_ANOMALY_WEATHER.md
 */

import { createBanner } from "../../components/banner.js";

export async function render(container, ctx) {
  container.innerHTML = "";

  const header = document.createElement("header");
  header.className = "page-header";
  header.innerHTML = `
    <h2>Anomaly Detection</h2>
    <p class="text-muted">Significant generation deviations evaluated against conformal bands with multi-signal evidence.</p>
  `;
  container.appendChild(header);

  const content = document.createElement("div");
  content.className = "page-content";

  content.appendChild(
    createBanner({
      type: "info",
      title: "Feature Shell Ready (Role 2)",
      message: "This feature slice will be implemented by Role 2 (GET /api/v1/anomalies and /api/v1/anomalies/{event_id}).",
    })
  );

  container.appendChild(content);
}

export function destroy() {
  // Teardown logic
}

