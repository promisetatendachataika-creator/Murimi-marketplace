/*
 * app.js - the page logic. It asks MarketAPI (api.js) for data and draws it.
 * It never reads mock.js directly, so swapping in the real API later is easy.
 */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));

  // ---------- Small helpers ----------
  const CROP_LOOK = {
    "Maize": { icon: "🌽", tone: "maize" },
    "Tobacco": { icon: "🍂", tone: "soil" },
    "Tomatoes": { icon: "🍅", tone: "tomato" },
    "Potatoes": { icon: "🥔", tone: "soil" },
    "Sugar beans": { icon: "🫘", tone: "bean" },
    "Citrus": { icon: "🍊", tone: "citrus" },
    "Cotton": { icon: "🌿", tone: "leaf" },
    "Avocados": { icon: "🥑", tone: "leaf" },
    "Other": { icon: "🧺", tone: "leaf" },
  };
  const look = (crop) => CROP_LOOK[crop] || CROP_LOOK.Other;

  let UNITS = {};
  // How a unit reads next to a number: 1 crate, 3 crates, 20 bags of 50 kg.
  const UNIT_WORDS = {
    kg: ["kg", "kg"], tonne: ["tonne", "tonnes"], crate: ["crate", "crates"],
    pocket_15kg: ["pocket of 15 kg", "pockets of 15 kg"], bag_50kg: ["bag of 50 kg", "bags of 50 kg"],
  };
  const unitLabel = (u, n) => {
    const w = UNIT_WORDS[u];
    if (!w) return UNITS[u] || u;
    return n === 1 ? w[0] : w[1];
  };
  const usd = (n) => "US$" + Number(n).toLocaleString("en-GB", { minimumFractionDigits: n < 100 ? 2 : 0, maximumFractionDigits: 2 });
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const shortDate = (iso) => new Date(iso + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  function daysAgo(iso) {
    const d = Math.round((Date.now() - new Date(iso + "T12:00:00")) / 86400000);
    if (d <= 0) return "today";
    if (d === 1) return "yesterday";
    if (d < 21) return d + " days ago";
    return "on " + shortDate(iso);
  }

  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => (t.hidden = true), 4200);
  }

  // ---------- Theme (light by default, dark on request) ----------
  function setTheme(next) {
    document.documentElement.dataset.theme = next;
    $("#themeToggle").setAttribute("aria-label", next === "dark" ? "Switch to light mode" : "Switch to dark mode");
    try { localStorage.setItem("murimi-theme", next); } catch (e) { /* private mode: fine */ }
  }
  $("#themeToggle").addEventListener("click", () =>
    setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  if (document.documentElement.dataset.theme === "dark") setTheme("dark");

  // ---------- Dialogs ----------
  $$("[data-open]").forEach((b) => b.addEventListener("click", () => $("#" + b.dataset.open).showModal()));
  $$("dialog").forEach((d) => d.addEventListener("click", (e) => { if (e.target === d) d.close("cancel"); }));

  // ---------- Filters state ----------
  const state = { crop: "", province: "", max_price: "", sort: "newest", sell_today: false };

  function fillSelect(sel, items, keepFirst = true) {
    if (!keepFirst) sel.innerHTML = "";
    items.forEach((it) => {
      const o = document.createElement("option");
      o.value = typeof it === "string" ? it : it.value;
      o.textContent = typeof it === "string" ? it : it.label;
      sel.appendChild(o);
    });
  }

  function renderChips(crops) {
    const box = $("#cropChips");
    const all = [""].concat(crops.filter((c) => c !== "Tobacco" && c !== "Cotton")); // auction crops are sold elsewhere
    box.innerHTML = all.map((c) =>
      `<button type="button" class="chip" data-crop="${esc(c)}" aria-pressed="${state.crop === c}">` +
      (c ? `<span aria-hidden="true">${look(c).icon}</span> ${esc(c)}` : "All produce") + `</button>`).join("");
    $$(".chip", box).forEach((b) => b.addEventListener("click", () => { state.crop = b.dataset.crop; sync(); }));
  }

  // Keep every control in step with `state`, then reload listings.
  function sync() {
    $$("#cropChips .chip").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.crop === state.crop)));
    $("#fProvince").value = state.province;
    $("#heroCrop").value = state.crop;
    $("#heroProvince").value = state.province;
    $$(".pin").forEach((p) => p.classList.toggle("is-active", p.dataset.province === state.province));
    loadListings();
  }

  $("#fProvince").addEventListener("change", (e) => { state.province = e.target.value; sync(); });
  $("#fSort").addEventListener("change", (e) => { state.sort = e.target.value; sync(); });
  $("#fSellToday").addEventListener("change", (e) => { state.sell_today = e.target.checked; sync(); });
  let priceTimer;
  $("#fMaxPrice").addEventListener("input", (e) => {
    clearTimeout(priceTimer);
    priceTimer = setTimeout(() => { state.max_price = e.target.value; sync(); }, 300);
  });
  $("#filters").addEventListener("submit", (e) => e.preventDefault());

  $("#heroSearch").addEventListener("submit", (e) => {
    e.preventDefault();
    state.crop = $("#heroCrop").value;
    state.province = $("#heroProvince").value;
    sync();
    $("#browse").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });

  // ---------- Map pins ----------
  // Where each province sits on the map picture, in % from the top-left.
  const PIN_SPOTS = {
    "Mashonaland Central": [66, 15], "Mashonaland West": [52, 26], "Mashonaland East": [77, 31],
    "Harare": [51, 43], "Manicaland": [86, 49], "Midlands": [46, 56], "Matabeleland North": [17, 46],
    "Bulawayo": [23, 58], "Masvingo": [68, 63], "Matabeleland South": [56, 81],
  };

  function renderPins(byProvince) {
    const frame = $("#mapFrame");
    $$(".pin", frame).forEach((p) => p.remove());
    Object.entries(PIN_SPOTS).forEach(([prov, [x, y]]) => {
      const n = byProvince[prov] || 0;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "pin" + (n ? "" : " is-empty");
      b.dataset.province = prov;
      b.style.left = x + "%";
      b.style.top = y + "%";
      b.innerHTML = `<span class="pin-n">${n}</span><span class="pin-name">${esc(prov)}</span>`;
      b.setAttribute("aria-label", `${prov}: ${n} listing${n === 1 ? "" : "s"}. Show them.`);
      b.addEventListener("click", () => {
        state.province = state.province === prov ? "" : prov;
        sync();
        $("#browse").scrollIntoView({ behavior: "smooth" });
      });
      frame.appendChild(b);
    });
  }

  // ---------- Fair-price meter ----------
  function meterHTML(m) {
    if (!m) return `<div class="meter meter-none"><p>No recent market price for this crop and unit.</p></div>`;
    const pct = Math.round(Math.abs(m.diff) * 100);
    const words = { below: `${pct}% below market`, at: "At market price", above: `${pct}% above market` }[m.band];
    // Place the dot on a scale from -30% (left) to +30% (right); the market sits in the middle.
    const pos = Math.max(0, Math.min(100, 50 + (m.diff / 0.3) * 50));
    return `<div class="meter meter-${m.band}">
      <div class="meter-track" aria-hidden="true"><span class="meter-mid"></span><span class="meter-dot" style="left:${pos}%"></span></div>
      <p><strong>${words}</strong> <span class="meter-src">${esc(m.market)} ${usd(m.usd)}, ${shortDate(m.date)}</span></p>
    </div>`;
  }

  // ---------- Listings ----------
  let current = [];

  function cardHTML(l) {
    const lk = look(l.crop);
    const f = l.farmer;
    const del = { pickup: "Pickup", delivery: "Delivery", both: "Pickup or delivery" }[l.delivery];
    const left = l.quantity_left < l.quantity ? `${l.quantity_left} of ${l.quantity} ${unitLabel(l.unit, l.quantity)} left` : `${l.quantity} ${unitLabel(l.unit, l.quantity)} available`;
    return `<article class="card" aria-labelledby="l${l.id}">
      <div class="card-top tone-${lk.tone}">
        <span class="card-icon" aria-hidden="true">${lk.icon}</span>
        ${l.sell_today ? `<span class="tag tag-today">Must sell today</span>` : ""}
      </div>
      <div class="card-body">
        <h3 id="l${l.id}">${esc(l.crop)} <span class="variety">${esc(l.variety)}</span></h3>
        <p class="place">${esc(l.district)}, ${esc(l.province)}</p>
        <p class="price"><span class="price-n">${usd(l.price_usd)}</span> <span class="price-u">per ${esc(unitLabel(l.unit, 1))}</span></p>
        ${meterHTML(l.market)}
        <dl class="facts">
          <div><dt>Quantity</dt><dd>${left}</dd></div>
          <div><dt>Harvested</dt><dd>${daysAgo(l.harvested_on)}</dd></div>
          <div><dt>Getting it</dt><dd>${del}</dd></div>
        </dl>
        <div class="farmer">
          <span class="avatar" aria-hidden="true">${esc(f.name.charAt(0))}</span>
          <span class="farmer-name">${esc(f.name)}${f.verified ? ` <span class="verified" title="Checked by a Murimi field officer">✓ Murimi Verified</span>` : ""}</span>
          <span class="farmer-record">${f.completed_orders ? `★ ${f.rating.toFixed(1)} from ${f.completed_orders} orders` : "New seller"}</span>
        </div>
        <button class="btn btn-green btn-block" type="button" data-offer="${l.id}">Make an offer</button>
      </div>
    </article>`;
  }

  async function loadListings() {
    const grid = $("#listingGrid");
    grid.setAttribute("aria-busy", "true");
    const data = await MarketAPI.listListings(state);
    current = data.results;
    grid.removeAttribute("aria-busy");
    $("#resultCount").textContent = data.count === 1 ? "1 listing" : `${data.count} listings`;
    if (!data.count) {
      grid.innerHTML = `<div class="empty"><p><strong>Nothing matches yet.</strong> Try another province or crop, or post a buyer request so farmers can come to you.</p>
        <button class="btn btn-outline" type="button" id="clearFilters">Show all produce</button></div>`;
      $("#clearFilters").addEventListener("click", () => {
        Object.assign(state, { crop: "", province: "", max_price: "", sell_today: false });
        $("#fMaxPrice").value = ""; $("#fSellToday").checked = false; sync();
      });
      return;
    }
    grid.innerHTML = current.map(cardHTML).join("");
    $$("[data-offer]", grid).forEach((b) => b.addEventListener("click", () => openOffer(Number(b.dataset.offer))));
  }

  // ---------- Offer dialog ----------
  let offering = null;
  function openOffer(id) {
    offering = current.find((l) => l.id === id);
    if (!offering) return;
    const l = offering;
    $("#offerSummary").innerHTML = `<span class="card-icon sm tone-${look(l.crop).tone}" aria-hidden="true">${look(l.crop).icon}</span>
      <div><strong>${esc(l.crop)}, ${esc(l.variety)}</strong><br><span>${usd(l.price_usd)} per ${esc(unitLabel(l.unit, 1))} from ${esc(l.farmer.name)}</span></div>`;
    const q = $("#offerQty");
    q.max = l.quantity_left; q.value = Math.min(10, l.quantity_left);
    $("#offerUnit").textContent = unitLabel(l.unit, 2);
    $("#offerQtyHint").textContent = `Up to ${l.quantity_left} available.`;
    const opts = l.delivery === "both" ? ["pickup", "delivery"] : [l.delivery];
    $("#offerDelivery").innerHTML = opts.map((o, i) =>
      `<label><input type="radio" name="delivery" value="${o}" ${i === 0 ? "checked" : ""}><span>${o === "pickup" ? "I'll collect" : "Deliver to me"}</span></label>`).join("");
    $("#offerError").textContent = "";
    $("#offerForm").message.value = "";
    updateTotal();
    $("#offerDialog").showModal();
  }
  function updateTotal() {
    if (!offering) return;
    const q = Number($("#offerQty").value) || 0;
    $("#offerTotal").innerHTML = q > 0 ? `Total <strong>${usd(q * offering.price_usd)}</strong> for ${q} ${unitLabel(offering.unit, q)}` : "";
  }
  $("#offerQty").addEventListener("input", updateTotal);

  $("#offerForm").addEventListener("submit", async (e) => {
    if (e.submitter && e.submitter.value === "cancel") return;
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true; btn.textContent = "Sending…";
    const res = await MarketAPI.sendOffer(offering.id, {
      quantity: form.quantity.value, delivery: form.delivery.value, message: form.message.value.trim(),
    });
    btn.disabled = false; btn.textContent = "Send offer";
    if (!res.ok) {
      const errs = res.body.errors || {};
      $("#offerError").textContent = errs.quantity || res.body.error;
      return;
    }
    $("#offerDialog").close("send");
    toast(`Offer sent to ${offering.farmer.name}. You'll get their WhatsApp number when they accept. (Demo: nothing was really sent.)`);
  });

  // ---------- Sell dialog ----------
  function updateSellCheck() {
    const f = $("#sellForm");
    const m = MarketAPI.fairPrice(f.crop.value, f.unit.value, Number(f.price.value));
    const box = $("#sellPriceCheck");
    if (!f.price.value) {
      const ref = MarketAPI.fairPrice(f.crop.value, f.unit.value, 1);
      box.innerHTML = ref ? `<p>Today at ${esc(ref.market)}: <strong>${usd(ref.usd)}</strong> per ${esc(unitLabel(f.unit.value, 1))}.</p>` : "";
      return;
    }
    box.innerHTML = meterHTML(m);
  }
  ["change", "input"].forEach((ev) => $("#sellForm").addEventListener(ev, (e) => {
    if (["crop", "unit", "price"].includes(e.target.name)) updateSellCheck();
  }));
  $("#sellForm").addEventListener("submit", async (e) => {
    if (e.submitter && e.submitter.value === "cancel") return;
    e.preventDefault();
    const f = e.target;
    const missing = $$("[required]", f).find((i) => !i.value.trim());
    if (missing) {
      $("#sellError").textContent = `Please fill in "${missing.closest("label").querySelector("span").textContent}".`;
      missing.focus();
      return;
    }
    $("#sellError").textContent = "";
    await MarketAPI.createListing(Object.fromEntries(new FormData(f)));
    $("#sellDialog").close("send");
    f.reset(); updateSellCheck();
    toast("Listing published. (Demo: it isn't saved yet. That comes with the listings API.)");
  });

  // ---------- Buyer requests ----------
  async function loadRequests() {
    const { results } = await MarketAPI.listRequests();
    $("#requestList").innerHTML = results.map((r) => {
      const pct = Math.round((r.filled / r.quantity) * 100);
      const still = r.quantity - r.filled;
      return `<article class="request">
        <div class="request-who"><span class="card-icon sm tone-${look(r.crop).tone}" aria-hidden="true">${look(r.crop).icon}</span>
          <div><h3>${r.quantity} ${unitLabel(r.unit, r.quantity)} of ${esc(r.crop.toLowerCase())}</h3>
          <p>${esc(r.buyer.name)}, ${esc(r.province)}. ${esc(r.repeat)}, needed by ${shortDate(r.needed_by)}.</p></div></div>
        <div class="fill">
          <div class="fill-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="Order filled"><span style="width:${pct}%"></span></div>
          <p>${r.suppliers ? `${r.suppliers} farmer${r.suppliers > 1 ? "s" : ""} supplying ${r.filled}.` : "No suppliers yet."} <strong>${still} ${unitLabel(r.unit, still)} still needed.</strong></p>
        </div>
        <button class="btn btn-outline" type="button" data-supply="${r.id}">Offer to supply</button>
      </article>`;
    }).join("");
    $$("[data-supply]").forEach((b) => b.addEventListener("click", () =>
      toast("Supplying part of a request arrives in the Buyer requests lesson. (Demo)")));
  }

  // ---------- How it works tabs ----------
  const tabs = $$('[role="tab"]');
  function selectTab(t) {
    tabs.forEach((x) => {
      const on = x === t;
      x.setAttribute("aria-selected", on); x.tabIndex = on ? 0 : -1;
      $("#" + x.getAttribute("aria-controls")).hidden = !on;
    });
    t.focus();
  }
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => selectTab(t));
    t.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") selectTab(tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length]);
    });
  });

  // ---------- Hero word: put the panel edge between "MURI" and "MI" ----------
  function placeSplit() {
    const word = $(".hero-word");
    const full = $(".hero-word-b", word);
    const probe = document.createElement("span");
    probe.textContent = "MURI";
    probe.style.cssText = "position:absolute;visibility:hidden;white-space:nowrap;font:inherit;letter-spacing:inherit";
    word.appendChild(probe);
    const share = probe.getBoundingClientRect().width / full.getBoundingClientRect().width;
    probe.remove();
    if (share > 0 && share < 1) word.style.setProperty("--split", (share * 100).toFixed(2) + "%");
  }
  placeSplit();
  if (document.fonts) document.fonts.ready.then(placeSplit);
  window.addEventListener("resize", placeSplit);

  // ---------- Start ----------
  async function start() {
    const meta = await MarketAPI.meta();
    meta.units.forEach((u) => (UNITS[u.value] = u.label));
    fillSelect($("#heroCrop"), meta.crops);
    fillSelect($("#heroProvince"), meta.provinces);
    fillSelect($("#fProvince"), meta.provinces);
    fillSelect($("#sellCrop"), meta.crops, false);
    fillSelect($("#sellUnit"), meta.units, false);
    fillSelect($("#sellProvince"), meta.provinces, false);
    $("#sellCrop").value = "Tomatoes"; $("#sellUnit").value = "crate";
    renderChips(meta.crops);

    const s = await MarketAPI.stats();
    $("#statListings").textContent = s.listings;
    $("#statFarmers").textContent = s.verified_farmers;
    $("#statProvinces").textContent = Object.keys(s.by_province).length;
    renderPins(s.by_province);

    updateSellCheck();
    loadListings();
    loadRequests();
  }
  start();
})();
