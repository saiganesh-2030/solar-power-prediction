/**
 * Global filter bar component.
 * Allows switching between plants, setting date ranges, and toggling
 * "Unseen test period only".
 */

import { filterStore } from "../state/filters.js";

export function renderFilterBar(container) {
  const bar = document.createElement("div");
  bar.className = "filter-bar";

  const current = filterStore.getFilters();

  // 1. Plant Selector
  const plantGroup = document.createElement("div");
  plantGroup.className = "filter-group";
  const plantLabel = document.createElement("label");
  plantLabel.textContent = "Plant:";
  const plantSelect = document.createElement("select");
  plantSelect.className = "filter-select";
  
  [1, 2].forEach((p) => {
    const opt = document.createElement("option");
    opt.value = String(p);
    opt.textContent = `Plant ${p}`;
    if (p === current.plant) opt.selected = true;
    plantSelect.appendChild(opt);
  });

  plantSelect.addEventListener("change", (e) => {
    filterStore.setFilters({ plant: parseInt(e.target.value, 10) });
  });

  plantGroup.appendChild(plantLabel);
  plantGroup.appendChild(plantSelect);
  bar.appendChild(plantGroup);

  // 2. Start Date
  const startGroup = document.createElement("div");
  startGroup.className = "filter-group";
  const startLabel = document.createElement("label");
  startLabel.textContent = "Start:";
  const startInput = document.createElement("input");
  startInput.type = "date";
  startInput.className = "filter-input";
  if (current.start) startInput.value = current.start;
  startInput.addEventListener("change", (e) => {
    filterStore.setFilters({ start: e.target.value || null });
  });
  startGroup.appendChild(startLabel);
  startGroup.appendChild(startInput);
  bar.appendChild(startGroup);

  // 3. End Date
  const endGroup = document.createElement("div");
  endGroup.className = "filter-group";
  const endLabel = document.createElement("label");
  endLabel.textContent = "End:";
  const endInput = document.createElement("input");
  endInput.type = "date";
  endInput.className = "filter-input";
  if (current.end) endInput.value = current.end;
  endInput.addEventListener("change", (e) => {
    filterStore.setFilters({ end: e.target.value || null });
  });
  endGroup.appendChild(endLabel);
  endGroup.appendChild(endInput);
  bar.appendChild(endGroup);

  // 4. "Unseen test period only" switch
  const testGroup = document.createElement("div");
  testGroup.className = "filter-group filter-checkbox-group";
  const testCheck = document.createElement("input");
  testCheck.type = "checkbox";
  testCheck.id = "unseen-test-only";
  testCheck.checked = current.testOnly;
  testCheck.addEventListener("change", (e) => {
    filterStore.setFilters({ testOnly: e.target.checked });
  });

  const testLabel = document.createElement("label");
  testLabel.htmlFor = "unseen-test-only";
  testLabel.textContent = "Unseen test period only";

  testGroup.appendChild(testCheck);
  testGroup.appendChild(testLabel);
  bar.appendChild(testGroup);

  container.appendChild(bar);

  // Sync back if external change happens
  const unsubscribe = filterStore.subscribe((filters) => {
    if (parseInt(plantSelect.value, 10) !== filters.plant) {
      plantSelect.value = String(filters.plant);
    }
    if (startInput.value !== (filters.start || "")) {
      startInput.value = filters.start || "";
    }
    if (endInput.value !== (filters.end || "")) {
      endInput.value = filters.end || "";
    }
    if (testCheck.checked !== filters.testOnly) {
      testCheck.checked = filters.testOnly;
    }
  });

  return unsubscribe;
}

