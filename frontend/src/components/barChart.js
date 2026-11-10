/**
 * Shared Bar Chart wrapper using Chart.js.
 *
 * References:
 * - docs/ARCHITECTURE_AND_API.md section 7
 */

import { Chart, BarController, BarElement, LinearScale, Title, Tooltip, Legend, CategoryScale } from "chart.js";

Chart.register(BarController, BarElement, LinearScale, Title, Tooltip, Legend, CategoryScale);

export function createBarChart(canvas, { labels = [], datasets = [], options = {} } = {}) {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.08)";
  const textColor = isDark ? "#cbd5e1" : "#475569";

  return new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: textColor },
        },
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { color: textColor },
        },
        y: {
          grid: { color: gridColor },
          ticks: { color: textColor },
        },
      },
      ...options,
    },
  });
}

