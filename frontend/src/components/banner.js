/**
 * Reusable banner component for notifications and error states.
 */

export function createBanner({ type = "info", title = "", message = "", onRetry = null }) {
  const el = document.createElement("div");
  el.className = `banner banner-${type}`;

  const titleEl = document.createElement("h4");
  titleEl.className = "banner-title";
  titleEl.textContent = title;
  el.appendChild(titleEl);

  const msgEl = document.createElement("p");
  msgEl.className = "banner-message";
  msgEl.textContent = message;
  el.appendChild(msgEl);

  if (onRetry) {
    const btn = document.createElement("button");
    btn.className = "btn btn-secondary";
    btn.textContent = "Retry";
    btn.addEventListener("click", onRetry);
    el.appendChild(btn);
  }

  return el;
}

