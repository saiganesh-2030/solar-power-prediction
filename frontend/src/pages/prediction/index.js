/**
 * Feature 2 — Solar Power Prediction (Owned by Role 1)
 *
 * Provides:
 * 1. Interactive What-if estimation panel (irradiance, temperatures) returning
 *    expected AC power per inverter with 90% conformal prediction interval and plant estimate.
 * 2. Actual vs Estimated power time series view with inverter selector and normal band edges.
 *
 * References:
 * - docs/PROJECT_HANDBOOK.md section 5 (Feature 2)
 * - docs/roles/ROLE_1_ML_ENGINEER.md
 * - docs/ARCHITECTURE_AND_API.md section 6
 */

import { get, post } from "../../api/client.js";
import { filterStore } from "../../state/filters.js";
import { createBanner } from "../../components/banner.js";
import { createSkeleton } from "../../components/skeleton.js";
import { createKpiCard } from "../../components/kpiCard.js";
import { createLineChart } from "../../components/lineChart.js";

let unsubscribeFilters = null;
let currentChart = null;

export async function render(container, ctx) {
  container.innerHTML = "";

  const header = document.createElement("header");
  header.className = "page-header";
  header.innerHTML = `
    <h2>Solar Power Prediction</h2>
    <p class="text-muted">Estimate expected AC power from ambient weather conditions and compare actual generation against calibrated expectations.</p>
  `;
  container.appendChild(header);

  const contentArea = document.createElement("div");
  contentArea.className = "page-content";
  container.appendChild(contentArea);

  // 1. What-If Panel Section
  const whatIfPanel = document.createElement("div");
  whatIfPanel.className = "panel";
  whatIfPanel.innerHTML = `
    <h3>What-If Expected Power Estimator</h3>
    <p class="text-muted">Evaluate what a fleet-normal inverter and plant should produce under specified environmental conditions.</p>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
      <div class="filter-group" style="flex-direction: column; align-items: flex-start;">
        <label>Irradiance (kW/m²):</label>
        <input id="whatif-irr" type="number" min="0" max="1.5" step="0.05" value="0.85" class="filter-input" style="width: 100%;">
      </div>
      <div class="filter-group" style="flex-direction: column; align-items: flex-start;">
        <label>Module Temp (°C):</label>
        <input id="whatif-modtemp" type="number" min="-10" max="90" step="1" value="52.0" class="filter-input" style="width: 100%;">
      </div>
      <div class="filter-group" style="flex-direction: column; align-items: flex-start;">
        <label>Ambient Temp (°C):</label>
        <input id="whatif-ambtemp" type="number" min="-10" max="60" step="1" value="33.0" class="filter-input" style="width: 100%;">
      </div>
      <div class="filter-group" style="flex-direction: column; align-items: flex-start;">
        <label>Model Architecture:</label>
        <select id="whatif-model" class="filter-select" style="width: 100%;">
          <option value="selected">Selected Model</option>
          <option value="physics_baseline">Physics Baseline</option>
          <option value="ridge_poly">Polynomial Ridge</option>
          <option value="hist_gradient_boosting">Hist Gradient Boosting</option>
          <option value="random_forest">Random Forest</option>
        </select>
      </div>
    </div>
    
    <div style="margin-top: 1rem;">
      <button id="whatif-submit" class="btn" style="background: var(--accent); color: white;">Calculate Expected Power</button>
    </div>

    <div id="whatif-results" style="margin-top: 1.25rem;"></div>
  `;
  contentArea.appendChild(whatIfPanel);

  // 2. Time Series Actual vs Expected Panel
  const tsPanel = document.createElement("div");
  tsPanel.className = "panel";
  tsPanel.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
      <div>
        <h3>Actual vs Expected Power Over Time</h3>
        <p class="text-muted">Generation tracking with shaded normal prediction interval (calibrated on unseen validation days).</p>
      </div>
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <label style="font-size: 0.85rem; font-weight: 500;">Inverter:</label>
        <select id="ts-inverter-select" class="filter-select">
          <option value="">Plant Aggregate (Total)</option>
        </select>
      </div>
    </div>
    <div id="ts-chart-container" style="height: 380px; margin-top: 1rem; position: relative;"></div>
    <p class="text-muted" style="margin-top: 0.5rem; font-size: 0.8rem;">
      <strong>How to read this chart:</strong> The solid blue line shows actual AC power; the dashed purple line shows the model's expectation. The shaded band marks the normal expected range.
    </p>
  `;
  contentArea.appendChild(tsPanel);

  // Setup What-If Click Handler
  const submitBtn = whatIfPanel.querySelector("#whatif-submit");
  const resultsDiv = whatIfPanel.querySelector("#whatif-results");

  async function handleWhatIf() {
    const irrInput = whatIfPanel.querySelector("#whatif-irr");
    const modInput = whatIfPanel.querySelector("#whatif-modtemp");
    const ambInput = whatIfPanel.querySelector("#whatif-ambtemp");
    const modelChoice = whatIfPanel.querySelector("#whatif-model").value;
    const currentPlant = filterStore.getFilters().plant;

    const irr = parseFloat(irrInput.value);
    const mod = parseFloat(modInput.value);
    const amb = parseFloat(ambInput.value);

    // Client-side range validation per Architecture section 6
    if (isNaN(irr) || irr < 0.0 || irr > 1.5) {
      resultsDiv.innerHTML = "";
      resultsDiv.appendChild(createBanner({
        type: "warning",
        title: "Validation Error",
        message: "Irradiance must be between 0.0 and 1.5 kW/m².",
      }));
      return;
    }
    if (isNaN(mod) || mod < -10.0 || mod > 90.0) {
      resultsDiv.innerHTML = "";
      resultsDiv.appendChild(createBanner({
        type: "warning",
        title: "Validation Error",
        message: "Module temperature must be between -10°C and 90°C.",
      }));
      return;
    }
    if (isNaN(amb) || amb < -10.0 || amb > 60.0) {
      resultsDiv.innerHTML = "";
      resultsDiv.appendChild(createBanner({
        type: "warning",
        title: "Validation Error",
        message: "Ambient temperature must be between -10°C and 60°C.",
      }));
      return;
    }

    resultsDiv.innerHTML = "";
    resultsDiv.appendChild(createSkeleton({ lines: 2 }));

    try {
      const payload = {
        plant: currentPlant,
        timestamp: "2020-06-10T12:00:00",
        irradiation_kw_m2: irr,
        module_temp_c: mod,
        ambient_temp_c: amb,
        model: modelChoice,
      };

      const res = await post("/predict", payload);
      const d = res.data;
      resultsDiv.innerHTML = "";

      const resGrid = document.createElement("div");
      resGrid.className = "kpi-grid";
      resGrid.style.marginBottom = "0.5rem";

      resGrid.appendChild(createKpiCard({
        title: "Per-Inverter Expected",
        value: d.ac_kw_per_inverter,
        unit: "kW",
        subtitle: `Model: ${d.model_name}`,
      }));

      resGrid.appendChild(createKpiCard({
        title: "90% Prediction Interval",
        value: `${d.interval_lo_kw} – ${d.interval_hi_kw}`,
        unit: "kW",
        subtitle: "Conformal calibration bounds",
      }));

      resGrid.appendChild(createKpiCard({
        title: "Plant Total Estimate",
        value: d.plant_ac_kw_estimate.toLocaleString(),
        unit: "kW",
        subtitle: `Fleet normal across ${d.n_inverters} inverters`,
      }));

      resultsDiv.appendChild(resGrid);

      if (d.warnings && d.warnings.length > 0) {
        const warnBox = createBanner({
          type: "info",
          title: "Operating Conditions Notice",
          message: d.warnings.join(" | "),
        });
        resultsDiv.appendChild(warnBox);
      }
    } catch (err) {
      resultsDiv.innerHTML = "";
      resultsDiv.appendChild(createBanner({
        type: "error",
        title: "Calculation Error",
        message: err.message || "Failed to calculate prediction",
      }));
    }
  }

  submitBtn.addEventListener("click", handleWhatIf);
  // Run initial calculation
  handleWhatIf();

  // Load Inverter options into dropdown
  const invSelect = tsPanel.querySelector("#ts-inverter-select");
  try {
    const metaRes = await get("/meta");
    const pStr = String(filterStore.getFilters().plant);
    const inverters = metaRes.data?.inverters?.[pStr] || [];
    inverters.forEach((inv) => {
      const opt = document.createElement("option");
      opt.value = inv;
      opt.textContent = `Inverter ${inv}`;
      invSelect.appendChild(opt);
    });
  } catch {
    // Dropdown remains with plant aggregate option
  }

  // Load Time Series Data
  async function loadTimeSeries() {
    const chartContainer = tsPanel.querySelector("#ts-chart-container");
    chartContainer.innerHTML = "";
    chartContainer.appendChild(createSkeleton({ lines: 5 }));

    const filters = filterStore.getFilters();
    const query = {
      plant: filters.plant,
      start: filters.start || undefined,
      end: filters.end || undefined,
      split: filters.testOnly ? "test" : undefined,
      inverter: invSelect.value || undefined,
    };

    try {
      const res = await get("/predictions/timeseries", query);
      const d = res.data;
      chartContainer.innerHTML = "";

      if (!d || !d.t || d.t.length === 0) {
        chartContainer.appendChild(createBanner({
          type: "info",
          title: "No Series Data",
          message: "No time-series rows match the selected filters.",
        }));
        return;
      }

      const canvas = document.createElement("canvas");
      chartContainer.appendChild(canvas);

      // Clean timestamps for chart display (MM-DD HH:MM)
      const labels = d.t.map((t) => t.slice(5, 16).replace("T", " "));

      if (currentChart) {
        currentChart.destroy();
        currentChart = null;
      }

      currentChart = createLineChart(canvas, {
        labels,
        datasets: [
          {
            label: "Actual AC Power (kW)",
            data: d.actual_kw,
            borderColor: "#2563eb",
            backgroundColor: "#2563eb",
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
          {
            label: "Expected AC Power (kW)",
            data: d.pred_kw,
            borderColor: "#9333ea",
            borderDash: [5, 4],
            backgroundColor: "#9333ea",
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
          {
            label: "Normal Upper Band (kW)",
            data: d.band_hi_kw,
            borderColor: "rgba(147, 51, 234, 0.2)",
            backgroundColor: "rgba(147, 51, 234, 0.08)",
            borderWidth: 1,
            pointRadius: 0,
            fill: "+1",
          },
          {
            label: "Normal Lower Band (kW)",
            data: d.band_lo_kw,
            borderColor: "rgba(147, 51, 234, 0.2)",
            backgroundColor: "rgba(147, 51, 234, 0.08)",
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
          },
        ],
      });
    } catch (err) {
      chartContainer.innerHTML = "";
      chartContainer.appendChild(createBanner({
        type: "error",
        title: "Failed to Load Time Series",
        message: err.message || "An error occurred fetching predictions",
        onRetry: loadTimeSeries,
      }));
    }
  }

  invSelect.addEventListener("change", loadTimeSeries);
  unsubscribeFilters = filterStore.subscribe(() => {
    loadTimeSeries();
  });

  loadTimeSeries();
}

export function destroy() {
  if (unsubscribeFilters) {
    unsubscribeFilters();
    unsubscribeFilters = null;
  }
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }
}
