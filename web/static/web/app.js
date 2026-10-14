/*
 * app.js - the page logic. It asks MarketAPI (api.js) for data and draws it.
 * All data comes from the server through MarketAPI; this file only draws.
 */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));

  // ---------- Small helpers ----------
  // Each crop's picture (in web/static/web/img/crops/) and a fallback colour.
  // A crop with photo: null shows its name on colour instead.
  const CROP_LOOK = {
    "Maize": { photo: "maize.webp", tone: "maize" },
    "Tobacco": { photo: "tobacco.webp", tone: "leaf" },
    "Tomatoes": { photo: "tomatoes.webp", tone: "tomato" },
    "Potatoes": { photo: "potatoes.webp", tone: "soil" },
    "Sugar beans": { photo: "beans.webp", tone: "bean" },
    "Citrus": { photo: "citrus.webp", tone: "citrus" },
    "Cotton": { photo: "cotton.webp", tone: "leaf" },
    "Avocados": { photo: "avocados.webp", tone: "leaf" },
    "Other": { photo: "grain.webp", tone: "maize" },
    "Broilers": { photo: "broilers.webp", tone: "soil" },
    "Eggs": { photo: "eggs.webp", tone: "citrus" },
  };
  // Where Django serves our static files, read from <body data-static="...">.
  const STATIC = document.body.dataset.static || "/static/web/";
  const cropPhoto = (crop) => { const p = look(crop).photo; return p ? STATIC + "img/crops/" + p : null; };

  /* The picture for a listing. The farmer's own photo wins (Lesson 7, uploads);
     until then we show an example photo of the crop and say so on the card. */
  function pictureHTML(item, size) {
    const own = item.photo_url || null;
    const src = own || cropPhoto(item.crop);
    const cls = size === "sm" ? "thumb" : "card-photo";
    if (!src) return `<span class="${cls} tone-${look(item.crop).tone}"><span class="photo-name">${esc(item.crop)}</span></span>`;
    return `<span class="${cls} tone-${look(item.crop).tone}"><img src="${src}" alt="" loading="lazy" decoding="async" width="640" height="400">` +
      (size !== "sm" && !own ? `<span class="photo-note">Example photo</span>` : "") + `</span>`;
  }

  // Tiny line icons (SVG), used instead of emoji or symbol characters.
  const ICON = {
    check: '<svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    star: '<svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.8l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z" fill="currentColor"/></svg>',
  };

  const look = (crop) => CROP_LOOK[crop] || CROP_LOOK.Other;

  let UNITS = {};
  // How a unit reads next to a number: 1 crate, 3 crates, 20 bags of 50 kg.
  const UNIT_WORDS = {
    kg: ["kg", "kg"], tonne: ["tonne", "tonnes"], crate: ["crate", "crates"],
    pocket_15kg: ["pocket of 15 kg", "pockets of 15 kg"], bag_50kg: ["bag of 50 kg", "bags of 50 kg"],
    bird: ["bird", "birds"], tray_30: ["tray of 30 eggs", "trays of 30 eggs"],
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
  // "2026-10-14T18:00" -> "6 pm"
  const clockTime = (iso) => { const h = iso ? new Date(iso).getHours() : 18; return h === 12 ? "12 noon" : h > 12 ? `${h - 12} pm` : `${h} am`; };
  const inDays = (n) => (n === 1 ? "tomorrow" : `in ${n} days`);
  /* How far away a coming-soon listing is, in weeks, for the label on the photo.
     We round UP (9 days = "2 weeks away") so buyers are never promised too early.
     Very close dates (1 to 3 days) are clearer in days. */
  function weeksAway(n) {
    if (n <= 3) return n === 1 ? "ready tomorrow" : `${n} days away`;
    const w = Math.ceil(n / 7);
    return w === 1 ? "1 week away" : `${w} weeks away`;
  }
  const isoDay = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };

  /* "20 bags of 50 kg of maize", but "10 trays of 30 eggs" and "40 broilers" (no repeated words). */
  function amountOf(qty, unit, crop) {
    if (crop === "Eggs" && unit === "tray_30") return `${qty} ${unitLabel(unit, qty)}`;
    if (crop === "Broilers" && unit === "bird") return `${qty} broiler${qty === 1 ? "" : "s"}`;
    return `${qty} ${unitLabel(unit, qty)} of ${String(crop).toLowerCase()}`;
  }
  // A sentence after a name that already ends in "." (like "Rutendo B.") needs no extra full stop.
  const endStop = (name) => (/[.!?]$/.test(name) ? "" : ".");

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
  const state = { crop: "", province: "", max_price: "", sort: "newest", sell_today: false, ready: "" };
  let META = null;

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
    const all = [""].concat(crops);
    box.innerHTML = all.map((c) =>
      `<button type="button" class="chip" data-crop="${esc(c)}" aria-pressed="${state.crop === c}">` +
      (c ? esc(c) : "Everything") + `</button>`).join("");
    $$(".chip", box).forEach((b) => b.addEventListener("click", () => { state.crop = b.dataset.crop; sync(); }));
  }

  // Keep every control in step with `state`, then reload listings.
  function sync(fromAddress) {
    $$("#cropChips .chip").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.crop === state.crop)));
    $("#fProvince").value = state.province;
    $("#heroCrop").value = state.crop;
    $("#heroProvince").value = state.province;
    $("#fSort").value = state.sort;
    $("#fMaxPrice").value = state.max_price;
    $("#fSellToday").checked = state.sell_today;
    const r = $(`#fReady input[value="${state.ready}"]`); if (r) r.checked = true;
    $$(".pin").forEach((p) => p.classList.toggle("is-active", p.dataset.province === state.province));
    if (!fromAddress) writeAddress();
    loadListings();
  }

  /* Keep the filters in the page address, e.g. /?crop=Tomatoes&province=Harare
     so refreshing keeps your search, and a link shared on WhatsApp opens the same view. */
  const FILTER_KEYS = ["crop", "province", "max_price", "sort", "ready", "sell_today"];
  function writeAddress() {
    const q = new URLSearchParams();
    FILTER_KEYS.forEach((k) => {
      const v = state[k];
      if (v && !(k === "sort" && v === "newest")) q.set(k, v === true ? "1" : v);
    });
    const demo = new URLSearchParams(location.search).get("demo");
    if (demo) q.set("demo", demo);
    const next = (q.toString() ? "?" + q : location.pathname) + (location.hash === "#browse" ? "#browse" : "");
    if (next !== location.search + location.hash) history.replaceState(null, "", next || "/");
  }
  function readAddress() {
    const q = new URLSearchParams(location.search);
    state.crop = q.get("crop") || "";
    state.province = q.get("province") || "";
    state.max_price = q.get("max_price") || "";
    state.sort = q.get("sort") || "newest";
    state.ready = ["now", "soon"].includes(q.get("ready")) ? q.get("ready") : "";
    state.sell_today = q.get("sell_today") === "1";
  }
  window.addEventListener("popstate", () => { readAddress(); sync(true); });

  $("#fProvince").addEventListener("change", (e) => { state.province = e.target.value; sync(); });
  $("#fSort").addEventListener("change", (e) => { state.sort = e.target.value; sync(); });
  $("#fSellToday").addEventListener("change", (e) => { state.sell_today = e.target.checked; sync(); });
  $("#fReady").addEventListener("change", (e) => { state.ready = e.target.value; sync(); });
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
    if (m && m.stale) return `<div class="meter meter-none"><p>Market price is out of date: the last ${esc(m.market)} price was ${usd(m.usd)} on ${shortDate(m.date)}, ${m.age_days} days ago. Too old to compare.</p></div>`;
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

  /* The "when" fact on a card. Coming soon: the ready date.
     Ready now: when it was harvested (crops), collected (eggs) or ready (broilers). */
  function readyFact(l) {
    if (l.ready_in_days > 0) return `<div><dt>Ready</dt><dd>${shortDate(l.available_from)} (${l.ready_in_days === 1 ? "1 day" : l.ready_in_days + " days"})</dd></div>`;
    const word = { Eggs: "Collected", Broilers: "Ready since" }[l.crop] || "Harvested";
    return `<div><dt>${word}</dt><dd>${l.harvested_on ? daysAgo(l.harvested_on) : "now"}</dd></div>`;
  }

  function cardHTML(l) {
    const f = l.farmer;
    const del = { pickup: "Pickup", delivery: "Delivery", both: "Pickup or delivery" }[l.delivery];
    const left = l.quantity_left < l.quantity ? `${l.quantity_left} of ${l.quantity} ${unitLabel(l.unit, l.quantity)} left` : `${l.quantity} ${unitLabel(l.unit, l.quantity)} available`;
    return `<article class="card" aria-labelledby="l${l.id}">
      <a class="card-top" href="/listing/${l.id}/" tabindex="-1" aria-hidden="true">
        ${pictureHTML(l)}
        ${l.sell_today ? `<span class="tag tag-today">Must sell today, until ${clockTime(l.ends_at)}</span>` : ""}
        ${l.ready_in_days > 0 ? `<span class="tag tag-soon">Coming soon: ${weeksAway(l.ready_in_days)}</span>` : ""}
      </a>
      <div class="card-body">
        <h3 id="l${l.id}"><a class="card-link" href="/listing/${l.id}/">${esc(l.crop)} <span class="variety">${esc(l.variety)}</span></a></h3>
        <p class="place">${esc(l.district)}, ${esc(l.province)}
          <a class="share-link" href="https://wa.me/?text=${encodeURIComponent(`${l.crop} for sale on Murimi Market: ${usd(l.price_usd)} per ${unitLabel(l.unit, 1)}, ${l.district}. ${location.origin}/listing/${l.id}/`)}" target="_blank" rel="noopener" aria-label="Share ${esc(l.crop)} on WhatsApp">Share</a></p>
        <p class="price"><span class="price-n">${usd(l.price_usd)}</span> <span class="price-u">per ${esc(unitLabel(l.unit, 1))}</span>${l.price_zig ? ` <span class="price-zig">or ZiG ${Number(l.price_zig).toLocaleString("en-GB")}</span>` : ""}</p>
        ${meterHTML(l.market)}
        <dl class="facts">
          <div><dt>Quantity</dt><dd>${left}</dd></div>
          ${readyFact(l)}
          <div><dt>Getting it</dt><dd>${del}</dd></div>
        </dl>
        <div class="farmer">
          <span class="avatar" aria-hidden="true">${esc(f.name.charAt(0))}</span>
          <span class="farmer-name">${esc(f.name)}${f.verified ? ` <span class="verified" title="Checked by a Murimi field officer">${ICON.check} Murimi Verified</span>` : ""}</span>
          <span class="farmer-record">${f.completed_orders ? `<span class="stars">${ICON.star} ${f.rating.toFixed(1)}</span> from ${f.completed_orders} orders` : "New seller"}</span>
        </div>
        <button class="btn btn-green btn-block" type="button" data-offer="${l.id}">${l.ready_in_days > 0 ? `Reserve for ${shortDate(l.available_from)}` : "Make an offer"}</button>
      </div>
    </article>`;
  }

  // Grey placeholder cards while waiting, so the page doesn't look empty on a slow connection.
  const skeletons = (n) => Array.from({ length: n }, () =>
    `<div class="card card-skeleton" aria-hidden="true"><div class="sk sk-photo"></div><div class="card-body"><div class="sk sk-line w60"></div><div class="sk sk-line w40"></div><div class="sk sk-line w80"></div><div class="sk sk-btn"></div></div></div>`).join("");

  // A friendly message instead of a blank page when the connection fails.
  function errorBox(where, retry) {
    where.innerHTML = `<div class="empty error-box" role="alert"><p><strong>We couldn't load the produce.</strong> Check your connection (data or Wi-Fi) and try again.</p>
      <button class="btn btn-green" type="button">Try again</button></div>`;
    where.querySelector("button").addEventListener("click", retry);
  }

  let page = 1;
  async function loadListings(more) {
    const grid = $("#listingGrid");
    const moreBtn = $("#loadMore");
    if (!more) { page = 1; grid.innerHTML = skeletons(6); }
    else { moreBtn.disabled = true; moreBtn.textContent = "Loading…"; }
    grid.setAttribute("aria-busy", "true");
    let data;
    try {
      data = await MarketAPI.listListings(Object.assign({}, state, { page }));
    } catch (err) {
      grid.removeAttribute("aria-busy");
      if (more) { moreBtn.disabled = false; moreBtn.textContent = "Try loading more again"; toast("Couldn't load more. Check your connection."); return; }
      $("#resultCount").textContent = "";
      moreBtn.hidden = true;
      errorBox(grid, () => loadListings());
      return;
    }
    grid.removeAttribute("aria-busy");
    current = more ? current.concat(data.results) : data.results;
    $("#resultCount").textContent = data.count === 1 ? "1 listing" : `${data.count} listings` + (data.count > current.length ? `, showing ${current.length}` : "");
    if (!data.count) {
      moreBtn.hidden = true;
      grid.innerHTML = `<div class="empty"><p><strong>Nothing matches yet.</strong> Try another province or crop, or tell farmers what you need and let them come to you.</p>
        <div class="btn-row"><button class="btn btn-outline" type="button" id="clearFilters">Show all produce</button>
        <button class="btn btn-green" type="button" id="emptyRequest">Post what you need</button></div></div>`;
      $("#emptyRequest").addEventListener("click", openRequest);
      $("#clearFilters").addEventListener("click", () => {
        Object.assign(state, { crop: "", province: "", max_price: "", sell_today: false, ready: "", sort: "newest" });
        sync();
      });
      return;
    }
    const html = data.results.map(cardHTML).join("");
    if (more) grid.insertAdjacentHTML("beforeend", html); else grid.innerHTML = html;
    page = data.page;
    moreBtn.hidden = !data.next;
    moreBtn.disabled = false;
    moreBtn.textContent = `Show more (${data.count - current.length} more)`;
  }
  // One listener for every card button (works for cards added by "Show more" too).
  $("#listingGrid").addEventListener("click", (e) => {
    const offer = e.target.closest("[data-offer]");
    if (offer) openOffer(Number(offer.dataset.offer));
  });
  $("#loadMore").addEventListener("click", () => { page += 1; loadListings(true); });

  // ---------- Offer dialog ----------
  let offering = null;
  function openOffer(id) {
    offering = current.find((l) => l.id === id);
    if (!offering) return;
    const l = offering;
    $("#offerSummary").innerHTML = `${pictureHTML(l, "sm")}
      <div><strong>${esc(l.crop)}, ${esc(l.variety)}</strong><br><span>${usd(l.price_usd)} per ${esc(unitLabel(l.unit, 1))} from ${esc(l.farmer.name)}</span></div>`;
    const q = $("#offerQty");
    q.max = l.quantity_left; q.value = Math.min(10, l.quantity_left);
    $("#offerUnit").textContent = unitLabel(l.unit, 2);
    $("#offerQtyHint").textContent = `Up to ${l.quantity_left} available.`;
    const opts = l.delivery === "both" ? ["pickup", "delivery"] : [l.delivery];
    $("#offerDelivery").innerHTML = opts.map((o, i) =>
      `<label><input type="radio" name="delivery" value="${o}" ${i === 0 ? "checked" : ""}><span>${o === "pickup" ? "I'll collect" : "Deliver to me"}</span></label>`).join("");
    const soon = l.ready_in_days > 0;
    $("#offerTitle").textContent = soon ? "Reserve before it's ready" : "Send an offer";
    $("#offerFine").textContent = soon
      ? `Ready on ${shortDate(l.available_from)}, ${weeksAway(l.ready_in_days)}. The farmer confirms closer to the date. Nothing is paid now.`
      : "Nothing is paid now. The farmer's number is shared after they accept.";
    $("#offerSend").textContent = soon ? "Send reservation" : "Send offer";
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
    btn.disabled = false; btn.textContent = offering.ready_in_days > 0 ? "Send reservation" : "Send offer";
    if (!res.ok) {
      if (res.status === 401) {
        // Not logged in: offer to log in, and come back to this page afterwards.
        $("#offerError").innerHTML = `Please <a href="/login/?next=/%23browse">log in</a> or <a href="/register/?next=/%23browse">create an account</a> to send offers. It's free.`;
        return;
      }
      const errs = res.body.errors || {};
      $("#offerError").textContent = errs.quantity || res.body.error;
      return;
    }
    $("#offerDialog").close("send");
    toast(offering.ready_in_days > 0
      ? `Reservation sent to ${offering.farmer.name} for ${shortDate(offering.available_from)}. Follow it in My account.`
      : `Offer sent to ${offering.farmer.name}. Follow it in My account; you'll get their WhatsApp number when they accept.`);
  });

  // ---------- Sell dialog ----------
  function updateSellCheck() {
    const f = $("#sellForm");
    const m = MarketAPI.fairPrice(f.crop.value, f.unit.value, Number(f.price.value));
    const box = $("#sellPriceCheck");
    if (!f.price.value) {
      const ref = MarketAPI.fairPrice(f.crop.value, f.unit.value, 1);
      box.innerHTML = !ref ? "" : ref.stale ? meterHTML(ref)
        : `<p>${ref.age_days <= 1 ? "Latest" : `${ref.age_days} days ago`} at ${esc(ref.market)}: <strong>${usd(ref.usd)}</strong> per ${esc(unitLabel(f.unit.value, 1))}.</p>`;
      return;
    }
    box.innerHTML = meterHTML(m);
  }
  // Only offer units that fit the product: birds for broilers, trays for eggs.
  function updateSellUnits() {
    const product = $("#sellCrop").value;
    const allowed = META.product_units[product] || META.product_units._crops;
    const keep = $("#sellUnit").value;
    fillSelect($("#sellUnit"), META.units.filter((u) => allowed.includes(u.value)), false);
    if (allowed.includes(keep)) $("#sellUnit").value = keep;
  }

  // "Ready now" or "Ready within 2 weeks": show the right date box.
  function updateSellWhen() {
    const f = $("#sellForm");
    const soon = f.when.value === "soon";
    const date = $("#sellDate"), harvest = $("#sellHarvest");
    $("#sellDateField").hidden = !soon;
    $("#sellHarvestField").hidden = soon;
    date.required = soon;
    date.min = isoDay(1);
    date.max = isoDay(META.ready_window_days);
    harvest.max = isoDay(0);
    harvest.min = isoDay(-60);
    if (!harvest.value) harvest.value = isoDay(0);
    if (!soon) date.value = "";
    // Eggs are "collected", broilers are "ready"; crops are "harvested".
    $("#sellHarvestLabel").textContent = { Eggs: "Collected on", Broilers: "Ready since" }[f.crop.value] || "Harvested on";
    // "Must sell today" only makes sense for produce that is ready now.
    $("#sellTodayField").hidden = soon;
    if (soon) f.sell_today.checked = false;
  }

  // ---------- Photos: checked and made smaller in the browser before sending ----------
  const MAX_PHOTOS = 3;
  const OK_TYPES = ["image/jpeg", "image/png", "image/webp"];
  let photos = [];        // data URLs of newly added photos (shrunk in the browser)
  let keptPhotos = [];    // photos already on the server: [{ id, url }]
  let droppedPhotos = []; // ids of server photos the farmer removed

  /* Resize to at most 1280 px on the long side and save as JPEG at 72% quality.
     A 4 MB phone photo usually ends up around 150 KB: cheaper for the farmer to
     send and for buyers to load. (The server will still check every file itself.) */
  function shrinkPhoto(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        const scale = Math.min(1, 1280 / Math.max(img.width, img.height));
        const c = document.createElement("canvas");
        c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        resolve(c.toDataURL("image/jpeg", 0.72));
      };
      img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("not an image")); };
      img.src = url;
    });
  }

  /* Draws the photos already saved first, then the newly added ones. Removing a saved photo
     remembers its id so the server can drop it when the farmer saves. */
  function drawPhotos() {
    $$(".photo-thumb", $("#photoPick")).forEach((x) => x.remove());
    const all = keptPhotos.map((p) => ({ src: p.url, id: p.id })).concat(photos.map((src) => ({ src })));
    all.forEach((item, i) => {
      const fig = document.createElement("figure");
      fig.className = "photo-thumb";
      fig.innerHTML = `<img src="${esc(item.src)}" alt="Photo ${i + 1}"><button type="button" aria-label="Remove photo ${i + 1}"><svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button>${i === 0 ? "<figcaption>Cover</figcaption>" : ""}`;
      fig.querySelector("button").addEventListener("click", () => {
        if (item.id != null) {
          droppedPhotos.push(item.id);
          keptPhotos = keptPhotos.filter((p) => p.id !== item.id);
        } else {
          photos.splice(i - keptPhotos.length, 1);
        }
        drawPhotos();
      });
      $("#photoPick").insertBefore(fig, $("#photoAdd"));
    });
    $("#photoAdd").hidden = all.length >= MAX_PHOTOS;
  }
  const photoCount = () => keptPhotos.length + photos.length;

  $("#photoInput").addEventListener("change", async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    for (const file of files) {
      if (photoCount() >= MAX_PHOTOS) { toast(`Up to ${MAX_PHOTOS} photos.`); break; }
      if (!OK_TYPES.includes(file.type)) { toast(`"${file.name}" isn't a JPG, PNG or WebP photo.`); continue; }
      if (file.size > 10 * 1024 * 1024) { toast(`"${file.name}" is bigger than 10 MB.`); continue; }
      try { photos.push(await shrinkPhoto(file)); } catch (err) { toast(`We couldn't open "${file.name}".`); }
    }
    drawPhotos();
  });

  $("#sellDesc").addEventListener("input", (e) => ($("#descCount").textContent = e.target.value.length));

  ["change", "input"].forEach((ev) => $("#sellForm").addEventListener(ev, (e) => {
    $("#sellError").textContent = "";          // an old error goes away once the farmer starts fixing things
    if (e.target.name === "crop") { updateSellUnits(); updateSellWhen(); }
    if (e.target.name === "when") updateSellWhen();
    if (["crop", "unit", "price"].includes(e.target.name)) updateSellCheck();
    if (e.target.name === "price") warnAboutWaitingOffers();
  }));

  // Selling needs an account: logged-out farmers go to log in first, then come back here.
  async function openSell() {
    const { user } = MarketAPI.me ? await MarketAPI.me() : { user: null };
    if (!user) { location.href = "/login/?next=" + encodeURIComponent("/#sell"); return; }
    if (user.role === "buyer") { openRequest(); return; }        // buyers: this button is "Post what you need"
    $("#sellDialog").showModal();
  }
  $("#sellBtn").addEventListener("click", openSell);

  function resetSell() {
    const f = $("#sellForm");
    f.reset(); photos = []; keptPhotos = []; droppedPhotos = []; drawPhotos();
    $("#descCount").textContent = "0";
    $("#sellCrop").value = "Tomatoes"; updateSellUnits(); $("#sellUnit").value = "crate";
    $("#sellHarvest").value = "";
    editing = null;
    $("#sellTitle").textContent = "List your produce";
    $("#sellFrozen").hidden = true;
    $("#sellOfferWarn").hidden = true;
    $("#sellCrop").disabled = $("#sellUnit").disabled = false;
    $("#sellSave").textContent = "Save as draft";
    $("#sellPublish").textContent = "Publish listing";
    $("#sellSave").hidden = false;
    updateSellWhen(); updateSellCheck();
  }

  /* ---------- Edit a listing ----------
     The same form, filled in with what's already there. The farmer reaches it from
     My account, which sends them to /?edit=<id>. */
  let editing = null;
  async function openEdit(id) {
    const user = await needAccount("farmer", `/?edit=${id}`);
    if (!user) return;
    const res = await MarketAPI.getListing(id);
    if (!res.ok || !res.body.is_mine) { toast(res.ok ? "That listing isn't yours." : res.body.error); return; }
    const l = res.body;
    resetSell();
    editing = l;
    const f = $("#sellForm");
    f.crop.value = l.crop; updateSellUnits(); f.unit.value = l.unit;
    f.variety.value = l.variety || "";
    f.quantity.value = l.quantity;
    f.price.value = l.price_usd;
    f.price_zig.value = l.price_zig == null ? "" : l.price_zig;
    f.province.value = l.province; f.district.value = l.district || "";
    f.delivery.value = l.delivery;
    f.description.value = l.description || "";
    $("#descCount").textContent = String((l.description || "").length);
    f.when.value = l.ready_in_days > 0 ? "soon" : "now";
    updateSellWhen();
    if (l.ready_in_days > 0) $("#sellDate").value = l.available_from;
    else if (l.harvested_on) $("#sellHarvest").value = l.harvested_on;
    f.sell_today.checked = !!l.sell_today;
    keptPhotos = (l.photo_items || []).slice(); drawPhotos();
    updateSellCheck();

    const sold = l.quantity - l.quantity_left;
    $("#sellTitle").textContent = "Edit your listing";
    $("#sellSave").hidden = l.status !== "draft";          // a draft can still be saved unfinished
    $("#sellSave").textContent = "Save as draft";
    $("#sellPublish").textContent = l.status === "draft" ? "Publish listing" : "Save changes";
    // Sold produce freezes the product and unit, because offers copied them.
    if (sold > 0 || l.pending_offers) {
      $("#sellCrop").disabled = $("#sellUnit").disabled = true;
      $("#sellFrozen").hidden = false;
      $("#sellFrozen").textContent = sold > 0
        ? `You've sold ${sold} ${unitLabel(l.unit, sold)} from this listing, so the product and unit can't change, and the quantity can't go below ${sold}.`
        : "This listing has offers waiting, so the product and unit can't change.";
    }
    $("#sellDialog").showModal();
  }

  // Changing the price while buyers are waiting: say what will happen, before saving.
  function warnAboutWaitingOffers() {
    const box = $("#sellOfferWarn");
    if (!editing || !editing.pending_offers) { if (box) box.hidden = true; return; }
    const changed = Number($("#sellPrice").value) !== Number(editing.price_usd);
    box.hidden = !changed;
    const n = editing.pending_offers;
    box.textContent = `${n} buyer${n > 1 ? "s have offers" : " has an offer"} waiting at ${usd(editing.price_usd)}. `
      + "Changing the price here doesn't change those offers: they stay as they were sent, and you can still accept or decline them.";
  }

  $("#sellForm").addEventListener("submit", async (e) => {
    if (e.submitter && e.submitter.value === "cancel") return;
    e.preventDefault();
    const f = e.target;
    const draft = e.submitter && e.submitter.value === "draft";
    // A draft can be half-finished; publishing needs every required box.
    if (!draft) {
      const missing = $$("[required]", f).find((i) => !i.disabled && !i.closest("[hidden]") && !i.value.trim());
      if (missing) {
        const label = missing.closest("label").querySelector("span").textContent;
        $("#sellError").textContent = `Please fill in "${label}".`;
        missing.focus();
        return;
      }
    }
    $("#sellError").textContent = "";
    const data = Object.fromEntries(new FormData(f));
    // A disabled box isn't sent by the browser, so put the frozen product and unit back.
    if (editing && $("#sellCrop").disabled) { data.crop = editing.crop; data.unit = editing.unit; }
    data.status = draft ? "draft" : "active";
    data.sell_today = !!data.sell_today;
    if (data.when === "now") { data.available = isoDay(0); data.harvested_on = data.harvested_on || isoDay(0); }
    else data.harvested_on = "";
    data.photos = photos.slice();
    data.remove_photos = droppedPhotos.slice();
    const wasEditing = editing;
    const btn = e.submitter; const label = btn.textContent;
    btn.disabled = true; btn.textContent = wasEditing && !draft ? "Saving…" : draft ? "Saving…" : "Publishing…";
    let res = wasEditing ? await MarketAPI.updateListing(wasEditing.id, data) : await MarketAPI.createListing(data);
    // Editing a draft and pressing Publish: save the changes first, then put it on the market.
    if (res.ok && wasEditing && wasEditing.status === "draft" && !draft) res = await MarketAPI.publishListing(wasEditing.id);
    btn.disabled = false; btn.textContent = label;
    if (!res.ok) {
      const errs = res.body.errors || {};
      $("#sellError").textContent = Object.values(errs)[0] || res.body.error;
      return;
    }
    $("#sellDialog").close("send");
    const l = res.body;
    resetSell();
    if (wasEditing) {
      toast(wasEditing.status === "draft" && !draft ? "Published. Buyers can send offers now." : "Your listing is updated.");
      if (new URLSearchParams(location.search).get("edit")) { location.href = "/account/"; return; }
      loadListings();
      return;
    }
    if (draft) { toast("Saved as a draft. Find it in My account, under My listings."); return; }
    toast(l.ready_in_days > 0
      ? `Listed as coming soon (${weeksAway(l.ready_in_days)}, ready ${shortDate(l.available_from)}). Buyers can reserve it now.`
      : "Your listing is on the market. Buyers can send offers now.");
    loadListings();
    MarketAPI.stats().then((st) => { renderPins(st.by_province); $("#statListings").textContent = st.listings; });
  });

  // ---------- Buyer requests ----------
  const REPEAT_WORDS = { once: "Once", weekly: "Every week", fortnightly: "Every 2 weeks", monthly: "Every month" };
  const DELIVERY_WORDS = { delivery: "Deliver to them", pickup: "They collect", either: "Delivery or collection" };
  let requests = [];

  async function loadRequests() {
    let results;
    try { ({ results } = await MarketAPI.listRequests()); }
    catch (err) { errorBox($("#requestList"), loadRequests); $("#requestList .error-box strong").textContent = "We couldn't load buyer requests."; return; }
    requests = results;
    if (!results.length) {
      $("#requestList").innerHTML = `<div class="empty"><p><strong>No open requests right now.</strong> Buyers: tell farmers what you need and they come to you.</p></div>`;
      return;
    }
    $("#requestList").innerHTML = results.map((r) => {
      const pct = Math.round((r.filled / r.quantity) * 100);
      const still = r.still_needed;
      const action = r.is_mine
        ? `<a class="btn btn-outline" href="/account/">Your request: see offers</a>`
        : still > 0 ? `<button class="btn btn-outline" type="button" data-supply="${r.id}">Offer to supply</button>`
        : `<span class="pill-full">Fully supplied</span>`;
      return `<article class="request">
        <div class="request-who">${pictureHTML(r, "sm")}
          <div><h3>${esc(amountOf(r.quantity, r.unit, r.crop))}</h3>
          <p>${esc(r.buyer.name)}${r.district ? `, ${esc(r.district)}` : ""}, ${esc(r.province)}. ${REPEAT_WORDS[r.repeat] || esc(r.repeat)}, needed by ${shortDate(r.needed_by)}.</p>
          <p class="request-terms">${DELIVERY_WORDS[r.delivery] || ""}${r.max_price_usd ? `. Pays up to <strong>${usd(r.max_price_usd)}</strong> per ${unitLabel(r.unit, 1)}` : ""}.</p>
          ${r.note ? `<p class="request-note">"${esc(r.note)}"</p>` : ""}</div></div>
        <div class="fill">
          <div class="fill-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="Request filled"><span style="width:${pct}%"></span></div>
          <p>${r.suppliers ? `${r.suppliers} farmer${r.suppliers > 1 ? "s" : ""} supplying ${r.filled}.` : "No suppliers yet."} <strong>${still} ${unitLabel(r.unit, still)} still needed.</strong></p>
        </div>
        ${action}
      </article>`;
    }).join("");
    $$("[data-supply]").forEach((b) => b.addEventListener("click", () => openSupply(Number(b.dataset.supply))));
  }

  // Both forms need the right kind of account; logged-out people log in first and come back.
  async function needAccount(kind, backTo) {
    const { user } = MarketAPI.me ? await MarketAPI.me() : { user: null };
    if (!user) { location.href = "/login/?next=" + encodeURIComponent(backTo); return null; }
    if (kind === "buyer" && user.role === "farmer") { toast("Your account is for selling. Posting requests needs a buyer account; WhatsApp us to change it."); return null; }
    if (kind === "farmer" && user.role === "buyer") { toast("Supplying needs a farmer account; WhatsApp us to change it."); return null; }
    return user;
  }

  // ----- Post a request (buyers) -----
  function updateReqUnits() {
    const allowed = META.product_units[$("#reqCrop").value] || META.product_units._crops;
    const keep = $("#reqUnit").value;
    fillSelect($("#reqUnit"), META.units.filter((u) => allowed.includes(u.value)), false);
    if (allowed.includes(keep)) $("#reqUnit").value = keep;
    updateReqPrice();
  }
  function updateReqPrice() {
    const ref = MarketAPI.fairPrice($("#reqCrop").value, $("#reqUnit").value, 1);
    $("#reqPriceCheck").innerHTML = ref && ref.stale ? meterHTML(ref) : ref ? `<p>Latest at ${esc(ref.market)}: <strong>${usd(ref.usd)}</strong> per ${esc(unitLabel($("#reqUnit").value, 1))}. A fair maximum helps farmers decide quickly.</p>` : "";
  }
  async function openRequest() {
    if (!(await needAccount("buyer", "/#request"))) return;
    const d = $("#reqDate"); d.min = isoDay(1); d.max = isoDay(90); if (!d.value) d.value = isoDay(7);
    $("#reqError").textContent = "";
    $("#requestDialog").showModal();
  }
  $("#postRequestBtn").addEventListener("click", openRequest);
  $("#reqCrop").addEventListener("change", updateReqUnits);
  $("#reqUnit").addEventListener("change", updateReqPrice);
  $("#requestForm").addEventListener("input", () => ($("#reqError").textContent = ""));
  $("#requestForm").addEventListener("submit", async (e) => {
    if (e.submitter && e.submitter.value === "cancel") return;
    e.preventDefault();
    const f = e.target;
    const data = Object.fromEntries(new FormData(f));
    if (data.grade) data.note = `${data.grade}. ${data.note || ""}`.trim();
    const res = await MarketAPI.createRequest(data);
    if (!res.ok) { $("#reqError").textContent = Object.values(res.body.errors || {})[0] || res.body.error; return; }
    $("#requestDialog").close("send");
    f.reset(); $("#reqCrop").value = "Tomatoes"; updateReqUnits();
    toast("Request posted. Farmers can offer to supply it now; their offers appear in My account.");
    await loadRequests();
    $("#requests").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });

  // ----- Offer to supply (farmers) -----
  let supplying = null;
  async function openSupply(id) {
    if (!(await needAccount("farmer", "/#requests"))) return;
    supplying = requests.find((r) => r.id === id);
    if (!supplying) return;
    const r = supplying;
    $("#supplySummary").innerHTML = `${pictureHTML(r, "sm")}<div><strong>${esc(r.buyer.name)} needs ${esc(amountOf(r.quantity, r.unit, r.crop))}</strong><br>
      <span>${r.still_needed} still needed, by ${shortDate(r.needed_by)}. ${DELIVERY_WORDS[r.delivery] || ""}.</span></div>`;
    const f = $("#supplyForm");
    f.reset();
    f.quantity.max = r.still_needed; f.quantity.value = r.still_needed;
    $("#supUnit").textContent = unitLabel(r.unit, 2);
    $("#supHint").textContent = `Up to ${r.still_needed}. Part of it is fine.`;
    $("#supPriceHint").textContent = r.max_price_usd ? `They pay up to ${usd(r.max_price_usd)}.` : "";
    if (r.max_price_usd) f.price.value = r.max_price_usd;
    const d = $("#supDate"); d.min = isoDay(0); d.max = isoDay(META.ready_window_days);
    d.value = r.needed_by <= d.max ? r.needed_by : isoDay(0);
    $("#supError").textContent = "";
    supTotal();
    $("#supplyDialog").showModal();
  }
  function supTotal() {
    const f = $("#supplyForm"); const q = Number(f.quantity.value) || 0, p = Number(f.price.value) || 0;
    $("#supTotal").innerHTML = q && p ? `Total <strong>${usd(q * p)}</strong> for ${q} ${unitLabel(supplying.unit, q)}` : "";
  }
  $("#supplyForm").addEventListener("input", () => { $("#supError").textContent = ""; supTotal(); });
  $("#supplyForm").addEventListener("submit", async (e) => {
    if (e.submitter && e.submitter.value === "cancel") return;
    e.preventDefault();
    const res = await MarketAPI.offerToSupply(supplying.id, Object.fromEntries(new FormData(e.target)));
    if (!res.ok) { $("#supError").textContent = Object.values(res.body.errors || {})[0] || res.body.error; return; }
    $("#supplyDialog").close("send");
    toast(`Offer sent to ${supplying.buyer.name}. Follow it in My account; you'll get their WhatsApp number when they accept.`);
  });

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

  // ---------- Who is logged in ----------
  async function showWho() {
    if (!MarketAPI.me) return;            // older api.js: no accounts yet
    const { user } = await MarketAPI.me();
    $("#loginLink").hidden = !!user;
    $("#whoBox").hidden = !user;
    const role = { farmer: "Farmer", buyer: "Buyer", both: "Farmer and buyer" }[user && user.role] || "";
    // Phones get the short form ("Farmer+buyer") so the top bar still fits.
    $("#whoRole").innerHTML = role === "Farmer and buyer"
      ? `<span class="lbl-long">Farmer and buyer</span><span class="lbl-short">Farmer+buyer</span>` : role;
    $("#whoRole").hidden = !role;
    $("#whoRole").title = role ? `You're logged in as a ${role.toLowerCase()}. Open My account` : "";
    if (user) { $("#whoName").textContent = "My account"; $("#whoName").title = `Logged in as ${user.name} (${role})`; }
    // A buyer can't sell, so the yellow button becomes what buyers do instead.
    $("#sellBtn").innerHTML = user && user.role === "buyer"
      ? `<span class="lbl-long">Post what you need</span><span class="lbl-short">Post a need</span>` : "Sell produce";
  }
  $("#logoutBtn").addEventListener("click", async () => {
    await MarketAPI.logout();
    await showWho();
    toast("You're logged out.");
  });
  // A message left by the log-in page ("Welcome back, Tendai.")
  try {
    const flash = sessionStorage.getItem("murimi-flash");
    if (flash) { sessionStorage.removeItem("murimi-flash"); setTimeout(() => toast(flash), 300); }
  } catch (e) { /* fine */ }

  // ---------- Server check (the first REAL request to Django) ----------
  async function showServerCheck() {
    const res = await MarketAPI.health();
    const box = $("#serverCheck");
    box.classList.toggle("is-bad", !res.ok);
    box.textContent = res.ok
      ? `Server: connected. Database: ${res.body.database_engine}, answered at ${res.body.server_time.slice(11, 16)}.`
      : res.status === 503 ? "Server: running, but the database isn't answering." : "Server: can't be reached right now.";
  }

  // ---------- Start ----------
  // Each step is guarded: if one part fails, the rest of the page still works,
  // and the error is written in the browser console (F12) so we can find it.
  async function step(name, work) {
    try { await work(); } catch (err) { console.error(`[Murimi] ${name} failed:`, err); }
  }

  async function start() {
    await step("who is logged in", showWho);
    readAddress();

    const meta = await MarketAPI.meta();
    META = meta;
    // Older api.js files only had "crops"; newer ones add poultry as "products".
    const products = meta.products || meta.crops || [];
    meta.product_units = meta.product_units || { _crops: meta.units.map((u) => u.value) };
    meta.ready_window_days = meta.ready_window_days || 14;
    meta.units.forEach((u) => (UNITS[u.value] = u.label));

    await step("menus", () => {
      fillSelect($("#heroProvince"), meta.provinces);
      fillSelect($("#fProvince"), meta.provinces);
      fillSelect($("#sellProvince"), meta.provinces, false);
      fillSelect($("#heroCrop"), products);
      fillSelect($("#sellCrop"), products, false);
      $("#sellCrop").value = "Tomatoes";
      updateSellUnits(); $("#sellUnit").value = "crate";
      updateSellWhen();
      renderChips(products);
      fillSelect($("#reqCrop"), products, false);
      fillSelect($("#reqProvince"), meta.provinces, false);
      fillSelect($("#reqRepeat"), meta.repeats || [{ value: "once", label: "Once" }], false);
      $("#reqCrop").value = "Tomatoes"; updateReqUnits();
    });

    await step("map and numbers", async () => {
      const s = await MarketAPI.stats();
      $("#statListings").textContent = s.listings;   // open listings right now (label says so)
      $("#statFarmers").textContent = s.verified_farmers;
      $("#statProvinces").textContent = Object.keys(s.by_province).length;
      renderPins(s.by_province);
    });

    await step("price check", updateSellCheck);
    step("server check", showServerCheck);
    const wantsEdit = new URLSearchParams(location.search).get("edit");
    if (wantsEdit) step("edit form", () => openEdit(Number(wantsEdit)));
    if (location.hash === "#sell") { history.replaceState(null, "", "/"); step("sell form", openSell); }
    if (location.hash === "#request") { history.replaceState(null, "", "/#requests"); step("request form", openRequest); }
    step("listings", () => sync(true));
    step("buyer requests", loadRequests);
  }
  start();
})();
