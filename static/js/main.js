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
    const decimals = Math.max(0, parseInt(element.dataset.decimals || "0", 10) || 0);
    function format(value) {
      const amount = Number.isFinite(value) ? value : 0;
      return prefix + amount.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }) + suffix;
    }
    element.textContent = format(target);
    if (reduce || !Number.isFinite(target)) return;
    const start = performance.now();
    function frame(now) {
      const progress = Math.min(1, (now - start) / 950);
      const eased = target * (1 - Math.pow(1 - progress, 3));
      element.textContent = format(progress === 1 ? target : eased);
      if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  counters.forEach(runCounter);

  /* Search inside long dropdowns. Short lists stay native selects. */
  document.querySelectorAll("select").forEach(function (select) {
    if (!window.TomSelect || select.tomselect) return;
    if (select.dataset.search === "off" || select.multiple) return;
    if (select.offsetParent === null && select.dataset.search !== "on") return;
    let choices = 0;
    Array.prototype.forEach.call(select.options, function (option) {
      if (option.value) choices += 1;
    });
    if (select.dataset.search !== "on" && choices < 8) return;
    const placeholder = select.dataset.searchPlaceholder || "Search";
    const control = new TomSelect(select, {
      plugins: ["dropdown_input"],
      allowEmptyOption: true,
      maxOptions: null,
      closeAfterSelect: true,
      dropdownParent: "body",
      onDropdownOpen: function () {
        const input = this.dropdown.querySelector(".dropdown-input");
        if (!input) return;
        input.placeholder = placeholder;
        input.setAttribute("aria-label", placeholder);
      },
    });
    const wrapper = control.wrapper;
    if (select.classList.contains("form-select-sm")) wrapper.classList.add("ts-sm");
    if (select.closest(".field-error")) wrapper.classList.add("ts-invalid");
  });

  /* SweetAlert confirmation and submit loading spinner */
  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char];
    });
  }

  function confirmCopy(button, form) {
    const message = (button && button.dataset.confirm) || form.dataset.confirm || "";
    const tone = (button && button.dataset.confirmTone) || (/delete|cancel/i.test(message) ? "danger" : "confirm");
    const danger = tone === "danger";
    const title = (button && button.dataset.confirmTitle) || (danger ? "Please confirm" : "Confirm this action");
    const detail = (button && button.dataset.confirmDetail) || "";
    const accept = (button && button.dataset.confirmAccept) || (danger ? "Continue" : "Confirm");
    const icon = danger ? "bi-trash3" : "bi-shield-check";
    const html = '<div class="bolo-alert-mark" aria-hidden="true"><i class="bi ' + icon + '"></i></div>'
      + '<h2 class="bolo-alert-heading">' + escapeHtml(title) + "</h2>"
      + '<p class="bolo-alert-lead">' + escapeHtml(message) + "</p>"
      + (detail ? '<p class="bolo-alert-note">' + escapeHtml(detail) + "</p>" : "");
    return { danger: danger, title: title, accept: accept, html: html };
  }

  function askConfirm(button, form) {
    const copy = confirmCopy(button, form);
    if (!window.Swal) {
      const plain = [copy.title, button && button.dataset.confirm, button && button.dataset.confirmDetail].filter(Boolean).join("\n\n");
      return Promise.resolve({ isConfirmed: window.confirm(plain) });
    }
    return Swal.fire({
      title: "",
      html: copy.html,
      showCancelButton: true,
      focusCancel: copy.danger,
      reverseButtons: true,
      buttonsStyling: false,
      heightAuto: false,
      confirmButtonText: copy.accept,
      cancelButtonText: "Go back",
      showClass: { popup: "bolo-alert-in", backdrop: "bolo-alert-backdrop-in" },
      hideClass: { popup: "bolo-alert-out" },
      customClass: {
        container: "bolo-alert-container",
        popup: "bolo-alert" + (copy.danger ? " is-danger" : " is-confirm"),
        title: "bolo-alert-title",
        htmlContainer: "bolo-alert-body",
        actions: "bolo-alert-actions",
        confirmButton: copy.danger ? "bolo-alert-btn bolo-alert-btn-danger" : "bolo-alert-btn bolo-alert-btn-primary",
        cancelButton: "bolo-alert-btn bolo-alert-btn-ghost",
      },
    });
  }

  document.addEventListener("submit", function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const button = event.submitter;
    const message = (button && button.dataset.confirm) || form.dataset.confirm;
    if (message && form.dataset.confirmed !== "1") {
      event.preventDefault();
      askConfirm(button, form).then(function (result) {
        if (!result.isConfirmed) return;
        form.dataset.confirmed = "1";
        if (button) form.requestSubmit(button);
        else form.requestSubmit();
      });
      return;
    }
    if (form.dataset.spinner === "off" || !button || button.dataset.loading === "1") return;
    button.dataset.loading = "1";
    button.setAttribute("aria-busy", "true");
    button.insertAdjacentHTML("beforeend", '<span class="spinner-border spinner-border-sm ms-2" role="status" aria-hidden="true"></span>');
  });
})();
