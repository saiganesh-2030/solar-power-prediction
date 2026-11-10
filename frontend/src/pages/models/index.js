/**
 * Feature 6 — Model Performance (Owned by Role 1)
 *
 * Displays:
 * 1. Selected model badge with explicit selection reason.
 * 2. Model comparison table with toggles for Daylight-only (primary) vs All-hours, and Validation vs Test.
 * 3. Model RMSE comparison bar chart.
 * 4. Walk-forward cross validation stability breakdown.
 * 5. Binned performance across irradiance levels and day types (clear vs cloudy).
 * 6. Residual distribution diagnostic histogram and bias check.
 * 7. Permutation feature importance rankings.
 *
 * References:
 * - docs/PROJECT_HANDBOOK.md section 5 (Feature 6)
 * - docs/roles/ROLE_1_ML_ENGINEER.md
 * - docs/DATA_AND_ML_SPEC.md sections 6 & 7
 */

import { get } from "../../api/client.js";
import { filterStore } from "../../state/filters.js";
import { createBanner } from "../../components/banner.js";
import { createSkeleton } from "../../components/skeleton.js";
import { createDataTable } from "../../components/dataTable.js";
import { createBarChart } from "../../components/barChart.js";
import { createLineChart } from "../../components/lineChart.js";

let unsubscribeFilters = null;
let currentChart = null;

export async function render(container, ctx) {
  container.innerHTML = "";

  const header = document.createElement("header");
  header.className = "page-header";
  header.innerHTML = `
    <h2>Model Performance & Diagnostics</h2>
    <p class="text-muted">Rigorous out-of-sample evaluation on unseen chronological days. Daylight metrics are primary.</p>
  `;
  container.appendChild(header);

  const contentArea = document.createElement("div");
  contentArea.className = "page-content";
  container.appendChild(contentArea);

  async function loadPerformanceData() {
    contentArea.innerHTML = "";
    contentArea.appendChild(createSkeleton({ lines: 6 }));

    const plant = filterStore.getFilters().plant;

    try {
      const [perfRes, resRes, featRes] = await Promise.all([
        get("/models/performance", { plant }),
        get("/models/residuals", { plant, split: "test" }),
        get("/models/feature-importance", { plant }),
      ]);

      const perf = perfRes.data;
      const residuals = resRes.data;
      const feats = featRes.data || [];

      contentArea.innerHTML = "";

      // 1. Selection Reason Banner
      const selectedPanel = document.createElement("div");
      selectedPanel.className = "panel";
      selectedPanel.style.borderLeft = "4px solid var(--accent)";
      selectedPanel.innerHTML = `
        <div style="display: flex; align-items: baseline; gap: 0.75rem; flex-wrap: wrap;">
          <h3>Selected Model: <span style="color: var(--accent);">${perf.selected_model}</span></h3>
          <span class="badge badge-category">Capacity Proxy: ${perf.capacity_proxy_kw} kW</span>
        </div>
        <p style="margin-top: 0.5rem; font-size: 0.9rem;"><strong>Selection Criteria:</strong> ${perf.selection_reason}</p>
      `;
      contentArea.appendChild(selectedPanel);

      // 2. Metrics Table with Interactive Toggles
      const tablePanel = document.createElement("div");
      tablePanel.className = "panel";

      let viewSplit = "test"; // "val" or "test"
      let viewMode = "daylight"; // "daylight" or "all"

      function renderMetricsView() {
        tablePanel.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1rem;">
            <div>
              <h3>Candidate Models Benchmark</h3>
              <p class="text-muted">Daylight metrics (G >= 0.05 kW/m²) remove zero-inflation from night rows.</p>
            </div>
            <div style="display: flex; gap: 0.75rem; align-items: center;">
              <div style="display: flex; border: 1px solid var(--border-color); border-radius: var(--radius); overflow: hidden;">
                <button id="btn-split-test" class="btn ${viewSplit === 'test' ? 'active' : 'btn-secondary'}" style="border-radius: 0; padding: 0.3rem 0.65rem;">Unseen Test</button>
                <button id="btn-split-val" class="btn ${viewSplit === 'val' ? 'active' : 'btn-secondary'}" style="border-radius: 0; padding: 0.3rem 0.65rem;">Validation</button>
              </div>
              <div style="display: flex; border: 1px solid var(--border-color); border-radius: var(--radius); overflow: hidden;">
                <button id="btn-mode-daylight" class="btn ${viewMode === 'daylight' ? 'active' : 'btn-secondary'}" style="border-radius: 0; padding: 0.3rem 0.65rem;">Daylight Only</button>
                <button id="btn-mode-all" class="btn ${viewMode === 'all' ? 'active' : 'btn-secondary'}" style="border-radius: 0; padding: 0.3rem 0.65rem;">All Hours</button>
              </div>
            </div>
          </div>
          <div id="metrics-table-mount"></div>
        `;

        // Wire buttons
        tablePanel.querySelector("#btn-split-test").addEventListener("click", () => { viewSplit = "test"; renderMetricsView(); });
        tablePanel.querySelector("#btn-split-val").addEventListener("click", () => { viewSplit = "val"; renderMetricsView(); });
        tablePanel.querySelector("#btn-mode-daylight").addEventListener("click", () => { viewMode = "daylight"; renderMetricsView(); });
        tablePanel.querySelector("#btn-mode-all").addEventListener("click", () => { viewMode = "all"; renderMetricsView(); });

        const rows = (perf.models || []).map((m) => {
          const splitData = m[viewSplit] || {};
          const modeData = splitData[viewMode] || {};
          return {
            name: m.name === perf.selected_model ? `${m.name} (Selected)` : m.name,
            mae: modeData.mae ?? "--",
            rmse: modeData.rmse ?? "--",
            r2: modeData.r2 ?? "--",
            wape: modeData.wape !== undefined ? `${(modeData.wape * 100).toFixed(1)}%` : "--",
            nmae: modeData.nmae !== undefined ? `${(modeData.nmae * 100).toFixed(1)}%` : "--",
          };
        });

        const tableMount = tablePanel.querySelector("#metrics-table-mount");
        tableMount.appendChild(createDataTable({
          columns: [
            { key: "name", label: "Model Architecture" },
            { key: "rmse", label: "RMSE (kW)" },
            { key: "mae", label: "MAE (kW)" },
            { key: "r2", label: "R²" },
            { key: "wape", label: "WAPE" },
            { key: "nmae", label: "Normalized MAE" },
          ],
          rows,
        }));
      }

      renderMetricsView();
      contentArea.appendChild(tablePanel);

      // 3. Grid for Diagnostics: Residual Plots (Histogram & Scatter)
      const resGrid = document.createElement("div");
      resGrid.style.display = "grid";
      resGrid.style.gridTemplateColumns = "repeat(auto-fit, minmax(320px, 1fr))";
      resGrid.style.gap = "1rem";
      resGrid.style.marginBottom = "1.5rem";

      // Residual Distribution Panel
      const resPanel = document.createElement("div");
      resPanel.className = "panel";
      resPanel.innerHTML = `
        <h3>Residual Distribution (Test Period)</h3>
        <p class="text-muted">Mean: <strong>${residuals.mean_residual_kw} kW</strong> | Std: <strong>${residuals.std_residual_kw} kW</strong> (Near zero indicates unbiased prediction)</p>
        <div id="res-hist-container" style="height: 240px; margin-top: 1rem;"></div>
      `;
      resGrid.appendChild(resPanel);

      // Residual vs Irradiance Diagnostic Panel
      const resScatterPanel = document.createElement("div");
      resScatterPanel.className = "panel";
      resScatterPanel.innerHTML = `
        <h3>Residual vs Irradiance Diagnostic</h3>
        <p class="text-muted">Check for systematic bias across solar irradiance levels (kW/m²).</p>
        <div id="res-scatter-container" style="height: 240px; margin-top: 1rem;"></div>
      `;
      resGrid.appendChild(resScatterPanel);
      contentArea.appendChild(resGrid);

      // Render Residuals Histogram
      const resHistContainer = resPanel.querySelector("#res-hist-container");
      if (residuals.histogram && residuals.histogram.length > 0) {
        const resCanvas = document.createElement("canvas");
        resHistContainer.appendChild(resCanvas);
        createBarChart(resCanvas, {
          labels: residuals.histogram.map((b) => `${b.bin_start} to ${b.bin_end}`),
          datasets: [{
            label: "Interval Count",
            data: residuals.histogram.map((b) => b.count),
            backgroundColor: "rgba(37, 99, 235, 0.7)",
            borderColor: "#2563eb",
            borderWidth: 1,
          }],
        });
      }

      // Render Residual vs Irradiance Plot
      const resScatterContainer = resScatterPanel.querySelector("#res-scatter-container");
      if (residuals.sample_points && residuals.sample_points.length > 0) {
        const sortedPoints = [...residuals.sample_points].sort((a, b) => a.irradiation_kw_m2 - b.irradiation_kw_m2);
        const scatterCanvas = document.createElement("canvas");
        resScatterContainer.appendChild(scatterCanvas);
        createLineChart(scatterCanvas, {
          labels: sortedPoints.map((p) => p.irradiation_kw_m2.toFixed(2)),
          datasets: [
            {
              label: "Residual Error (kW)",
              data: sortedPoints.map((p) => p.residual_kw),
              borderColor: "#0284c7",
              backgroundColor: "rgba(2, 132, 199, 0.2)",
              borderWidth: 1.5,
              pointRadius: 3,
              pointHoverRadius: 5,
            },
            {
              label: "Zero Bias Baseline",
              data: sortedPoints.map(() => 0),
              borderColor: "rgba(239, 68, 68, 0.6)",
              borderDash: [4, 4],
              borderWidth: 1.5,
              pointRadius: 0,
            },
          ],
        });
      }

      // 4. Breakdowns: By Irradiation Bin & By Day Type
      const breakdownGrid = document.createElement("div");
      breakdownGrid.style.display = "grid";
      breakdownGrid.style.gridTemplateColumns = "repeat(auto-fit, minmax(320px, 1fr))";
      breakdownGrid.style.gap = "1rem";
      breakdownGrid.style.marginBottom = "1.5rem";

      // Irradiance Bin Panel
      const irrBinPanel = document.createElement("div");
      irrBinPanel.className = "panel";
      irrBinPanel.innerHTML = `
        <h3>Performance by Irradiance Bin (Test Daylight)</h3>
        <p class="text-muted">MAE across five standard irradiance intervals (kW/m²).</p>
        <div id="irr-bin-table-mount" style="margin-top: 0.75rem;"></div>
      `;
      const irrMount = irrBinPanel.querySelector("#irr-bin-table-mount");
      irrMount.appendChild(createDataTable({
        columns: [
          { key: "bin", label: "Irradiance Bin (kW/m²)" },
          { key: "model", label: "Model Architecture" },
          { key: "mae", label: "Daylight MAE (kW)" },
          { key: "n", label: "Sample Count" },
        ],
        rows: (perf.by_irradiation_bin || []).map((b) => ({
          bin: b.bin,
          model: b.model,
          mae: b.mae,
          n: b.n,
        })),
      }));
      breakdownGrid.appendChild(irrBinPanel);

      // Day Type Panel
      const dayTypePanel = document.createElement("div");
      dayTypePanel.className = "panel";
      dayTypePanel.innerHTML = `
        <h3>Performance by Day Type (Clear vs Cloudy)</h3>
        <p class="text-muted">MAE across clear, mixed, and cloudy days (Spec section 12).</p>
        <div id="day-type-table-mount" style="margin-top: 0.75rem;"></div>
      `;
      const dtMount = dayTypePanel.querySelector("#day-type-table-mount");
      dtMount.appendChild(createDataTable({
        columns: [
          { key: "day_type", label: "Day Classification" },
          { key: "model", label: "Model Architecture" },
          { key: "mae", label: "Daylight MAE (kW)" },
          { key: "n", label: "Interval Count" },
        ],
        rows: (perf.by_day_type || []).map((d) => ({
          day_type: d.day_type.toUpperCase(),
          model: d.model,
          mae: d.mae,
          n: d.n,
        })),
      }));
      breakdownGrid.appendChild(dayTypePanel);
      contentArea.appendChild(breakdownGrid);

      // 5. Permutation Feature Importance with Plain-Language Explanations
      const featPanel = document.createElement("div");
      featPanel.className = "panel";
      featPanel.style.marginBottom = "1.5rem";
      featPanel.innerHTML = `
        <h3>Permutation Feature Importance & Physical Explanations</h3>
        <p class="text-muted">Evaluated on unseen validation block rows (5 repeats, seed 42) with plain-language engineering explanations.</p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.25rem; margin-top: 1rem;">
          <div id="feat-chart-container" style="height: 260px;"></div>
          <div id="feat-table-mount"></div>
        </div>
      `;
      contentArea.appendChild(featPanel);

      // Render Feature Importance Chart
      const featContainer = featPanel.querySelector("#feat-chart-container");
      if (feats.length > 0) {
        const featCanvas = document.createElement("canvas");
        featContainer.appendChild(featCanvas);
        createBarChart(featCanvas, {
          labels: feats.slice(0, 6).map((f) => f.feature),
          datasets: [{
            label: "Normalized Importance",
            data: feats.slice(0, 6).map((f) => f.importance),
            backgroundColor: "rgba(147, 51, 234, 0.7)",
            borderColor: "#9333ea",
            borderWidth: 1,
          }],
        });

        // Render Explanations Table
        const featTableMount = featPanel.querySelector("#feat-table-mount");
        featTableMount.appendChild(createDataTable({
          columns: [
            { key: "feature", label: "Feature" },
            { key: "importance_pct", label: "Share" },
            { key: "explanation", label: "Physical & Engineering Explanation" },
          ],
          rows: feats.slice(0, 6).map((f) => ({
            feature: f.feature,
            importance_pct: `${(f.importance * 100).toFixed(1)}%`,
            explanation: f.explanation || "Domain weather covariate",
          })),
        }));
      }

      // 6. Walk-Forward Stability Rolling-Fold Chart & Table
      if (perf.walk_forward && perf.walk_forward.length > 0) {
        const wfPanel = document.createElement("div");
        wfPanel.className = "panel";
        wfPanel.innerHTML = `
          <h3>Walk-Forward Stability (Expanding Window Folds)</h3>
          <p class="text-muted">Evaluating rolling stability across consecutive chronological out-of-sample test windows inside the train period.</p>
          <div id="wf-chart-container" style="height: 220px; margin-top: 1rem; margin-bottom: 1rem;"></div>
          <div id="wf-table-mount"></div>
        `;
        contentArea.appendChild(wfPanel);

        // Render Rolling-Fold Chart
        const wfChartContainer = wfPanel.querySelector("#wf-chart-container");
        const wfCanvas = document.createElement("canvas");
        wfChartContainer.appendChild(wfCanvas);
        createBarChart(wfCanvas, {
          labels: perf.walk_forward.map((f) => `Fold ${f.fold} (${f.test_range[0].slice(5)})`),
          datasets: [{
            label: "Daylight RMSE (kW)",
            data: perf.walk_forward.map((f) => f.daylight_rmse),
            backgroundColor: "rgba(16, 185, 129, 0.7)",
            borderColor: "#10b981",
            borderWidth: 1,
          }],
        });

        // Render Table
        const wfMount = wfPanel.querySelector("#wf-table-mount");
        wfMount.appendChild(createDataTable({
          columns: [
            { key: "fold", label: "Fold #" },
            { key: "train_end", label: "Train Window End" },
            { key: "test_range", label: "Out-of-Sample Window" },
            { key: "model", label: "Model Architecture" },
            { key: "daylight_rmse", label: "Daylight RMSE (kW)" },
          ],
          rows: perf.walk_forward.map((f) => ({
            fold: f.fold,
            train_end: f.train_end,
            test_range: `${f.test_range[0]} to ${f.test_range[1]}`,
            model: f.model,
            daylight_rmse: f.daylight_rmse,
          })),
        }));
      }

    } catch (err) {
      contentArea.innerHTML = "";
      contentArea.appendChild(createBanner({
        type: "error",
        title: "Failed to Load Performance Metrics",
        message: err.message || "An error occurred fetching model metrics",
        onRetry: loadPerformanceData,
      }));
    }
  }

  unsubscribeFilters = filterStore.subscribe(() => {
    loadPerformanceData();
  });

  await loadPerformanceData();
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
