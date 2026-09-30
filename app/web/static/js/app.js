/**
 * Mini Hiring Pipeline - Main Frontend Script (Plain ES2020)
 * CSP-compatible Alpine component registration and HTMX request configuration.
 */

document.addEventListener("alpine:init", () => {
  // Toasts component
  Alpine.data("toasts", () => ({
    items: [],
    init() {
      const handler = (evt) => {
        const detail = evt.detail || {};
        if (detail.toast) {
          this.add(detail.toast.kind || "info", detail.toast.message || "");
        } else if (detail.message) {
          this.add(detail.kind || "info", detail.message);
        }
      };
      window.addEventListener("toast", handler);
    },
    add(kind, message) {
      const id = String(Date.now() + Math.random());
      this.items.push({ id, kind, message });
      setTimeout(() => {
        this.removeById(id);
      }, 4000);
    },
    dismiss(evt) {
      const target = evt.currentTarget;
      const toastEl = target ? target.closest("[data-id]") : null;
      if (toastEl) {
        const id = toastEl.getAttribute("data-id");
        if (id) {
          this.removeById(id);
        }
      }
    },
    removeById(id) {
      this.items = this.items.filter((item) => String(item.id) !== String(id));
    },
  }));

  // Confirm Reject inline panel component
  Alpine.data("confirmReject", () => ({
    showing: false,
    open() {
      this.showing = true;
    },
    toggle() {
      this.showing = !this.showing;
    },
    close() {
      this.showing = false;
    },
  }));

  // Modal dialog component
  Alpine.data("modal", () => ({
    init() {
      const dialog = this.$refs.dialog || this.$el;
      if (dialog && typeof dialog.showModal === "function") {
        try {
          dialog.showModal();
        } catch (_err) {
          // Ignore if already open
        }
      }
      this._onCloseDialog = () => this.close();
      window.addEventListener("close-dialog", this._onCloseDialog);
    },
    destroy() {
      if (this._onCloseDialog) {
        window.removeEventListener("close-dialog", this._onCloseDialog);
      }
    },
    close() {
      const container = document.getElementById("dialog");
      if (container) {
        container.innerHTML = "";
      }
    },
  }));

  // Live stage timer component
  Alpine.data("timer", () => ({
    text: "",
    intervalId: null,
    init() {
      this.tick();
      this.intervalId = setInterval(() => {
        this.tick();
      }, 1000);
    },
    destroy() {
      if (this.intervalId) {
        clearInterval(this.intervalId);
        this.intervalId = null;
      }
    },
    tick() {
      const sinceStr = this.$el.getAttribute("data-since");
      if (!sinceStr) {
        this.text = "";
        return;
      }
      const sinceMs = Number(sinceStr);
      if (isNaN(sinceMs) || sinceMs <= 0) {
        this.text = "";
        return;
      }
      const diffMs = Math.max(0, Date.now() - sinceMs);
      const totalSeconds = Math.floor(diffMs / 1000);
      const days = Math.floor(totalSeconds / 86400);
      const hours = Math.floor((totalSeconds % 86400) / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);

      if (days > 0) {
        this.text = `${days}d ${hours}h ${minutes}m`;
      } else if (hours > 0) {
        this.text = `${hours}h ${minutes}m`;
      } else {
        this.text = `${minutes}m`;
      }
    },
  }));
});

// Configure HTMX headers before every request
document.addEventListener("htmx:configRequest", (evt) => {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) {
    const token = meta.getAttribute("content");
    if (token) {
      evt.detail.headers["X-CSRF-Token"] = token;
    }
  }
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz) {
      evt.detail.headers["X-Timezone"] = tz;
    }
  } catch (_err) {
    // Ignore timezone resolution error
  }
});

// Set client timezone cookie on load
document.addEventListener("DOMContentLoaded", () => {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz) {
      document.cookie = `tz=${encodeURIComponent(tz)}; path=/; SameSite=Strict`;
    }
  } catch (_err) {
    // Ignore timezone resolution error
  }
});

// Copy data-q attribute into search input on example chip click
document.addEventListener("click", (evt) => {
  const btn = evt.target ? evt.target.closest("button[data-q]") : null;
  if (btn) {
    const qVal = btn.getAttribute("data-q");
    const input = document.getElementById("search-input");
    if (input && qVal !== null) {
      input.value = qVal;
    }
  }
});

// Global keyboard shortcuts: Escape closes drawer, '/' focuses search input
document.addEventListener("keydown", (evt) => {
  if (evt.key === "Escape") {
    const drawerEl = document.getElementById("drawer");
    if (drawerEl && drawerEl.children.length > 0) {
      drawerEl.replaceChildren();
    }
  } else if (evt.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(evt.target?.tagName)) {
    const input = document.getElementById("search-input");
    if (input) {
      evt.preventDefault();
      input.focus();
    }
  }
});

