(function () {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.querySelectorAll(".toast").forEach(function (element) {
    if (window.bootstrap) {
      bootstrap.Toast.getOrCreateInstance(element).show();
    }
  });

  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (element) {
    if (window.bootstrap) bootstrap.Tooltip.getOrCreateInstance(element);
  });

  /* Light / Obsidian Dark Theme Switcher */
  const themeBtn = document.getElementById("theme-toggle");
  const themeIcon = document.getElementById("theme-icon");
  function syncThemeIcon() {
    if (!themeIcon) return;
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    themeIcon.className = isDark ? "bi bi-sun-fill text-warning" : "bi bi-moon-stars";
  }
  syncThemeIcon();
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("boloman-theme", next); } catch (e) {}
      syncThemeIcon();
    });
  }

  /* Scroll Reveal */
  const reveals = document.querySelectorAll(".reveal");
  if (reduce || !("IntersectionObserver" in window)) {
    reveals.forEach(function (element) { element.classList.add("is-visible"); });
  } else {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    reveals.forEach(function (element) { observer.observe(element); });
  }

  /* Button Ripple */
  document.addEventListener("click", function (event) {
    const button = event.target.closest(".btn");
    if (!button || reduce) return;
    const rect = button.getBoundingClientRect();
    const ripple = document.createElement("span");
    ripple.className = "ripple";
    ripple.style.left = (event.clientX - rect.left) + "px";
    ripple.style.top = (event.clientY - rect.top) + "px";
    button.appendChild(ripple);
    ripple.addEventListener("animationend", function () { ripple.remove(); });
  });

  /* Interactive Color-Reactive Swatch Dots on Product Cards */
  document.addEventListener("click", function (event) {
    const swatch = event.target.closest(".card-swatch-btn");
    if (!swatch) return;
    event.preventDefault();
    const card = swatch.closest(".product-card");
    if (!card) return;
    card.style.setProperty("--card-tint", swatch.dataset.hex || "transparent");
    card.querySelectorAll(".card-swatch-btn").forEach(function (btn) {
      btn.classList.toggle("is-active", btn === swatch);
    });
  });

  /* Keyboard Shortcut `/` or `Cmd/Ctrl+K` for Quick Search Modal */
  const searchModalEl = document.getElementById("quickSearchModal");
  if (searchModalEl && window.bootstrap) {
    const searchInput = document.getElementById("quick-search-input");
    searchModalEl.addEventListener("shown.bs.modal", function () {
      if (searchInput) searchInput.focus();
    });
    document.addEventListener("keydown", function (event) {
      const tag = (event.target && event.target.tagName) || "";
      const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || event.target.isContentEditable;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        bootstrap.Modal.getOrCreateInstance(searchModalEl).show();
      } else if (!typing && event.key === "/") {
        event.preventDefault();
        bootstrap.Modal.getOrCreateInstance(searchModalEl).show();
      }
    });
  }

  /* Animated Counters */
  const counters = document.querySelectorAll("[data-counter]");
  function runCounter(element) {
    const target = Number(element.dataset.counter || 0);
    const prefix = element.dataset.prefix || "";
    const suffix = element.dataset.suffix || "";
    if (reduce) {
      element.textContent = prefix + target.toLocaleString() + suffix;
      return;
    }
    const start = performance.now();
    function frame(now) {
      const progress = Math.min(1, (now - start) / 950);
      const value = Math.round(target * (1 - Math.pow(1 - progress, 3)));
      element.textContent = prefix + value.toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  if ("IntersectionObserver" in window) {
    const counterObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          runCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(function (element) { counterObserver.observe(element); });
  } else {
    counters.forEach(runCounter);
  }

  /* Confirmation Modal & Submit Loading Spinner */
  const modalElement = document.getElementById("confirmModal");
  const confirmModal = modalElement && window.bootstrap ? new bootstrap.Modal(modalElement) : null;
  let pendingForm = null;
  let pendingButton = null;
  document.addEventListener("submit", function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const button = event.submitter;
    const message = (button && button.dataset.confirm) || form.dataset.confirm;
    if (message && form.dataset.confirmed !== "1" && confirmModal) {
      event.preventDefault();
      pendingForm = form;
      pendingButton = button;
      document.getElementById("confirmCopy").textContent = message;
      confirmModal.show();
      return;
    }
    if (form.dataset.spinner === "off" || !button || button.dataset.loading === "1") return;
    button.dataset.loading = "1";
    button.setAttribute("aria-busy", "true");
    button.insertAdjacentHTML("beforeend", '<span class="spinner-border spinner-border-sm ms-2" role="status" aria-hidden="true"></span>');
  });
  const confirmButton = document.getElementById("confirmAccept");
  if (confirmButton) {
    confirmButton.addEventListener("click", function () {
      if (!pendingForm) return;
      pendingForm.dataset.confirmed = "1";
      if (confirmModal) confirmModal.hide();
      if (pendingButton) pendingForm.requestSubmit(pendingButton);
      else pendingForm.requestSubmit();
    });
  }
})();
