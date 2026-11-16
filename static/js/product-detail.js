(function () {
  const photo = document.getElementById("main-photo");
  const thumbs = Array.from(document.querySelectorAll(".thumb"));
  const countEl = document.getElementById("gallery-count");
  if (photo && thumbs.length > 1) {
    let index = thumbs.findIndex(function (thumb) { return thumb.classList.contains("is-active"); });
    if (index < 0) index = 0;

    function showPhoto(next) {
      index = (next + thumbs.length) % thumbs.length;
      const thumb = thumbs[index];
      photo.src = thumb.dataset.src;
      if (thumb.dataset.alt) photo.alt = thumb.dataset.alt;
      thumbs.forEach(function (item) {
        const active = item === thumb;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-selected", active ? "true" : "false");
      });
      if (countEl) countEl.textContent = (index + 1) + " / " + thumbs.length;
    }

    const previous = document.getElementById("gallery-prev");
    const next = document.getElementById("gallery-next");
    if (previous) previous.addEventListener("click", function () { showPhoto(index - 1); });
    if (next) next.addEventListener("click", function () { showPhoto(index + 1); });
    thumbs.forEach(function (thumb, thumbIndex) {
      thumb.addEventListener("click", function () { showPhoto(thumbIndex); });
    });
    document.addEventListener("keydown", function (event) {
      const typing = event.target && (event.target.matches("input, textarea, select") || event.target.isContentEditable);
      if (typing) return;
      if (event.key === "ArrowLeft") showPhoto(index - 1);
      if (event.key === "ArrowRight") showPhoto(index + 1);
    });
    showPhoto(index);
  }

  const dataElement = document.getElementById("variant-data");
  if (!dataElement) return;
  const variants = JSON.parse(dataElement.textContent).variants;
  const colorBox = document.getElementById("color-options");
  const sizeBox = document.getElementById("size-options");
  const sizeLegend = document.getElementById("size-legend");
  const sizeBlock = document.getElementById("size-block");
  const hidden = document.getElementById("variant-id");
  const qty = document.getElementById("qty");
  const qtyMinus = document.getElementById("qty-minus");
  const qtyPlus = document.getElementById("qty-plus");
  const price = document.getElementById("price");
  const subtotal = document.getElementById("estimated-total");
  const selectedLabel = document.getElementById("selected-summary");
  const stockLine = document.getElementById("color-stock");
  const status = document.getElementById("stock-status");
  const meterBar = document.getElementById("stock-meter-bar");
  const stageEl = document.getElementById("gallery-main");
  const stagePill = document.getElementById("stage-live-pill");
  const notesInput = document.getElementById("notes");
  const orderButton = document.getElementById("order-btn");

  const colors = [];
  variants.forEach(function (variant) {
    if (!colors.some(function (color) { return color.name === variant.color; })) {
      const matches = variants.filter(function (item) { return item.color === variant.color; });
      colors.push({
        name: variant.color,
        hex: variant.hex,
        stock: matches.reduce(function (sum, item) { return sum + item.stock; }, 0),
      });
    }
  });

  const usesCapacity = variants.some(function (variant) { return variant.capacity; });
  const usesSize = variants.some(function (variant) { return variant.size; });
  if (sizeLegend) sizeLegend.textContent = usesCapacity ? "Select Capacity" : "Select Size";
  if (!usesCapacity && !usesSize && sizeBlock) sizeBlock.hidden = true;

  let selectedColor = (colors.find(function (color) { return color.stock > 0; }) || colors[0]).name;
  let selectedKey = "";

  function peso(value) {
    return "₱" + Number(value).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function optionsFor(color) {
    return variants.filter(function (variant) { return variant.color === color; });
  }

  function current() {
    return variants.find(function (variant) {
      const key = variant.capacity || variant.size || "";
      return variant.color === selectedColor && key === selectedKey;
    }) || optionsFor(selectedColor)[0];
  }

  function renderColors() {
    colorBox.innerHTML = "";
    colors.forEach(function (color) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "swatch" + (color.name === selectedColor ? " is-selected" : "");
      button.setAttribute("role", "radio");
      button.setAttribute("aria-checked", color.name === selectedColor ? "true" : "false");
      button.disabled = color.stock === 0;
      const countText = color.stock === 0 ? "Out" : color.stock;
      button.innerHTML = '<i style="background:' + color.hex + '"></i><span>' + color.name + "</span><small>" + countText + "</small>";
      button.addEventListener("click", function () {
        selectedColor = color.name;
        const available = optionsFor(selectedColor).find(function (variant) { return variant.stock > 0; });
        const fallback = optionsFor(selectedColor)[0];
        selectedKey = available ? (available.capacity || available.size || "") : (fallback ? (fallback.capacity || fallback.size || "") : "");
        render();
      });
      colorBox.appendChild(button);
    });
    const color = colors.find(function (item) { return item.name === selectedColor; });
    if (stockLine && color) {
      stockLine.textContent = color.name + ": " + (color.stock === 0 ? "Out of stock" : color.stock + " in stock");
    }
  }

  function renderSizes() {
    sizeBox.innerHTML = "";
    optionsFor(selectedColor).forEach(function (variant) {
      const key = variant.capacity || variant.size || "";
      const label = variant.capacity || variant.sizeLabel || "Standard";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "size-btn" + (key === selectedKey ? " is-selected" : "");
      button.setAttribute("role", "radio");
      button.setAttribute("aria-checked", key === selectedKey ? "true" : "false");
      button.disabled = variant.stock === 0;
      button.innerHTML = variant.stock === 0
        ? "<span>" + label + "</span><small>Out</small>"
        : "<span>" + label + "</span><small>" + variant.stock + "</small>";
      button.addEventListener("click", function () {
        selectedKey = key;
        render();
      });
      sizeBox.appendChild(button);
    });
  }

  function updateSummary(variant) {
    const count = Math.max(1, Number(qty.value) || 1);
    if (subtotal && variant) {
      subtotal.textContent = peso(Number(variant.price) * count);
    }
    if (selectedLabel && variant) {
      const opt = variant.capacity || variant.sizeLabel || "";
      selectedLabel.textContent = variant.color + (opt ? " / " + opt : "") + " · " + count + (count === 1 ? " pc" : " pcs") + " · " + variant.sku;
    }
  }

  function render() {
    renderColors();
    renderSizes();
    const variant = current();
    if (!variant) return;
    selectedKey = variant.capacity || variant.size || "";
    hidden.value = variant.id;
    price.textContent = peso(variant.price);
    qty.max = String(Math.max(variant.stock, 1));
    if (Number(qty.value) > variant.stock) qty.value = String(Math.max(variant.stock, 1));
    if (variant.stock === 0) qty.value = "1";

    if (stageEl) {
      stageEl.style.setProperty("--stage-color", variant.hex || "transparent");
    }
    if (stagePill) {
      const opt = variant.capacity || variant.sizeLabel || "";
      stagePill.innerHTML =
        '<span class="swatch-dot" style="background:' + variant.hex + '"></span>' +
        "<span>" + variant.color + (opt ? " · " + opt : "") + " (" + variant.sku + ")</span>";
    }

    status.className = "stock-banner";
    if (variant.stock <= 0) {
      status.innerHTML = '<i class="bi bi-x-circle-fill" aria-hidden="true"></i> Out of stock';
      status.classList.add("is-out");
      orderButton.disabled = true;
      if (meterBar) { meterBar.style.width = "0%"; meterBar.style.backgroundColor = "#dc2626"; }
    } else if (variant.stock <= variant.reorder) {
      status.innerHTML = '<i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i> Low stock · Only ' + variant.stock + " left";
      status.classList.add("is-low");
      orderButton.disabled = false;
      if (meterBar) { meterBar.style.width = Math.max(15, variant.stock * 10) + "%"; meterBar.style.backgroundColor = "#d97706"; }
    } else {
      status.innerHTML = '<i class="bi bi-check-circle-fill" aria-hidden="true"></i> ' + variant.stock + " ready to print";
      status.classList.add("is-in");
      orderButton.disabled = false;
      if (meterBar) { meterBar.style.width = Math.min(100, Math.round((variant.stock / 30) * 100)) + "%"; meterBar.style.backgroundColor = "#0d9488"; }
    }
    updateSummary(variant);
  }

  function clampQty(nextValue) {
    const variant = current();
    let value = Number(nextValue);
    if (!value || value < 1) value = 1;
    if (variant && variant.stock > 0 && value > variant.stock) value = variant.stock;
    qty.value = String(value);
    if (variant) updateSummary(variant);
  }

  qty.addEventListener("input", function () { clampQty(qty.value); });
  if (qtyMinus) qtyMinus.addEventListener("click", function () { clampQty((Number(qty.value) || 1) - 1); });
  if (qtyPlus) qtyPlus.addEventListener("click", function () { clampQty((Number(qty.value) || 1) + 1); });

  /* Quick Print Note Presets */
  document.querySelectorAll("[data-note-preset]").forEach(function (chip) {
    chip.addEventListener("click", function () {
      if (!notesInput) return;
      notesInput.value = chip.dataset.notePreset;
      notesInput.focus();
    });
  });

  const first = optionsFor(selectedColor).find(function (variant) { return variant.stock > 0; }) || optionsFor(selectedColor)[0];
  selectedKey = first ? (first.capacity || first.size || "") : "";
  render();
})();
