/**
 * Badge component for displaying categories, severities, and confidence levels.
 *
 * Uses approved vocabulary:
 * - Categories: data_quality, weather_transient, fleet_wide, inverter_specific, unexplained
 * - Severities: low, medium, high
 * - Confidence: low, medium, high
 */

const DISPLAY_NAMES = {
  data_quality: "Possible measurement irregularity",
  weather_transient: "Weather-driven variation",
  fleet_wide: "Plant-wide deviation",
  inverter_specific: "Candidate for inspection",
  unexplained: "Unexplained deviation",
  shortfall: "Shortfall",
  surplus: "Surplus",
};

export function createBadge(label, type = "category") {
  const span = document.createElement("span");
  span.className = `badge badge-${type} badge-${label.toLowerCase()}`;
  span.textContent = DISPLAY_NAMES[label] || label;
  return span;
}

