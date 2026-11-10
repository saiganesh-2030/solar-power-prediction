/**
 * Feature 6 — Model Performance (Owned by Role 1)
 *
 * Metrics, baselines comparison, walk-forward CV, and residual breakdowns.
 *
 * References:
 * - docs/PROJECT_HANDBOOK.md section 5 (Feature 6)
 * - docs/roles/ROLE_1_ML_ENGINEER.md
 */

import { createBanner } from "../../components/banner.js";

export async function render(container, ctx) {
  container.innerHTML = "";

  const header = document.createElement("header");
  header.className = "page-header";
  header.innerHTML = `
    <h2>Model Performance</h2>
    <p class="text-muted">Rigorous chronological evaluation on unseen days with primary daylight-only metrics.</p>
  `;
  container.appendChild(header);

  const content = document.createElement("div");
  content.className = "page-content";

  content.appendChild(
    createBanner({
      type: "info",
      title: "Feature Shell Ready (Role 1)",
      message: "This feature slice will be implemented by Role 1 (GET /api/v1/models and /api/v1/models/performance).",
    })
  );

  container.appendChild(content);
}

export function destroy() {
  // Teardown logic
}

