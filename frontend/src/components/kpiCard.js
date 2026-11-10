/**
 * KPI summary card component.
 */

export function createKpiCard({ title, value, unit = "", subtitle = "", status = "" }) {
  const card = document.createElement("div");
  card.className = `kpi-card ${status ? `kpi-${status}` : ""}`;

  const titleEl = document.createElement("div");
  titleEl.className = "kpi-title";
  titleEl.textContent = title;
  card.appendChild(titleEl);

  const valueWrap = document.createElement("div");
  valueWrap.className = "kpi-value-wrap";

  const valEl = document.createElement("span");
  valEl.className = "kpi-value";
  valEl.textContent = value !== null && value !== undefined ? String(value) : "--";
  valueWrap.appendChild(valEl);

  if (unit) {
    const unitEl = document.createElement("span");
    unitEl.className = "kpi-unit";
    unitEl.textContent = ` ${unit}`;
    valueWrap.appendChild(unitEl);
  }
  card.appendChild(valueWrap);

  if (subtitle) {
    const subEl = document.createElement("div");
    subEl.className = "kpi-subtitle";
    subEl.textContent = subtitle;
    card.appendChild(subEl);
  }

  return card;
}

