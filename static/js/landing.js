(function () {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const laser = document.getElementById("scroll-laser");
  function updateLaser() {
    if (!laser) return;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    laser.style.transform = "scaleX(" + ratio.toFixed(4) + ")";
  }
  window.addEventListener("scroll", updateLaser, { passive: true });
  updateLaser();

  const staggered = document.querySelectorAll(".reveal-stagger, .reveal-3d");
  if (reduce || !("IntersectionObserver" in window)) {
    staggered.forEach(function (el) { el.classList.add("is-visible"); });
  } else {
    const revObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        revObserver.unobserve(entry.target);
      });
    }, { threshold: 0.12 });
    staggered.forEach(function (el) { revObserver.observe(el); });
  }

  document.querySelectorAll("[data-counter]").forEach(function (node) {
    const target = Number(node.getAttribute("data-counter")) || 0;
    if (reduce) {
      node.textContent = String(target);
      return;
    }
    const start = performance.now();
    const duration = 1100;
    function tick(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      node.textContent = String(Math.round(target * eased));
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });

  const hero = document.getElementById("hero-3d");
  const studio = document.getElementById("holo-studio");
  const glare = document.getElementById("holo-glare");
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
      if (glare) {
        glare.style.setProperty("--gx", ((nx + 0.5) * 100).toFixed(1) + "%");
        glare.style.setProperty("--gy", ((ny + 0.5) * 100).toFixed(1) + "%");
      }
    });
    studio.addEventListener("pointerleave", function () {
      studio.style.transform = "rotateX(0deg) rotateY(0deg)";
    });
  }

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

    document.querySelectorAll("[data-tilt-3d]").forEach(function (el) {
      const max = Number(el.dataset.tiltMax || 8);
      el.addEventListener("pointermove", function (e) {
        const r = el.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width;
        const py = (e.clientY - r.top) / r.height;
        const rx = ((0.5 - py) * max).toFixed(2);
        const ry = ((px - 0.5) * max).toFixed(2);
        el.style.transform = "rotateX(" + rx + "deg) rotateY(" + ry + "deg) translateY(-4px)";
        el.style.setProperty("--gx", (px * 100).toFixed(1) + "%");
        el.style.setProperty("--gy", (py * 100).toFixed(1) + "%");
      });
      el.addEventListener("pointerleave", function () {
        el.style.transform = "";
      });
    });
  }

  document.querySelectorAll(".spotlight-card").forEach(function (card) {
    card.addEventListener("pointermove", function (e) {
      const r = card.getBoundingClientRect();
      card.style.setProperty("--spot-x", (e.clientX - r.left).toFixed(0) + "px");
      card.style.setProperty("--spot-y", (e.clientY - r.top).toFixed(0) + "px");
    });
  });

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
  const turntable = document.getElementById("holo-3d-turntable");

  let activeItem = "tee";
  let activeColor = "#0f766e";
  let activeColorCode = "TEAL";
  let studioMode = "photo";

  function cleanPrintText() {
    return ((textInput && textInput.value) || "BOLOMAN 26")
      .toUpperCase()
      .replace(/[<>&"]/g, "")
      .slice(0, 14) || "YOUR LOGO";
  }

  function renderStudio(animateSwitch) {
    if (!photoStage) return;
    const cfg = ITEMS[activeItem];
    const cleanText = cleanPrintText();
    if (animateSwitch) {
      if (!reduce) {
        photoStage.classList.add("is-switching");
        setTimeout(function () { photoStage.classList.remove("is-switching"); }, 220);
      }
      photoStage.src = cfg.photo;
    }
    if (viewport) viewport.style.setProperty("--holo-tint", activeColor);
    if (printTextEl) printTextEl.textContent = cleanText;
    if (skuChip) skuChip.textContent = "SKU " + cfg.skuPrefix + "-" + activeColorCode + "-M";
    if (methodChip) methodChip.textContent = cfg.method;
    if (priceEl) priceEl.textContent = cfg.price;
    if (ctaLink) ctaLink.href = cfg.url;
    if (studioMode === "mesh") syncMesh();
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

  if (textInput) textInput.addEventListener("input", function () { renderStudio(false); });
  renderStudio(false);

  function setStudioMode(mode) {
    studioMode = mode === "mesh" && window.THREE ? "mesh" : "photo";
    document.querySelectorAll("[data-studio-mode]").forEach(function (btn) {
      btn.classList.toggle("is-active", btn.dataset.studioMode === studioMode);
    });
    if (viewport) viewport.classList.toggle("is-mesh", studioMode === "mesh");
    if (turntable) turntable.hidden = studioMode !== "mesh";
    if (studioMode === "mesh") syncMesh();
  }

  document.querySelectorAll("[data-studio-mode]").forEach(function (btn) {
    btn.addEventListener("click", function () { setStudioMode(btn.dataset.studioMode); });
  });
  const launch = document.getElementById("holo-launch-3d");
  if (launch) launch.addEventListener("click", function () { setStudioMode("mesh"); });

  const STAGE_COPY = [
    "Order placed & variant stock atomically reserved via select_for_update.",
    "Artwork proofed & blanks pulled from warehouse bin for press setup.",
    "Quality check passed; packed with protective wrap and queued for rider.",
    "Dispatched with courier — live tracking active until handoff.",
    "Delivered & verified. Full audit log stored in customer portal.",
  ];
  const stagePills = document.querySelectorAll("[data-stage-idx]");
  const stageDesc = document.getElementById("stage-live-desc");
  const stageFill = document.getElementById("stage-progress-fill");

  function setStage(idx) {
    stagePills.forEach(function (pill) {
      const i = Number(pill.dataset.stageIdx);
      pill.classList.toggle("is-done", i < idx);
      pill.classList.toggle("is-active", i === idx);
    });
    if (stageDesc && STAGE_COPY[idx]) stageDesc.textContent = STAGE_COPY[idx];
    if (stageFill && stagePills.length) {
      stageFill.style.width = (((idx + 1) / stagePills.length) * 100).toFixed(1) + "%";
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

  if (!window.THREE) return;

  const THREE = window.THREE;
  let meshFrame = 0;
  let pageHidden = false;
  document.addEventListener("visibilitychange", function () {
    pageHidden = document.hidden;
  });

  const meshCanvas = document.getElementById("holo-3d-canvas");
  let product = null;

  function makeLabelTexture(text) {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 160;
    const g = canvas.getContext("2d");
    g.clearRect(0, 0, 512, 160);
    g.fillStyle = "rgba(5, 8, 17, 0.82)";
    g.beginPath();
    g.roundRect(16, 28, 480, 104, 18);
    g.fill();
    g.strokeStyle = "#5eead4";
    g.lineWidth = 3;
    g.stroke();
    g.fillStyle = "#5eead4";
    g.font = "600 22px sans-serif";
    g.textAlign = "center";
    g.fillText("LIVE PRINT", 256, 62);
    g.fillStyle = "#f8fafc";
    g.font = "700 46px sans-serif";
    g.fillText(text, 256, 112);
    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    return tex;
  }

  function disposeObject(root) {
    root.traverse(function (obj) {
      if (obj.geometry) obj.geometry.dispose();
      if (!obj.material) return;
      const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
      mats.forEach(function (mat) {
        if (mat.map) mat.map.dispose();
        mat.dispose();
      });
    });
  }

  function buildMerchandise(kind, color, label) {
    const group = new THREE.Group();
    const cloth = new THREE.MeshStandardMaterial({
      color: new THREE.Color(color),
      roughness: 0.46,
      metalness: 0.06,
    });
    const trim = new THREE.MeshStandardMaterial({
      color: 0xf8fafc,
      roughness: 0.35,
      metalness: 0.04,
    });

    if (kind === "mug") {
      group.add(new THREE.Mesh(new THREE.CylinderGeometry(0.78, 0.66, 1.45, 40), cloth));
      const cavity = new THREE.Mesh(
        new THREE.CylinderGeometry(0.62, 0.52, 1.15, 32),
        new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.18 })
      );
      cavity.position.y = 0.18;
      const handle = new THREE.Mesh(new THREE.TorusGeometry(0.4, 0.09, 16, 28, Math.PI), cloth);
      handle.position.set(0.82, 0.02, 0);
      handle.rotation.z = -Math.PI / 2;
      group.add(cavity, handle);
    } else if (kind === "cap") {
      const crown = new THREE.Mesh(
        new THREE.SphereGeometry(0.86, 32, 18, 0, Math.PI * 2, 0, Math.PI / 2),
        cloth
      );
      crown.scale.set(1.05, 0.58, 1);
      const brim = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.08, 0.78), cloth);
      brim.position.set(0, -0.02, 0.78);
      const button = new THREE.Mesh(new THREE.SphereGeometry(0.1, 16, 12), trim);
      button.position.y = 0.5;
      group.add(crown, brim, button);
    } else {
      const torso = new THREE.Mesh(new THREE.BoxGeometry(1.55, 1.9, 0.38), cloth);
      const left = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.42, 0.36), cloth);
      left.position.set(-1.02, 0.62, 0);
      left.rotation.z = 0.55;
      const right = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.42, 0.36), cloth);
      right.position.set(1.02, 0.62, 0);
      right.rotation.z = -0.55;
      const collar = new THREE.Mesh(new THREE.TorusGeometry(0.26, 0.07, 10, 24), trim);
      collar.rotation.x = Math.PI / 2;
      collar.position.y = 0.98;
      group.add(torso, left, right, collar);
      if (kind === "jersey") {
        torso.scale.set(1.08, 1.06, 1);
        const stripe = new THREE.Mesh(
          new THREE.BoxGeometry(1.62, 0.12, 0.4),
          new THREE.MeshStandardMaterial({ color: 0x5eead4, roughness: 0.3, emissive: 0x0f766e, emissiveIntensity: 0.35 })
        );
        stripe.position.y = 0.15;
        group.add(stripe);
      }
    }

    const labelMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(kind === "cap" ? 0.9 : 1.2, 0.38),
      new THREE.MeshBasicMaterial({ map: makeLabelTexture(label), transparent: true, depthTest: false })
    );
    if (kind === "mug") labelMesh.position.set(0, 0.08, 0.92);
    else if (kind === "cap") labelMesh.position.set(0, 0.12, 0.72);
    else labelMesh.position.set(0, 0.08, 0.32);
    labelMesh.name = "printLabel";
    group.add(labelMesh);
    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(1.35, 40),
      new THREE.MeshBasicMaterial({ color: 0x2dd4bf, transparent: true, opacity: 0.16 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = kind === "mug" ? -0.78 : kind === "cap" ? -0.22 : -1.02;
    group.add(floor);
    group.scale.setScalar(kind === "cap" ? 1.15 : 0.92);
    group.userData.kind = kind;
    return group;
  }

  function ensureProductStudio() {
    if (product || !meshCanvas || !turntable) return;
    const renderer = new THREE.WebGLRenderer({ canvas: meshCanvas, alpha: true, antialias: true });
    renderer.setClearColor(0x000000, 0);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 20);
    camera.position.set(0, 0.15, 5.6);
    scene.add(new THREE.AmbientLight(0xffffff, 0.72));
    const key = new THREE.DirectionalLight(0xffffff, 1.15);
    key.position.set(2.4, 3.2, 4);
    const rim = new THREE.PointLight(0x2dd4bf, 1.4, 12);
    rim.position.set(-2.2, 1.2, 2);
    scene.add(key, rim);
    const root = new THREE.Group();
    scene.add(root);

    let dragging = false;
    let lastX = 0;
    let spin = 0.35;
    turntable.addEventListener("pointerdown", function (e) {
      dragging = true;
      lastX = e.clientX;
      spin = 0;
      turntable.classList.add("is-dragging");
      turntable.setPointerCapture(e.pointerId);
    });
    turntable.addEventListener("pointermove", function (e) {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      lastX = e.clientX;
      root.rotation.y += dx * 0.01;
    });
    function endDrag() {
      dragging = false;
      spin = reduce ? 0 : 0.35;
      turntable.classList.remove("is-dragging");
    }
    turntable.addEventListener("pointerup", endDrag);
    turntable.addEventListener("pointercancel", endDrag);

    function resizeMesh() {
      const width = turntable.clientWidth || 320;
      const height = turntable.clientHeight || 240;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
    }
    resizeMesh();
    window.addEventListener("resize", resizeMesh);

    product = { renderer: renderer, scene: scene, camera: camera, root: root, resize: resizeMesh, get dragging() { return dragging; }, get spin() { return spin; } };

    function renderMesh() {
      meshFrame = requestAnimationFrame(renderMesh);
      if (pageHidden || studioMode !== "mesh") return;
      if (!dragging && !reduce) root.rotation.y += spin * 0.01;
      renderer.render(scene, camera);
    }
    meshFrame = requestAnimationFrame(renderMesh);
  }

  function syncMesh() {
    if (!window.THREE || studioMode !== "mesh") return;
    ensureProductStudio();
    if (!product) return;
    product.resize();
    const next = buildMerchandise(activeItem, activeColor, cleanPrintText());
    if (product.current) {
      next.rotation.copy(product.current.rotation);
      product.root.remove(product.current);
      disposeObject(product.current);
    }
    product.root.add(next);
    product.current = next;
  }
})();
