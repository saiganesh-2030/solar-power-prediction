/**
 * Feature 1 — Dashboard Overview (Owned by Role 4)
 *
 * Displays:
 * - Actual vs predicted generation (kWh)
 * - Overall deviation %
 * - Anomaly event counts
 * - Estimated shortfall range (conservative, central, upper)
 * - Model test performance metrics
 * - Data quality score
 * - Top candidates for inspection (never diagnosed without external evidence)
 *
 * References:
 * - docs/PROJECT_HANDBOOK.md section 5 (Feature 1)
 * - docs/ARCHITECTURE_AND_API.md section 6
 */

import { get } from "../../api/client.js";
import { filterStore } from "../../state/filters.js";
import { createBanner } from "../../components/banner.js";
import { createSkeleton } from "../../components/skeleton.js";
import { createKpiCard } from "../../components/kpiCard.js";

let unsubscribeFilters = null;

export async function render(container, ctx) {
  container.innerHTML = "";

  const pageHeader = document.createElement("header");
  pageHeader.className = "page-header";
  pageHeader.innerHTML = `
    <h2>Dashboard Overview</h2>
    <p class="text-muted">High-level plant generation, estimated expected output, and performance deviation summary.</p>
  `;
  container.appendChild(pageHeader);

  const contentArea = document.createElement("div");
  contentArea.className = "page-content";
  container.appendChild(contentArea);

  async function loadData() {
    contentArea.innerHTML = "";
    contentArea.appendChild(createSkeleton({ lines: 4 }));

    const filters = filterStore.getFilters();
    const query = {
      plant: filters.plant,
      start: filters.start || undefined,
      end: filters.end || undefined,
      split: filters.testOnly ? "test" : undefined,
    };

    try {
      const response = await get("/dashboard/overview", query);
      const data = response.data;
      contentArea.innerHTML = "";

      if (!data || !data.kpis) {
        contentArea.appendChild(
          createBanner({
            type: "info",
            title: "No Data Available",
            message: "No generation records match the current filter selection.",
          })
        );
        return;
      }

      // Render KPIs Grid
      const grid = document.createElement("div");
      grid.className = "kpi-grid";

      grid.appendChild(
        createKpiCard({
          title: "Actual Generation",
          value: Math.round(data.kpis.actual_kwh).toLocaleString(),
          unit: "kWh",
          subtitle: "Measured solar output",
        })
      );

      grid.appendChild(
        createKpiCard({
          title: "Expected Generation",
          value: Math.round(data.kpis.predicted_kwh).toLocaleString(),
          unit: "kWh",
          subtitle: `Model: ${data.kpis.model?.name || "Selected"}`,
        })
      );

      grid.appendChild(
        createKpiCard({
          title: "Deviation",
          value: `${data.kpis.deviation_pct > 0 ? "+" : ""}${data.kpis.deviation_pct}%`,
          status: data.kpis.deviation_pct < -5 ? "warning" : "normal",
          subtitle: "vs fleet-normal expectation",
        })
      );

      grid.appendChild(
        createKpiCard({
          title: "Deviation Events",
          value: data.kpis.anomaly_events?.total ?? 0,
          subtitle: `${data.kpis.anomaly_events?.shortfall ?? 0} shortfall, ${data.kpis.anomaly_events?.surplus ?? 0} surplus`,
        })
      );

      grid.appendChild(
        createKpiCard({
          title: "Data Quality Score",
          value: `${data.kpis.data_quality_score}%`,
          subtitle: "Rows with zero flags",
        })
      );

      contentArea.appendChild(grid);

      // Section: Inspection Candidates
      const candidatesSection = document.createElement("div");
      candidatesSection.className = "panel";
      candidatesSection.innerHTML = `
        <h3>Top Candidates for Inspection</h3>
        <p class="text-muted">Inverters with persistent shortfall relative to peer expectations (supporting evidence required for diagnosis).</p>
      `;

      if (data.top_candidates && data.top_candidates.length > 0) {
        const list = document.createElement("ul");
        list.className = "candidates-list";
        data.top_candidates.forEach((cand) => {
          const item = document.createElement("li");
          item.textContent = `Inverter ${cand.inverter_id} — ${cand.events} events, shortfall: ${Math.round(cand.shortfall_kwh)} kWh, peer ratio: ${cand.mean_peer_ratio} (Confidence: ${cand.confidence})`;
          list.appendChild(item);
        });
        candidatesSection.appendChild(list);
      } else {
        const emptyMsg = document.createElement("p");
        emptyMsg.className = "text-muted";
        emptyMsg.textContent = "No inspection candidates identified in the current window.";
        candidatesSection.appendChild(emptyMsg);
      }

      contentArea.appendChild(candidatesSection);
    } catch (err) {
      contentArea.innerHTML = "";
      contentArea.appendChild(
        createBanner({
          type: "error",
          title: "Unable to load dashboard data",
          message: err.message || "Failed to fetch data from API.",
          onRetry: loadData,
        })
      );
    }
  }

  unsubscribeFilters = filterStore.subscribe(() => {
    loadData();
  });

  await loadData();
}

export function destroy() {
  if (unsubscribeFilters) {
    unsubscribeFilters();
    unsubscribeFilters = null;
  }
}
