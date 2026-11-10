/**
 * Heatmap grid renderer for date x hour energy matrix.
 *
 * References:
 * - docs/ARCHITECTURE_AND_API.md section 7
 */

export function createHeatmap({ xLabels = [], yLabels = [], dataMatrix = [] } = {}) {
  const container = document.createElement("div");
  container.className = "heatmap-container";

  if (!dataMatrix || dataMatrix.length === 0) {
    const empty = document.createElement("div");
    empty.className = "text-muted";
    empty.textContent = "No matrix data available";
    container.appendChild(empty);
    return container;
  }

  const grid = document.createElement("div");
  grid.className = "heatmap-grid";
  grid.style.display = "grid";
  grid.style.gridTemplateColumns = `auto repeat(${xLabels.length}, 1fr)`;
  grid.style.gap = "2px";

  // Render corner cell
  const corner = document.createElement("div");
  grid.appendChild(corner);

  // Render header row
  xLabels.forEach((x) => {
    const headerCell = document.createElement("div");
    headerCell.className = "heatmap-header-cell";
    headerCell.textContent = x;
    grid.appendChild(headerCell);
  });

  // Render rows
  yLabels.forEach((y, rIdx) => {
    const rowLabel = document.createElement("div");
    rowLabel.className = "heatmap-row-label";
    rowLabel.textContent = y;
    grid.appendChild(rowLabel);

    xLabels.forEach((_, cIdx) => {
      const cell = document.createElement("div");
      cell.className = "heatmap-cell";
      const val = dataMatrix[rIdx]?.[cIdx] ?? 0;
      cell.title = `${y} - ${xLabels[cIdx]}: ${val}`;
      cell.textContent = val > 0 ? String(Math.round(val)) : "";
      grid.appendChild(cell);
    });
  });

  container.appendChild(grid);
  return container;
}

