(function () {
  const form = document.getElementById("checkout-form");
  const gcashPanel = document.getElementById("gcash-panel");
  const codPanel = document.getElementById("cod-panel");
  const qtyInput = document.getElementById("id_quantity");
  const notesInput = document.getElementById("id_customization_notes");
  const totalElements = document.querySelectorAll("[data-unit-price]");
  const file = document.getElementById("id_screenshot");
  const preview = document.getElementById("shot-preview");
  let previewUrl = "";

  function peso(value) {
    return "₱" + Number(value).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function currentQty() {
    return Math.max(1, Math.floor(Number(qtyInput && qtyInput.value) || 1));
  }

  function clearPreview() {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      previewUrl = "";
    }
    if (preview) {
      preview.removeAttribute("src");
      preview.hidden = true;
    }
  }

  function syncTotals() {
    const qty = currentQty();
    totalElements.forEach(function (el) {
      const unit = Number(el.dataset.unitPrice || 0);
      el.textContent = peso(unit * qty);
    });
    const qtyMirror = document.getElementById("summary-qty");
    if (qtyMirror) qtyMirror.textContent = String(qty);
  }

  function syncPayment() {
    const selected = document.querySelector('input[name="payment_method"]:checked');
    const isGcash = Boolean(selected && selected.value === "GCASH");
    if (gcashPanel) gcashPanel.hidden = !isGcash;
    if (codPanel) codPanel.hidden = isGcash;
    if (!isGcash) clearPreview();
    document.querySelectorAll(".payment-option").forEach(function (card) {
      const radio = card.querySelector('input[name="payment_method"]');
      card.classList.toggle("is-selected", Boolean(radio && radio.checked));
    });
  }

  function copyToClipboard(text, button) {
    if (!text || !button) return;
    const done = function () {
      const original = button.innerHTML;
      button.innerHTML = '<i class="bi bi-check2" aria-hidden="true"></i> Copied';
      setTimeout(function () { button.innerHTML = original; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () {});
    } else {
      const temp = document.createElement("textarea");
      temp.value = text;
      temp.setAttribute("readonly", "");
      temp.style.position = "absolute";
      temp.style.left = "-9999px";
      document.body.appendChild(temp);
      temp.select();
      try {
        if (document.execCommand("copy")) done();
      } finally {
        document.body.removeChild(temp);
      }
    }
  }

  document.querySelectorAll('input[name="payment_method"]').forEach(function (input) {
    input.addEventListener("change", syncPayment);
  });
  if (qtyInput) qtyInput.addEventListener("input", syncTotals);

  const copyBtn = document.getElementById("copy-gcash");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      const number = (copyBtn.dataset.number || "").replace(/[\s-]+/g, "");
      copyToClipboard(number, copyBtn);
    });
  }

  const copyAmountBtn = document.getElementById("copy-amount");
  if (copyAmountBtn) {
    copyAmountBtn.addEventListener("click", function () {
      const unit = Number(copyAmountBtn.dataset.unitPriceRaw || 0);
      const exact = (unit * currentQty()).toFixed(2);
      copyToClipboard(exact, copyAmountBtn);
    });
  }

  if (file && preview) {
    file.addEventListener("change", function () {
      clearPreview();
      const image = file.files && file.files[0];
      const allowed = ["image/jpeg", "image/png", "image/webp"];
      if (!image || !allowed.includes(image.type) || image.size > 5 * 1024 * 1024) {
        return;
      }
      previewUrl = URL.createObjectURL(image);
      preview.src = previewUrl;
      preview.hidden = false;
    });
  }

  /* Step-by-step guided checkout wizard */
  const stepCards = Array.from(document.querySelectorAll("[data-checkout-step]"));
  const step1Fields = [
    document.getElementById("id_recipient_name"),
    document.getElementById("id_phone"),
    document.getElementById("id_address_line"),
    document.getElementById("id_city"),
    document.getElementById("id_province"),
  ].filter(Boolean);

  step1Fields.forEach(function (field) {
    field.addEventListener("input", function () {
      if ((field.value || "").trim()) field.classList.remove("is-invalid");
    });
  });
  if (qtyInput) {
    qtyInput.addEventListener("input", function () {
      qtyInput.classList.remove("is-invalid");
    });
  }

  function updateStepSummaries() {
    const s1 = document.getElementById("step-1-summary");
    if (s1) {
      const name = (document.getElementById("id_recipient_name")?.value || "").trim();
      const phone = (document.getElementById("id_phone")?.value || "").trim();
      const city = (document.getElementById("id_city")?.value || "").trim();
      const province = (document.getElementById("id_province")?.value || "").trim();
      const place = [city, province].filter(Boolean).join(", ");
      s1.textContent = [name, phone, place].filter(Boolean).join(" · ");
    }
    const s2 = document.getElementById("step-2-summary");
    if (s2) {
      const qty = currentQty();
      const notes = (notesInput && notesInput.value || "").trim();
      s2.textContent = qty + (qty === 1 ? " piece" : " pieces") + (notes ? " · Print notes: " + notes.slice(0, 60) : " · No extra print notes");
    }
  }

  function validateStep1(focusInvalid) {
    const hint = document.getElementById("step-1-hint");
    let firstMissing = null;
    step1Fields.forEach(function (field) {
      const empty = !(field.value || "").trim();
      field.classList.toggle("is-invalid", empty);
      if (empty && !firstMissing) firstMissing = field;
    });
    if (hint) {
      hint.hidden = !firstMissing;
      hint.classList.toggle("d-block", Boolean(firstMissing));
    }
    if (firstMissing && focusInvalid) firstMissing.focus();
    return !firstMissing;
  }

  function validateStep2(focusInvalid) {
    const hint = document.getElementById("step-2-hint");
    if (!qtyInput) return true;
    const raw = Number(qtyInput.value);
    const max = Number(qtyInput.max || 0);
    const invalid = !Number.isInteger(raw) || raw < 1 || (max > 0 && raw > max);
    qtyInput.classList.toggle("is-invalid", invalid);
    if (hint) {
      hint.hidden = !invalid;
      hint.classList.toggle("d-block", invalid);
    }
    if (invalid && focusInvalid) qtyInput.focus();
    return !invalid;
  }

  function openStep(stepNumber, scrollIntoView) {
    updateStepSummaries();
    stepCards.forEach(function (card) {
      const num = Number(card.dataset.checkoutStep);
      const isDone = num < stepNumber;
      const isActive = num === stepNumber;
      const body = card.querySelector(".checkout-card-body");
      const sub = card.querySelector(".checkout-step-sub");
      const summary = card.querySelector(".checkout-step-summary");
      const editBtn = card.querySelector('.checkout-card-head [data-edit-step]');
      const badge = card.querySelector("[data-step-badge]");

      card.classList.toggle("is-active", isActive);
      card.classList.toggle("is-done", isDone);
      card.classList.toggle("is-collapsed", !isActive);

      if (body) body.hidden = !isActive;
      if (sub) sub.hidden = !isActive && isDone;
      if (summary) summary.hidden = !(isDone && summary.textContent);
      if (editBtn) editBtn.hidden = !isDone;
      if (badge) {
        badge.innerHTML = isDone ? '<i class="bi bi-check2" aria-hidden="true"></i>' : String(num);
      }
    });

    if (scrollIntoView) {
      const target = document.querySelector('[data-checkout-step="' + stepNumber + '"]');
      if (target && target.scrollIntoView) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  document.querySelectorAll("[data-next-step]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const target = Number(btn.dataset.nextStep);
      if (target >= 2 && !validateStep1(true)) return;
      if (target >= 3 && !validateStep2(true)) return;
      openStep(target, true);
    });
  });

  document.querySelectorAll("[data-edit-step]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      openStep(Number(btn.dataset.editStep), true);
    });
  });

  if (form && stepCards.length === 3) {
    form.addEventListener("submit", function (event) {
      if (!validateStep1(false)) {
        event.preventDefault();
        openStep(1, true);
        validateStep1(true);
        return;
      }
      if (!validateStep2(false)) {
        event.preventDefault();
        openStep(2, true);
        validateStep2(true);
      }
    });

    const stepWithError = stepCards.find(function (card) {
      return Boolean(card.querySelector(".field-error, .alert-danger"));
    });
    if (stepWithError) {
      openStep(Number(stepWithError.dataset.checkoutStep), true);
    } else {
      openStep(1, false);
    }
  }

  syncPayment();
  syncTotals();
})();
