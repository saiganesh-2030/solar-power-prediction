/**
 * API Client module.
 * The ONLY place in the frontend that invokes the fetch API.
 *
 * Features:
 * - get(path, params) and post(path, body)
 * - Automatic query string serialization
 * - Standardized envelope parsing (data, meta)
 * - Typed ApiError
 * - Timeout handling and 1 automatic retry on GET failures
 * - Mock mode support (VITE_USE_MOCK=true or URL ?mock=true)
 *
 * References:
 * - docs/ARCHITECTURE_AND_API.md section 7
 * - docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
 */

export class ApiError extends Error {
  constructor(message, code = "internal_error", status = 500, details = null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

const DEFAULT_BASE_URL = import.meta.env?.VITE_API_BASE || "http://localhost:8000/api/v1";

export function isMockMode() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("mock") === "true") return true;
  return import.meta.env?.VITE_USE_MOCK === "true";
}

function buildQueryString(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== "") {
      query.append(key, String(val));
    }
  }
  const str = query.toString();
  return str ? `?${str}` : "";
}

function getMockPath(path) {
  // Convert /dashboard/overview -> /mock/dashboard-overview.json
  const cleaned = path.replace(/^\/api\/v1\//, "").replace(/^\//, "");
  const slug = cleaned.replace(/\//g, "-") || "index";
  return `/mock/${slug}.json`;
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 8000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(id);
  }
}

export async function get(path, params = {}) {
  if (isMockMode()) {
    const mockFile = getMockPath(path);
    try {
      const res = await fetch(mockFile);
      if (!res.ok) {
        throw new ApiError(`Mock fixture not found: ${mockFile}`, "not_found", res.status);
      }
      const json = await res.json();
      return json;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(`Failed to load mock data: ${err.message}`, "not_found", 404);
    }
  }

  const base = DEFAULT_BASE_URL.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${base}${normalizedPath}${buildQueryString(params)}`;

  let lastError = null;
  // Try twice (initial request + 1 retry) for GET
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const response = await fetchWithTimeout(url, {
        method: "GET",
        headers: { "Accept": "application/json" },
      });

      const contentType = response.headers.get("content-type") || "";
      const isJson = contentType.includes("application/json");
      const body = isJson ? await response.json() : await response.text();

      if (!response.ok) {
        const errorObj = isJson && body.error ? body.error : {};
        throw new ApiError(
          errorObj.message || `Request failed with status ${response.status}`,
          errorObj.code || "internal_error",
          response.status,
          errorObj.details || null
        );
      }

      return body;
    } catch (err) {
      lastError = err;
      if (err.name === "AbortError") {
        lastError = new ApiError("Request timed out", "timeout", 408);
      }
      // Only retry if it's the first attempt and network or server error
      if (attempt === 0 && (!(err instanceof ApiError) || err.status >= 500)) {
        await new Promise((r) => setTimeout(r, 400));
        continue;
      }
      break;
    }
  }

  throw lastError instanceof ApiError
    ? lastError
    : new ApiError(lastError?.message || "Network request failed", "network_error", 0);
}

export async function post(path, body = {}) {
  if (isMockMode()) {
    // In mock mode, return mock response or stub
    const mockFile = getMockPath(path);
    try {
      const res = await fetch(mockFile);
      if (res.ok) return await res.json();
    } catch {
      // Fall through to simulated success
    }
    return { data: { simulated: true }, meta: { source: "mock" } };
  }

  const base = DEFAULT_BASE_URL.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${base}${normalizedPath}`;

  try {
    const response = await fetchWithTimeout(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(body),
    });

    const isJson = (response.headers.get("content-type") || "").includes("application/json");
    const json = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const errorObj = isJson && json.error ? json.error : {};
      throw new ApiError(
        errorObj.message || `POST failed with status ${response.status}`,
        errorObj.code || "invalid_parameter",
        response.status,
        errorObj.details || null
      );
    }

    return json;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(err.message || "Network POST failed", "network_error", 0);
  }
}

