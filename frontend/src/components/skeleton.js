/**
 * Skeleton loader placeholder generator.
 */

export function createSkeleton({ lines = 3, height = "20px" } = {}) {
  const container = document.createElement("div");
  container.className = "skeleton-container";

  for (let i = 0; i < lines; i++) {
    const line = document.createElement("div");
    line.className = "skeleton-line";
    line.style.height = height;
    line.style.width = i === lines - 1 ? "60%" : "100%";
    container.appendChild(line);
  }

  return container;
}

