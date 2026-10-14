/*
 * listing.js - the listing details page (/listing/<id>/).
 * Reads the id from <body data-listing="101">, asks MarketAPI.getListing(id),
 * and draws: photos, price and fair-price meter, description, facts,
 * the offer form, the farmer's profile and reviews, and similar listings.
 */
(function () {
  "use strict";
  const { $, $$, esc, usd, unitLabel, shortDate, monthYear, daysAgo, weeksAway, ICON, stars, meterHTML, toast, cropPhoto, STATIC } = window.Murimi;
  const ID = Number(document.body.dataset.listing);
  let L = null;     // the listing
  let ME = null;    // who is logged in

  Murimi.themeToggle($("#themeToggle"));

  // ---------- Photos ----------
  // The farmer's own photos if there are any; otherwise one example photo, clearly labelled.
  function galleryHTML(l) {
    // Uploaded photos arrive as full addresses (or data: in the demo); sample ones are relative to /static/web/.
    const own = l.photos.map((p) => (/^(data:|\/|https?:)/.test(p) ? p : STATIC + p));
    const list = own.length ? own : [cropPhoto(l.crop)];
    const main = `<figure class="gal-main">
        <img id="galImg" src="${list[0]}" alt="${esc(l.crop)}, photo 1 of ${list.length}" width="960" height="600">
        ${own.length ? "" : `<figcaption class="photo-note">Example photo. The farmer hasn't added photos yet.</figcaption>`}
        ${l.ready_in_days > 0 ? `<span class="tag tag-soon">Coming soon: ${weeksAway(l.ready_in_days)}</span>` : l.sell_today ? `<span class="tag tag-today">Must sell today</span>` : ""}
      </figure>`;
    const thumbs = list.length > 1 ? `<div class="gal-thumbs" role="group" aria-label="Choose a photo">${list.map((src, i) =>
      `<button type="button" class="gal-thumb" data-src="${src}" data-n="${i + 1}" aria-pressed="${i === 0}"><img src="${src}" alt="Photo ${i + 1}" loading="lazy" width="960" height="600"></button>`).join("")}</div>` : "";
    return main + thumbs;
  }

  // ---------- Facts ----------
  function factsHTML(l) {
    const del = { pickup: "Collect from the farm", delivery: "Farmer delivers", both: "Collect, or the farmer delivers" }[l.delivery];
    const whenWord = { Eggs: "Collected", Broilers: "Ready since" }[l.crop] || "Harvested";
    const rows = [
      ["Available", l.sold_out ? "Sold out" : `${l.quantity_left} ${unitLabel(l.unit, l.quantity_left)}${l.quantity_left < l.quantity ? ` (of ${l.quantity})` : ""}`],
      l.ready_in_days > 0 ? ["Ready on", `${shortDate(l.available_from)}, ${weeksAway(l.ready_in_days)}`]
        : [whenWord, l.harvested_on ? `${shortDate(l.harvested_on)} (${daysAgo(l.harvested_on)})` : "Now"],
      ["Grade or variety", l.variety],
      ["Where", `${l.district}, ${l.province}`],
      ["Getting it", del],
      ["Listed", daysAgo(l.created_at)],
    ];
    return `<dl class="lp-facts">${rows.map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>`;
  }

  // ---------- Fair price, explained ----------
  function fairHTML(l) {
    const m = l.market;
    if (!m) return `<div class="lp-fair">${meterHTML(null)}<p class="lp-fair-note">We don't have a recent market price for ${esc(l.crop.toLowerCase())} sold per ${unitLabel(l.unit, 1)}, so we can't compare this one.</p></div>`;
    if (m.stale) return `<div class="lp-fair">${meterHTML(m)}<p class="lp-fair-note">We only compare with prices from the last 7 days, so an old price doesn't mislead you. Ask the farmer, or check today's price at the market.</p></div>`;
    const say = { below: "cheaper than", at: "about the same as", above: "dearer than" }[m.band];
    return `<div class="lp-fair">${meterHTML(m)}
      <p class="lp-fair-note">This price is ${say} what ${esc(l.crop.toLowerCase())} sold for at ${esc(m.market)} on ${shortDate(m.date)}
      (${usd(m.usd)} per ${unitLabel(l.unit, 1)}). Market prices change daily; use this as a guide.</p></div>`;
  }

  // ---------- The offer box ----------
  function offerHTML(l) {
    const soon = l.ready_in_days > 0;
    if (l.sold_out) return `<div class="offer-box" id="offer"><h2>Sold out</h2><p>This farmer has no more to sell right now.</p><a class="btn btn-outline btn-block" href="/#browse">See other produce</a></div>`;
    if (l.is_mine) return `<div class="offer-box" id="offer"><h2>This is your listing</h2><p>Offers from buyers appear in My account.</p><a class="btn btn-green btn-block" href="/account/">Open My account</a></div>`;
    const opts = l.delivery === "both" ? ["pickup", "delivery"] : [l.delivery];
    return `<form class="offer-box" id="offer" novalidate>
      <h2>${soon ? "Reserve before it's ready" : "Make an offer"}</h2>
      <label class="field"><span>How much do you want?</span>
        <div class="qty-row"><input name="quantity" type="number" min="1" max="${l.quantity_left}" step="1" inputmode="numeric" value="${Math.min(10, l.quantity_left)}" required>
        <span class="unit">${unitLabel(l.unit, 2)}</span></div>
        <small class="hint">Up to ${l.quantity_left}.</small></label>
      <fieldset class="field"><legend>Pickup or delivery</legend><div class="seg">${opts.map((o, i) =>
        `<label><input type="radio" name="delivery" value="${o}" ${i === 0 ? "checked" : ""}><span>${o === "pickup" ? "I'll collect" : "Deliver to me"}</span></label>`).join("")}</div></fieldset>
      <label class="field"><span>Message to the farmer (optional)</span>
        <textarea name="message" rows="2" maxlength="300" placeholder="For example: I can collect on Friday morning."></textarea></label>
      <p class="total" id="lpTotal"></p>
      <p class="form-error" id="lpError" role="alert"></p>
      <button class="btn btn-green btn-block" type="submit">${soon ? "Send reservation" : "Send offer"}</button>
      <p class="fine">${soon ? `Ready on ${shortDate(l.available_from)}. The farmer confirms closer to the date. ` : ""}Nothing is paid now. The farmer's WhatsApp number is shared after they accept.</p>
    </form>`;
  }

  // ---------- The farmer ----------
  function farmerHTML(f) {
    const avg = f.completed_orders ? f.rating.toFixed(1) : null;
    return `<section class="lp-farmer" aria-labelledby="farmerTitle">
      <div class="farmer-head">
        <span class="avatar avatar-lg" aria-hidden="true">${esc(f.name.charAt(0))}</span>
        <div>
          <h2 id="farmerTitle">${esc(f.name)}</h2>
          <p>${f.member_since ? `On Murimi since ${monthYear(f.member_since)}` : "New on Murimi"}</p>
        </div>
      </div>
      ${f.verified
        ? `<p class="trust trust-yes">${ICON.check} <span><strong>Murimi Verified.</strong> A Murimi field officer visited this farm${f.verified_on ? ` on ${new Date(f.verified_on + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}` : ""} and checked their ID and land.</span></p>`
        : `<p class="trust trust-no"><span><strong>Not verified yet.</strong> A field officer hasn't visited this farm. Meet in a safe public place, check the produce before you pay, and never pay in advance.</span></p>`}
      <div class="record">
        <div><span class="big">${f.completed_orders || 0}</span><span>completed orders</span></div>
        <div><span class="big">${avg ? `${avg}` : "None"}</span><span>${avg ? stars(f.rating) : "ratings yet"}</span></div>
      </div>
      ${f.reviews.length ? `<h3>What buyers say</h3><ul class="reviews">${f.reviews.map((r) =>
        `<li>${stars(r.stars)}<p>"${esc(r.comment)}"</p><span>${esc(r.by)}, ${daysAgo(r.date)}</span></li>`).join("")}</ul>` : ""}
    </section>`;
  }

  function miniCard(x, withPlace) {
    return `<a class="mini" href="/listing/${x.id}/">
      <img src="${cropPhoto(x.crop)}" alt="" loading="lazy" width="640" height="400">
      <span><strong>${esc(x.crop)}</strong> ${esc(x.variety)}<br>
      <span class="mini-price">${usd(x.price_usd)}</span> per ${unitLabel(x.unit, 1)}${withPlace ? `<br><span class="mini-place">${esc(x.district)}, ${esc(x.province)}</span>` : ""}</span>
    </a>`;
  }

  // ---------- The whole page ----------
  function render(l) {
    document.title = `${l.crop}, ${l.variety}: ${usd(l.price_usd)} per ${unitLabel(l.unit, 1)} | Murimi Market`;
    const shareText = encodeURIComponent(`${l.crop} (${l.variety}) for sale on Murimi Market: ${usd(l.price_usd)} per ${unitLabel(l.unit, 1)}, ${l.district}. ${location.href}`);
    $("#lpBody").innerHTML = `
      <div class="lp-grid">
        <div class="lp-gallery">${galleryHTML(l)}</div>

        <div class="lp-info">
          <p class="lp-place">${esc(l.district)}, ${esc(l.province)}</p>
          <h1>${esc(l.crop)} <span class="variety">${esc(l.variety)}</span></h1>
          <p class="lp-price"><span class="price-n">${usd(l.price_usd)}</span> <span class="price-u">per ${unitLabel(l.unit, 1)}</span>${l.price_zig ? ` <span class="price-zig">or ZiG ${Number(l.price_zig).toLocaleString("en-GB")}</span>` : ""}</p>
          ${fairHTML(l)}
          ${l.description ? `<div class="lp-desc"><h2>From the farmer</h2><p>${esc(l.description)}</p></div>` : ""}
          ${factsHTML(l)}
          <div class="lp-share">
            <a class="btn btn-whatsapp" href="https://wa.me/?text=${shareText}" target="_blank" rel="noopener">Share on WhatsApp</a>
            <button class="btn btn-outline" type="button" id="copyLink">Copy link</button>
            <button class="link-btn report" type="button" id="reportBtn">Report this listing</button>
          </div>
        </div>

        <aside class="lp-side">${offerHTML(l)}${farmerHTML(l.farmer)}</aside>
      </div>

      ${l.more_from_farmer.length ? `<section class="lp-more"><h2>More from ${esc(l.farmer.name)}</h2><div class="mini-row">${l.more_from_farmer.map((x) => miniCard(x)).join("")}</div></section>` : ""}
      ${l.similar.length ? `<section class="lp-more"><h2>Other ${esc(l.crop.toLowerCase())} for sale</h2><div class="mini-row">${l.similar.map((x) => miniCard(x, true)).join("")}</div></section>` : ""}
    `;

    // Phone bar
    if (!l.sold_out && !l.is_mine) {
      $("#barPrice").textContent = usd(l.price_usd);
      $("#barUnit").textContent = "per " + unitLabel(l.unit, 1);
      $("#barBtn").textContent = l.ready_in_days > 0 ? "Reserve" : "Make an offer";
      $("#lpBar").hidden = false;
    }
    wire(l);
  }

  // ---------- Buttons and the form ----------
  function wire(l) {
    $$(".gal-thumb").forEach((b) => b.addEventListener("click", () => {
      $("#galImg").src = b.dataset.src;
      $("#galImg").alt = `${l.crop}, photo ${b.dataset.n}`;
      $$(".gal-thumb").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    }));

    $("#copyLink").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(location.href); toast("Link copied. Paste it into WhatsApp or SMS."); }
      catch (e) { toast("Copy this address from the top of your browser: " + location.href); }
    });
    $("#reportBtn").addEventListener("click", () => toast("Thank you. Reporting comes with the staff tools; for now, WhatsApp us on +263 78 257 3320."));

    const form = $("form#offer");
    if (!form) return;
    const total = () => {
      const q = Number(form.quantity.value) || 0;
      $("#lpTotal").innerHTML = q > 0 ? `Total <strong>${usd(q * l.price_usd)}</strong> for ${q} ${unitLabel(l.unit, q)}` : "";
    };
    form.quantity.addEventListener("input", total);
    total();

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      const label = btn.textContent;
      btn.disabled = true; btn.textContent = "Sending…";
      const res = await MarketAPI.sendOffer(l.id, { quantity: form.quantity.value, delivery: form.delivery.value, message: form.message.value.trim() });
      btn.disabled = false; btn.textContent = label;
      if (!res.ok) {
        if (res.status === 401) {
          $("#lpError").innerHTML = `Please <a href="/login/?next=/listing/${l.id}/">log in</a> or <a href="/register/?next=/listing/${l.id}/">create an account</a> to send offers. It's free.`;
        } else {
          $("#lpError").textContent = (res.body.errors || {}).quantity || res.body.error;
        }
        return;
      }
      form.innerHTML = `<h2>${l.ready_in_days > 0 ? "Reservation sent" : "Offer sent"}</h2>
        <p>${esc(l.farmer.name)} will accept or decline. You'll get their WhatsApp number as soon as they accept.</p>
        <a class="btn btn-green btn-block" href="/account/">Follow it in My account</a>`;
      $("#lpBar").hidden = true;
    });
  }

  // ---------- Start ----------
  async function start() {
    if (MarketAPI.me) {
      ME = (await MarketAPI.me()).user;
      $("#loginLink").hidden = !!ME;
      $("#accountLink").hidden = !ME;
    }
    const res = await MarketAPI.getListing(ID);
    $("#main").removeAttribute("aria-busy");
    if (!res.ok) {
      document.title = "Listing not found: Murimi Market";
      $("#lpBody").innerHTML = `<div class="empty"><h1>We can't find that listing</h1><p>${esc(res.body.error)} It may have sold out or been removed by the farmer.</p>
        <a class="btn btn-green" href="/#browse">See all produce</a></div>`;
      return;
    }
    L = res.body;
    render(L);
  }
  start();
})();
