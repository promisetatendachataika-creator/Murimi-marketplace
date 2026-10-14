/*
 * common.js - small helpers shared by the pages (listing page first; app.js and
 * account.js will move onto these too). Loaded before the page's own script.
 *   Murimi.esc("<b>")        -> "&lt;b&gt;"   (makes text safe to put in HTML)
 *   Murimi.usd(6.5)          -> "US$6.50"
 *   Murimi.unitLabel("crate", 3) -> "crates"
 */
window.Murimi = (function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const STATIC = (document.body && document.body.dataset.static) || "/static/web/";

  const PHOTOS = { Maize: "maize", Tobacco: "tobacco", Tomatoes: "tomatoes", Potatoes: "potatoes", "Sugar beans": "beans",
    Citrus: "citrus", Cotton: "cotton", Avocados: "avocados", Other: "grain", Broilers: "broilers", Eggs: "eggs" };
  const cropPhoto = (crop) => `${STATIC}img/crops/${PHOTOS[crop] || "grain"}.webp`;

  const UNIT_WORDS = {
    kg: ["kg", "kg"], tonne: ["tonne", "tonnes"], crate: ["crate", "crates"],
    pocket_15kg: ["pocket of 15 kg", "pockets of 15 kg"], bag_50kg: ["bag of 50 kg", "bags of 50 kg"],
    bird: ["bird", "birds"], tray_30: ["tray of 30 eggs", "trays of 30 eggs"],
  };
  const unitLabel = (u, n) => (UNIT_WORDS[u] ? UNIT_WORDS[u][n === 1 ? 0 : 1] : u);

  const usd = (n) => "US$" + Number(n).toLocaleString("en-GB", { minimumFractionDigits: n < 100 ? 2 : 0, maximumFractionDigits: 2 });
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const shortDate = (iso) => new Date(String(iso).slice(0, 10) + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  const monthYear = (ym) => new Date(ym + "-15T12:00:00").toLocaleDateString("en-GB", { month: "long", year: "numeric" });
  function daysAgo(iso) {
    const d = Math.round((Date.now() - new Date(String(iso).slice(0, 10) + "T12:00:00")) / 86400000);
    return d <= 0 ? "today" : d === 1 ? "yesterday" : d < 21 ? `${d} days ago` : "on " + shortDate(iso);
  }
  function weeksAway(n) {
    if (n <= 3) return n === 1 ? "ready tomorrow" : `${n} days away`;
    const w = Math.ceil(n / 7);
    return w === 1 ? "1 week away" : `${w} weeks away`;
  }

  const ICON = {
    check: '<svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    star: '<svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.8l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z" fill="currentColor"/></svg>',
  };
  const stars = (n) => `<span class="stars" aria-label="${n} out of 5 stars">${ICON.star.repeat(Math.round(n))}</span>`;

  /* The fair-price meter: where the asking price sits against today's market. */
  function meterHTML(m) {
    if (m && m.stale) return `<div class="meter meter-none"><p>Market price is out of date: the last ${esc(m.market)} price was ${usd(m.usd)} on ${shortDate(m.date)}, ${m.age_days} days ago. Too old to compare.</p></div>`;
    if (!m) return `<div class="meter meter-none"><p>No recent market price for this product and unit.</p></div>`;
    const pct = Math.round(Math.abs(m.diff) * 100);
    const words = { below: `${pct}% below market`, at: "At market price", above: `${pct}% above market` }[m.band];
    const pos = Math.max(0, Math.min(100, 50 + (m.diff / 0.3) * 50));
    return `<div class="meter meter-${m.band}">
      <div class="meter-track" aria-hidden="true"><span class="meter-mid"></span><span class="meter-dot" style="left:${pos}%"></span></div>
      <p><strong>${words}</strong> <span class="meter-src">${esc(m.market)} ${usd(m.usd)}, ${shortDate(m.date)}</span></p>
    </div>`;
  }

  function toast(msg) {
    const t = $("#toast");
    if (!t) return;
    t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 4500);
  }

  function themeToggle(btn) {
    if (!btn) return;
    btn.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      btn.setAttribute("aria-label", next === "dark" ? "Switch to light mode" : "Switch to dark mode");
      try { localStorage.setItem("murimi-theme", next); } catch (e) { /* fine */ }
    });
  }

  // Which kind of account is logged in, in plain words.
  const ROLE_WORDS = { farmer: "Farmer", buyer: "Buyer", both: "Farmer and buyer" };
  const roleWords = (user) => (user && ROLE_WORDS[user.role]) || "";

  return { roleWords, $, $$, STATIC, cropPhoto, unitLabel, usd, esc, shortDate, monthYear, daysAgo, weeksAway, ICON, stars, meterHTML, toast, themeToggle };
})();
