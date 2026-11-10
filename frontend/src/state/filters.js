/**
 * Global reactive filter store.
 * Synchronizes with URL query parameters so filtered views are easily shareable.
 *
 * State:
 * - plant (1 | 2)
 * - start (YYYY-MM-DD | null)
 * - end (YYYY-MM-DD | null)
 * - testOnly (boolean)
 *
 * References:
 * - docs/ARCHITECTURE_AND_API.md section 7
 * - docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
 */

class FilterStore {
  constructor() {
    this.listeners = new Set();
    this.state = this._readFromUrl();

    // Listen to popstate (browser back/forward)
    window.addEventListener("popstate", () => {
      this.state = this._readFromUrl();
      this._notify();
    });
  }

  _readFromUrl() {
    // Read query parameters from URL or hash query
    const hash = window.location.hash;
    const queryPart = hash.includes("?")
      ? hash.split("?")[1]
      : window.location.search.replace(/^\?/, "");
    const params = new URLSearchParams(queryPart);

    const plant = parseInt(params.get("plant") || "1", 10);
    const start = params.get("start") || null;
    const end = params.get("end") || null;
    const testOnly = params.get("testOnly") === "true";

    return {
      plant: plant === 2 ? 2 : 1,
      start,
      end,
      testOnly,
    };
  }

  _syncToUrl() {
    const hashParts = window.location.hash.split("?");
    const route = hashParts[0] || "#/";

    const params = new URLSearchParams();
    params.set("plant", String(this.state.plant));
    if (this.state.start) params.set("start", this.state.start);
    if (this.state.end) params.set("end", this.state.end);
    if (this.state.testOnly) params.set("testOnly", "true");

    const newHash = `${route}?${params.toString()}`;
    if (window.location.hash !== newHash) {
      window.history.replaceState(null, "", newHash);
    }
  }

  _notify() {
    const snapshot = this.getFilters();
    for (const listener of this.listeners) {
      try {
        listener(snapshot);
      } catch (err) {
        console.error("Filter listener error:", err);
      }
    }
  }

  getFilters() {
    return { ...this.state };
  }

  setFilters(partial) {
    let changed = false;
    for (const [key, val] of Object.entries(partial)) {
      if (this.state[key] !== val) {
        this.state[key] = val;
        changed = true;
      }
    }
    if (changed) {
      this._syncToUrl();
      this._notify();
    }
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}

export const filterStore = new FilterStore();

