(function () {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* 1. Top Scroll-Progress Laser */
  const laser = document.getElementById("scroll-laser");
  function updateLaser() {
    if (!laser) return;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    laser.style.transform = "scaleX(" + ratio.toFixed(4) + ")";
  }
  window.addEventListener("scroll", updateLaser, { passive: true });
  updateLaser();

  /* 2. Staggered Scroll Reveals */
  const staggered = document.querySelectorAll(".reveal-stagger");
  if (reduce || !("IntersectionObserver" in window)) {
    staggered.forEach(function (el) { el.classList.add("is-visible"); });
  } else {
    const revObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    staggered.forEach(function (el) { revObserver.observe(el); });
  }

  /* 3. Hero Cursor Aura + 3D Holo Studio Tilt */
  const hero = document.querySelector(".nx-hero");
  const studio = document.getElementById("holo-studio");
  if (hero && !reduce) {
    hero.addEventListener("pointermove", function (e) {
      const rect = hero.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      hero.style.setProperty("--mx", x.toFixed(1) + "%");
      hero.style.setProperty("--my", y.toFixed(1) + "%");
    });
  }
  if (studio && !reduce) {
    studio.addEventListener("pointermove", function (e) {
      const rect = studio.getBoundingClientRect();
      const nx = (e.clientX - rect.left) / rect.width - 0.5;
      const ny = (e.clientY - rect.top) / rect.height - 0.5;
      studio.style.transform =
        "rotateX(" + (-ny * 7).toFixed(2) + "deg) rotateY(" + (nx * 8).toFixed(2) + "deg)";
    });
    studio.addEventListener("pointerleave", function () {
      studio.style.transform = "rotateX(0deg) rotateY(0deg)";
    });
  }

  /* 4. Magnetic CTA Buttons */
  if (!reduce) {
    document.querySelectorAll("[data-magnetic]").forEach(function (btn) {
      btn.addEventListener("pointermove", function (e) {
        const r = btn.getBoundingClientRect();
        const dx = (e.clientX - (r.left + r.width / 2)) * 0.16;
        const dy = (e.clientY - (r.top + r.height / 2)) * 0.22;
        btn.style.transform = "translate3d(" + dx.toFixed(1) + "px, " + dy.toFixed(1) + "px, 0)";
      });
      btn.addEventListener("pointerleave", function () {
        btn.style.transform = "translate3d(0, 0, 0)";
      });
    });
  }

  /* 5. Spotlight Hover Cards */
  document.querySelectorAll(".spotlight-card").forEach(function (card) {
    card.addEventListener("pointermove", function (e) {
      const r = card.getBoundingClientRect();
      card.style.setProperty("--spot-x", (e.clientX - r.left).toFixed(0) + "px");
      card.style.setProperty("--spot-y", (e.clientY - r.top).toFixed(0) + "px");
    });
  });

  /* 6. Interactive Live Print Studio Preview */
  const ITEMS = {
    tee: {
      method: "DTF / Screen Print",
      skuPrefix: "CTN",
      price: "₱350.00",
      url: "/products/?category=cotton-shirts",
      photo: "/static/img/landing_page_pics.jpg",
    },
    jersey: {
      method: "Full Dye-Sublimation",
      skuPrefix: "SUB",
      price: "₱650.00",
      url: "/products/?category=sublimated-shirts",
      photo: "/static/img/landing_page_pics.jpg",
    },
    mug: {
      method: "UV / Wrap Sublimation",
      skuPrefix: "MUG",
      price: "₱199.00",
      url: "/products/?category=mugs",
      photo: "/static/img/studio/ceramic-photo-mug.jpg",
    },
    cap: {
      method: "3D Stitch Embroidery",
      skuPrefix: "CAP",
      price: "₱250.00",
      url: "/products/?category=baseball-caps",
      photo: "/static/img/studio/embroidered-dad-cap.jpg",
    },
  };

  const viewport = document.getElementById("holo-viewport");
  const photoStage = document.getElementById("holo-photo");
  const printTextEl = document.getElementById("holo-print-text");
  const textInput = document.getElementById("holo-text");
  const skuChip = document.getElementById("holo-sku");
  const methodChip = document.getElementById("holo-method");
  const priceEl = document.getElementById("holo-price");
  const ctaLink = document.getElementById("holo-cta");

  let activeItem = "tee";
  let activeColor = "#0f766e";
  let activeColorCode = "TEAL";

  function renderStudio(animateSwitch) {
    if (!photoStage) return;
    const cfg = ITEMS[activeItem];
    const cleanText = ((textInput && textInput.value) || "BOLOMAN 26")
      .toUpperCase()
      .replace(/[<>&"]/g, "")
      .slice(0, 14);
    if (animateSwitch) {
      if (!reduce) {
        photoStage.classList.add("is-switching");
        setTimeout(function () { photoStage.classList.remove("is-switching"); }, 220);
      }
      photoStage.src = cfg.photo;
    }
    if (viewport) viewport.style.setProperty("--holo-tint", activeColor);
    if (printTextEl) printTextEl.textContent = cleanText || "YOUR LOGO";
    if (skuChip) skuChip.textContent = "SKU " + cfg.skuPrefix + "-" + activeColorCode + "-M";
    if (methodChip) methodChip.textContent = cfg.method;
    if (priceEl) priceEl.textContent = cfg.price;
    if (ctaLink) ctaLink.href = cfg.url;
  }

  document.querySelectorAll("[data-studio-item]").forEach(function (tab) {
    tab.addEventListener("click", function () {
      activeItem = tab.dataset.studioItem;
      document.querySelectorAll("[data-studio-item]").forEach(function (t) {
        t.classList.toggle("is-active", t === tab);
        t.setAttribute("aria-selected", t === tab ? "true" : "false");
      });
      renderStudio(true);
    });
  });

  document.querySelectorAll("[data-studio-color]").forEach(function (sw) {
    sw.addEventListener("click", function () {
      activeColor = sw.dataset.studioColor;
      activeColorCode = sw.dataset.code || "CLR";
      document.querySelectorAll("[data-studio-color]").forEach(function (s) {
        s.classList.toggle("is-active", s === sw);
      });
      renderStudio(false);
    });
  });

  if (textInput) {
    textInput.addEventListener("input", function () { renderStudio(false); });
  }
  renderStudio(false);

  /* 7. Interactive Order Stage Telemetry Simulator */
  const STAGE_COPY = [
    "Order placed & variant stock atomically reserved via select_for_update.",
    "Artwork proofed & blanks pulled from warehouse bin for press setup.",
    "Quality check passed; packed with protective wrap and queued for rider.",
    "Dispatched with courier — live tracking active until handoff.",
    "Delivered & verified. Full audit log stored in customer portal.",
  ];
  const stagePills = document.querySelectorAll("[data-stage-idx]");
  const stageDesc = document.getElementById("stage-live-desc");

  function setStage(idx) {
    stagePills.forEach(function (pill) {
      const i = Number(pill.dataset.stageIdx);
      pill.classList.toggle("is-done", i < idx);
      pill.classList.toggle("is-active", i === idx);
    });
    if (stageDesc && STAGE_COPY[idx]) {
      stageDesc.textContent = STAGE_COPY[idx];
    }
  }

  let stageIndex = 1;
  let stageTimer = null;
  if (stagePills.length) {
    stagePills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        stageIndex = Number(pill.dataset.stageIdx);
        setStage(stageIndex);
        if (stageTimer) clearInterval(stageTimer);
      });
    });
    setStage(stageIndex);
    if (!reduce) {
      stageTimer = setInterval(function () {
        stageIndex = (stageIndex + 1) % stagePills.length;
        setStage(stageIndex);
      }, 3200);
    }
  }
})();
