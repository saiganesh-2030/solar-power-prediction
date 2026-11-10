/**
 * Reusable Data Table component.
 * Renders data rows, handles empty states, and safely escapes cell contents.
 *
 * References:
 * - docs/ARCHITECTURE_AND_API.md section 7
 */

export function createDataTable({ columns = [], rows = [], emptyMessage = "No records to display" } = {}) {
  const container = document.createElement("div");
  container.className = "table-container";

  if (!rows || rows.length === 0) {
    const emptyEl = document.createElement("div");
    emptyEl.className = "text-muted";
    emptyEl.style.padding = "1rem";
    emptyEl.textContent = emptyMessage;
    container.appendChild(emptyEl);
    return container;
  }

  const table = document.createElement("table");
  table.className = "data-table";

  // Header
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col.label || col.key;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((col) => {
      const td = document.createElement("td");
      const val = row[col.key];
      if (col.render && typeof col.render === "function") {
        const rendered = col.render(val, row);
        if (typeof rendered === "string") {
          td.textContent = rendered;
        } else if (rendered instanceof HTMLElement) {
          td.appendChild(rendered);
        }
      } else {
        td.textContent = val !== null && val !== undefined ? String(val) : "--";
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  container.appendChild(table);
  return container;
}

