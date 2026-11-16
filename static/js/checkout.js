(function () {
  const panel = document.getElementById("gcash-panel");
  const qtyInput = document.getElementById("id_quantity");
  const totalElements = document.querySelectorAll("[data-unit-price]");

  function peso(value) {
    return "₱" + Number(value).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function syncTotals() {
    const qty = Math.max(1, Number(qtyInput && qtyInput.value) || 1);
    totalElements.forEach(function (el) {
      const unit = Number(el.dataset.unitPrice || 0);
      el.textContent = peso(unit * qty);
    });
    const qtyMirror = document.getElementById("summary-qty");
    if (qtyMirror) qtyMirror.textContent = String(qty);
  }

  function syncPayment() {
    const selected = document.querySelector('input[name="payment_method"]:checked');
    if (panel) panel.hidden = !selected || selected.value !== "GCASH";
    document.querySelectorAll(".payment-option").forEach(function (card) {
      const radio = card.querySelector('input[name="payment_method"]');
      card.classList.toggle("is-selected", Boolean(radio && radio.checked));
    });
  }

  document.querySelectorAll('input[name="payment_method"]').forEach(function (input) {
    input.addEventListener("change", syncPayment);
  });
  if (qtyInput) qtyInput.addEventListener("input", syncTotals);

  const copyBtn = document.getElementById("copy-gcash");
  if (copyBtn && navigator.clipboard) {
    copyBtn.addEventListener("click", function () {
      navigator.clipboard.writeText(copyBtn.dataset.number || "").then(function () {
        const original = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="bi bi-check2" aria-hidden="true"></i> Copied';
        setTimeout(function () { copyBtn.innerHTML = original; }, 1600);
      });
    });
  }

  const file = document.getElementById("id_screenshot");
  const preview = document.getElementById("shot-preview");
  if (file && preview) {
    file.addEventListener("change", function () {
      const image = file.files && file.files[0];
      if (!image) {
        preview.hidden = true;
        return;
      }
      preview.src = URL.createObjectURL(image);
      preview.hidden = false;
    });
  }

  syncPayment();
  syncTotals();
})();
