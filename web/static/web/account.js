/*
 * account.js - the My account page (/account/).
 *   Offers on my produce  (farmer): accept or decline, then mark completed, then rate the buyer
 *   My listings           (farmer): what I'm selling, how much is left, mark sold out
 *   My orders             (buyer):  what I asked for, cancel while waiting, complete, rate the farmer
 * Like the other pages, it only talks to MarketAPI (api.js).
 */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));

  // ---------- Helpers (the same ones app.js uses; to be shared in one file later) ----------
  const STATIC = document.body.dataset.static || "/static/web/";
  const PHOTOS = { Maize: "maize", Tobacco: "tobacco", Tomatoes: "tomatoes", Potatoes: "potatoes", "Sugar beans": "beans",
    Citrus: "citrus", Cotton: "cotton", Avocados: "avocados", Other: "grain", Broilers: "broilers", Eggs: "eggs" };
  const UNIT_WORDS = {
    kg: ["kg", "kg"], tonne: ["tonne", "tonnes"], crate: ["crate", "crates"],
    pocket_15kg: ["pocket of 15 kg", "pockets of 15 kg"], bag_50kg: ["bag of 50 kg", "bags of 50 kg"],
    bird: ["bird", "birds"], tray_30: ["tray of 30 eggs", "trays of 30 eggs"],
  };
  const unitLabel = (u, n) => (UNIT_WORDS[u] ? UNIT_WORDS[u][n === 1 ? 0 : 1] : u);
  const usd = (n) => "US$" + Number(n).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const shortDate = (iso) => new Date(String(iso).slice(0, 10) + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  function when(iso) {
    const d = Math.round((Date.now() - new Date(String(iso).slice(0, 10) + "T12:00:00")) / 86400000);
    return d <= 0 ? "today" : d === 1 ? "yesterday" : d < 7 ? `${d} days ago` : "on " + shortDate(iso);
  }
  const thumb = (crop) => `<span class="thumb"><img src="${STATIC}img/crops/${PHOTOS[crop] || "grain"}.webp" alt="" width="640" height="400" loading="lazy"></span>`;
  const prettyPhone = (p) => (MarketAPI.prettyPhone ? MarketAPI.prettyPhone(p) : p);
  const STAR = '<svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.8l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z" fill="currentColor"/></svg>';
  const stars = (n) => `<span class="stars" aria-label="${n} out of 5 stars">${STAR.repeat(n)}</span>`;

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
    t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 4800);
  }

  // ---------- Theme ----------
  $("#themeToggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("murimi-theme", next); } catch (e) { /* fine */ }
  });

  // ---------- Tabs ----------
  const tabs = () => $$('[role="tab"]').filter((t) => !t.hidden);
  function selectTab(t, focus) {
    $$('[role="tab"]').forEach((x) => {
      const on = x === t;
      x.setAttribute("aria-selected", on); x.tabIndex = on ? 0 : -1;
      $("#" + x.getAttribute("aria-controls")).hidden = !on;
    });
    if (focus) t.focus();
    try { sessionStorage.setItem("murimi-acct-tab", t.id); } catch (e) { /* fine */ }
  }
  $$('[role="tab"]').forEach((t) => {
    t.addEventListener("click", () => selectTab(t));
    t.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const list = tabs(); const i = list.indexOf(t);
      selectTab(list[(i + (e.key === "ArrowRight" ? 1 : list.length - 1)) % list.length], true);
    });
  });

  // ---------- Status: a small 3-step track (Sent, Accepted, Completed) ----------
  const STATUS_WORDS = { pending: "Waiting for the farmer", accepted: "Accepted", completed: "Completed", declined: "Declined", cancelled: "Cancelled" };
  function track(o) {
    if (o.status === "declined" || o.status === "cancelled") {
      const words = o.status === "declined" ? (o.i_sent ? "They declined this offer" : "You declined this offer")
        : (o.i_sent ? "You cancelled this offer" : "They cancelled this offer");
      return `<p class="status status-${o.status}">${words}</p>`;
    }
    const steps = ["pending", "accepted", "completed"];
    const at = steps.indexOf(o.status);
    const names = ["Sent", "Accepted", "Completed"];
    return `<ol class="track" aria-label="Status: ${STATUS_WORDS[o.status]}">` +
      names.map((n, i) => `<li class="${i < at ? "done" : i === at ? "now" : ""}">${n}</li>`).join("") + `</ol>`;
  }

  // ---------- One offer / order card ----------
  function orderCard(o) {
    const farmerView = o.my_side === "farmer";
    const them = `<strong>${esc(o.other_party.name)}</strong>`;
    const who = o.i_sent ? (farmerView ? `To ${them}` : `Farmer: ${them}`) : (farmerView ? `From ${them}` : `From farmer ${them}`);
    // Supply offers (a farmer answering a buyer's request) get a small label so they're easy to tell apart.
    const kind = o.request_id ? `<p class="kind">${o.i_sent ? "Your offer to supply their request" : "Offer to supply your request"}</p>` : "";
    const delivery = o.delivery === "delivery" ? (farmerView ? "Wants delivery" : "Delivery") : (farmerView ? "Will collect" : "I'll collect");
    let action = "";

    // Contact reveal: the number only arrives from the API after "accepted".
    if (o.other_party.phone) {
      const text = encodeURIComponent(`Hello ${o.other_party.name}, this is about the Murimi order for ${o.quantity} ${unitLabel(o.unit, o.quantity)} of ${(o.product_name || o.crop).toLowerCase()}.`);
      action += `<div class="contact">
        <p>WhatsApp ${esc(o.other_party.name)}: <span class="phone">${esc(prettyPhone(o.other_party.phone))}</span></p>
        <a class="btn btn-whatsapp" href="https://wa.me/${o.other_party.phone.replace("+", "")}?text=${text}" rel="noopener" target="_blank">Open WhatsApp</a>
      </div>`;
    } else if (o.status === "pending") {
      action += `<p class="contact-wait">${o.can.includes("accept") ? `Accept to see ${esc(o.other_party.name)}'s WhatsApp number.` : `You'll get ${esc(o.other_party.name)}'s WhatsApp number when they accept.`}</p>`;
    }

    const btns = [];
    if (o.can.includes("accept")) btns.push(`<button class="btn btn-green" data-act="accept" data-id="${o.id}" type="button">Accept</button>`);
    if (o.can.includes("decline")) btns.push(`<button class="btn btn-outline" data-act="decline" data-id="${o.id}" data-confirm="Yes, decline" type="button">Decline</button>`);
    if (o.can.includes("cancel")) btns.push(`<button class="btn btn-outline" data-act="cancel" data-id="${o.id}" data-confirm="Yes, cancel it" type="button">Cancel my offer</button>`);
    if (o.can.includes("complete")) btns.push(`<button class="btn btn-green" data-act="complete" data-id="${o.id}" data-confirm="Yes, it's done" type="button">Mark as completed</button>`);
    if (btns.length) action += `<div class="btn-row">${btns.join("")}</div>`;

    if (o.can.includes("rate")) action += rateForm(o);
    if (o.my_rating) action += `<p class="rated">You rated ${farmerView ? "this buyer" : "this farmer"} ${stars(o.my_rating.stars)}${o.my_rating.comment ? ` "${esc(o.my_rating.comment)}"` : ""}</p>`;
    if (o.their_rating) action += `<p class="rated">${esc(o.other_party.name)} rated you ${stars(o.their_rating.stars)}${o.their_rating.comment ? ` "${esc(o.their_rating.comment)}"` : ""}</p>`;

    return `<article class="order order-${o.status}" id="order-${o.id}">
      ${thumb(o.crop)}
      <div class="order-main">
        ${kind}
        <h3>${esc(amountOf(o.quantity, o.unit, o.product_name || o.crop))} <span class="variety">${esc(o.variety)}</span></h3>
        <p class="order-who">${who}${endStop(o.other_party.name)} Sent ${when(o.created_at)}.</p>
        ${o.message ? `<blockquote>${esc(o.message)}</blockquote>` : ""}
        <dl class="order-facts">
          <div><dt>Total</dt><dd>${usd(o.total_usd)}</dd></div>
          <div><dt>Price</dt><dd>${usd(o.price_usd)} per ${unitLabel(o.unit, 1)}</dd></div>
          <div><dt>Getting it</dt><dd>${delivery}</dd></div>
          ${o.ready_on ? `<div><dt>Ready on</dt><dd>${shortDate(o.ready_on)}</dd></div>` : ""}
        </dl>
        ${track(o)}
      </div>
      <div class="order-side">${action}</div>
    </article>`;
  }

  function rateForm(o) {
    const whom = o.my_side === "farmer" ? "the buyer" : "the farmer";
    return `<form class="rate" data-id="${o.id}">
      <fieldset>
        <legend>How was ${whom}?</legend>
        <div class="star-pick">${[5, 4, 3, 2, 1].map((n) =>
          `<input type="radio" name="stars" value="${n}" id="s${o.id}-${n}"><label for="s${o.id}-${n}" title="${n} star${n > 1 ? "s" : ""}">${STAR}<span class="sr-only">${n} star${n > 1 ? "s" : ""}</span></label>`).join("")}</div>
      </fieldset>
      <input name="comment" maxlength="300" placeholder="A few words (optional)" aria-label="Comment">
      <p class="field-error" role="alert"></p>
      <button class="btn btn-green" type="submit">Save rating</button>
    </form>`;
  }

  // Group cards under plain headings, most urgent first: what needs YOUR answer comes first.
  const GROUPS = [
    ["Waiting for your answer", (o) => o.status === "pending" && o.can.includes("accept")],
    ["Waiting for the other side", (o) => o.status === "pending" && !o.can.includes("accept")],
    ["Accepted: arrange pickup or delivery", (o) => o.status === "accepted"],
    ["Finished", (o) => ["completed", "declined", "cancelled"].includes(o.status)],
  ];
  function grouped(rows, emptyText) {
    if (!rows.length) return `<div class="empty-box"><p>${emptyText}</p></div>`;
    return GROUPS.map(([title, test]) => {
      const part = rows.filter(test);
      return part.length ? `<h2 class="group-title">${title} <span>${part.length}</span></h2>${part.map(orderCard).join("")}` : "";
    }).join("");
  }
  const needsMe = (rows) => rows.filter((o) => o.status === "pending" && o.can.includes("accept")).length;

  // One plain sentence at the top of each tab, saying what it's for.
  const HELP = {
    offers: "People who want to buy from you, and your offers to supply buyers' requests. Accept to get their WhatsApp number.",
    listings: "Everything you're selling, how much is left, and offers waiting.",
    orders: "Things you want to buy, and farmers' offers to supply your requests. When a farmer accepts (or you accept a farmer), you get their WhatsApp number.",
    requests: "Notices you posted saying what you need. Farmers offer to supply all or part of each one.",
  };
  const help = (key) => `<p class="tab-help">${HELP[key]}</p>`;

  // ---------- Panels ----------
  // "Offers on my produce": everything where I'm the farmer (buyers' offers, and my offers to supply requests)
  async function loadOffers() {
    const res = await MarketAPI.offersReceived();
    if (!res.ok) return 0;
    const rows = res.body.results;
    const waiting = needsMe(rows);
    $("#countOffers").textContent = waiting || "";
    $("#panel-offers").innerHTML = help("offers") + grouped(rows, `No offers yet. When buyers send offers on your listings, they appear here. <a href="/">See the market</a>`);
    return waiting;
  }

  // "My orders": everything where I'm the buyer (my offers, and farmers' offers to supply my requests)
  async function loadOrders() {
    const res = await MarketAPI.myOrders();
    if (!res.ok) return [0, 0];
    const rows = res.body.results;
    const open = rows.filter((o) => o.status === "pending" || o.status === "accepted").length;
    $("#countOrders").textContent = needsMe(rows) || open || "";
    $("#panel-orders").innerHTML = help("orders") + grouped(rows, `You haven't sent any offers yet. <a href="/#browse">Find produce</a>`);
    return [needsMe(rows), open];
  }

  // "My requests": what I asked farmers for, how full each one is
  async function loadMyRequests() {
    if (!MarketAPI.myRequests) return;
    const res = await MarketAPI.myRequests();
    if (!res.ok) return;
    const rows = res.body.results;
    if (!rows.length) {
      $("#panel-requests").innerHTML = help("requests") + `<div class="empty-box"><p>You haven't posted a request. Tell farmers what you need and they offer to supply it. <a href="/#request">Post what you need</a></p></div>`;
      return;
    }
    const REPEAT = { once: "Once", weekly: "Every week", fortnightly: "Every 2 weeks", monthly: "Every month" };
    $("#panel-requests").innerHTML = help("requests") + rows.map((r) => {
      const pct = Math.round((r.filled / r.quantity) * 100);
      const closed = r.status === "closed";
      return `<article class="mine${closed ? " order-cancelled" : ""}">
        ${thumb(r.crop)}
        <div class="order-main">
          <h3>${esc(amountOf(r.quantity, r.unit, r.crop))}</h3>
          <p class="pill ${closed ? "pill-sold" : r.still_needed ? "pill-live" : "pill-soon"}">${closed ? "Closed" : r.still_needed ? "Open to offers" : "Fully supplied"}</p>
          <dl class="order-facts">
            <div><dt>Needed by</dt><dd>${shortDate(r.needed_by)}</dd></div>
            <div><dt>How often</dt><dd>${REPEAT[r.repeat] || esc(r.repeat)}</dd></div>
            <div><dt>Supplied</dt><dd>${r.filled} of ${r.quantity}, by ${r.suppliers} farmer${r.suppliers === 1 ? "" : "s"}</dd></div>
          </dl>
          <div class="stock-bar" aria-hidden="true"><span style="width:${pct}%"></span></div>
        </div>
        <div class="order-side">
          ${r.offers_waiting ? `<button class="link-btn" type="button" data-goto="tab-orders">${r.offers_waiting} supply offer${r.offers_waiting > 1 ? "s" : ""} waiting for your answer</button>` : `<p class="contact-wait">${closed ? "This request is closed." : "No offers waiting right now."}</p>`}
          ${closed ? "" : `<div class="btn-row"><button class="btn btn-outline" type="button" data-closereq="${r.id}" data-confirm="Yes, close it">Close request</button></div>`}
        </div>
      </article>`;
    }).join("");
  }

  async function loadListings() {
    const res = await MarketAPI.myListings();
    if (!res.ok) return;
    const rows = res.body.results;
    if (!rows.length) {
      $("#panel-listings").innerHTML = help("listings") + `<div class="empty-box"><p>You haven't listed anything yet. <a href="/#browse">List your produce</a></p></div>`;
      return;
    }
    const label = (l) => l.status === "review" ? ["soon", "Waiting for Murimi staff to check this product"]
      : l.status === "draft" ? ["draft", "Draft: only you can see it"]
      : l.status === "sold_out" ? ["sold", "Sold out"]
      : l.ready_in_days > 0 ? ["soon", `Coming soon: ready ${shortDate(l.available_from)}`] : ["live", "On the market"];
    $("#panel-listings").innerHTML = help("listings") + rows.map((l) => {
      const [cls, text] = label(l);
      const sold = l.quantity - l.quantity_left;
      return `<article class="mine">
        ${thumb(l.crop)}
        <div class="order-main">
          <h3>${esc(l.product_name || l.crop)} <span class="variety">${esc(l.variety)}</span></h3>
          <p class="pill pill-${cls}">${text}</p>
          <dl class="order-facts">
            <div><dt>Left</dt><dd>${l.quantity_left} of ${l.quantity} ${unitLabel(l.unit, l.quantity)}</dd></div>
            <div><dt>Price</dt><dd>${usd(l.price_usd)} per ${unitLabel(l.unit, 1)}</dd></div>
            <div><dt>Sold so far</dt><dd>${sold} ${unitLabel(l.unit, sold)}</dd></div>
          </dl>
          <div class="stock-bar" aria-hidden="true"><span style="width:${Math.round((sold / l.quantity) * 100)}%"></span></div>
        </div>
        <div class="order-side">
          ${l.pending_offers ? `<button class="link-btn" type="button" data-goto="tab-offers">${l.pending_offers} offer${l.pending_offers > 1 ? "s" : ""} waiting</button>` : ""}
          <div class="btn-row">
            <button class="btn btn-outline" type="button" data-edit="${l.id}">Edit</button>
            ${l.status === "active" ? `<button class="btn btn-outline" type="button" data-soldout="${l.id}" data-confirm="Yes, it's sold out">Mark sold out</button>` : ""}
          </div>
        </div>
      </article>`;
    }).join("");
  }

  // ---------- Buttons (one listener for the whole page) ----------
  // Buttons with data-confirm ask once more ("Yes, decline") before doing it.
  function needsConfirm(btn) {
    if (!btn.dataset.confirm || btn.dataset.armed) return false;
    btn.dataset.armed = "1";
    const old = btn.textContent;
    btn.textContent = btn.dataset.confirm;
    btn.classList.add("is-armed");
    setTimeout(() => { delete btn.dataset.armed; btn.textContent = old; btn.classList.remove("is-armed"); }, 4000);
    return true;
  }

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;

    if (btn.dataset.goto) return selectTab($("#" + btn.dataset.goto), true);
    if (btn.dataset.edit) { location.href = `/?edit=${btn.dataset.edit}`; return; }

    if (btn.dataset.closereq) {
      if (needsConfirm(btn)) return;
      const res = await MarketAPI.closeRequest(Number(btn.dataset.closereq));
      toast(res.ok ? "Request closed. Farmers won't see it any more." : res.body.error);
      return refresh();
    }

    if (btn.dataset.soldout) {
      if (needsConfirm(btn)) return;
      const res = await MarketAPI.markSoldOut(Number(btn.dataset.soldout));
      toast(res.ok ? "Marked as sold out. Buyers won't see it any more." : res.body.error);
      return refresh();
    }

    if (btn.dataset.act) {
      if (needsConfirm(btn)) return;
      const id = Number(btn.dataset.id);
      btn.disabled = true;
      const res = await MarketAPI.orderAction(id, btn.dataset.act);
      if (!res.ok) { btn.disabled = false; toast(res.body.error); return; }
      const o = res.body;
      toast({
        accept: `Accepted. You can now WhatsApp ${o.other_party.name} to arrange ${o.delivery === "delivery" ? "delivery" : "pickup"}.`,
        decline: "Offer declined. The buyer will be told.",
        cancel: "Your offer is cancelled.",
        complete: "Marked as completed. Please rate them.",
      }[btn.dataset.act]);
      await refresh();
      const card = $("#order-" + id);
      if (card) card.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    }

    if (btn.id === "logoutBtn") { await MarketAPI.logout(); location.href = "/"; }
  });

  document.addEventListener("submit", async (e) => {
    const form = e.target.closest("form.rate");
    if (!form) return;
    e.preventDefault();
    const picked = form.querySelector("input[name=stars]:checked");
    const res = await MarketAPI.rateOrder(Number(form.dataset.id), picked ? picked.value : 0, form.comment.value);
    if (!res.ok) { form.querySelector(".field-error").textContent = (res.body.errors || {}).stars || res.body.error; return; }
    toast("Thank you. Your rating helps other buyers and farmers.");
    refresh();
  });

  // ---------- Start ----------
  let ME = null;
  async function refresh() {
    const isFarmer = ME.can_sell;
    const isBuyer = ME.can_buy;
    const [farmerWaiting, [buyerWaiting, open]] = await Promise.all([
      isFarmer ? loadOffers() : 0, isBuyer ? loadOrders() : [0, 0],
      isFarmer ? loadListings() : null, isBuyer ? loadMyRequests() : null]);
    const waiting = farmerWaiting + buyerWaiting;
    const bits = [];
    if (waiting) bits.push(`<strong>${waiting} offer${waiting > 1 ? "s" : ""}</strong> waiting for your answer`);
    if (open) bits.push(`<strong>${open} order${open > 1 ? "s" : ""}</strong> in progress`);
    $("#summary").innerHTML = bits.length ? bits.join(", ") + "." : "Nothing needs your attention right now.";
  }

  async function start() {
    const { user } = await MarketAPI.me();
    if (!user) { location.replace("/login/?next=/account/"); return; }
    ME = user;
    const roleWords = Murimi.roleWords(user);
    $("#hello").innerHTML = `Hello, ${esc(user.name.split(" ")[0])}${roleWords ? ` <span class="role-badge">${esc(roleWords)}</span>` : ""}`;
    $("#whoLine").innerHTML = `${roleWords ? `${esc(Murimi.roleSentence(roleWords))} ` : ""}WhatsApp <span class="phone">${esc(prettyPhone(user.phone))}</span>${user.username ? `, username <span class="phone">${esc(user.username)}</span>` : ""}.`;

    // Show only the tabs that fit: farmers see offers and listings, buyers see orders.
    const isFarmer = user.can_sell;
    const isBuyer = user.can_buy;
    $$('[role="tab"]').forEach((t) => (t.hidden = t.dataset.for === "farmer" ? !isFarmer : !isBuyer));

    // Staff neither buy nor sell, so there are no tabs to show them. Say so and point
    // them at the back office, instead of an empty page.
    if (!isFarmer && !isBuyer) {
      $(".acct-tabs").hidden = true;
      $("#summary").textContent = "";
      $("#panel-offers").hidden = false;
      $("#panel-offers").innerHTML = `<div class="empty-box">
        <p><strong>This is a staff account.</strong> Staff accounts don't buy or sell, so there's nothing to show here.</p>
        <p><a href="/admin/">Open the back office</a> to handle reports, prices and accounts.</p></div>`;
      $("#main").removeAttribute("aria-busy");
      return;
    }

    let first = tabs()[0];
    try { const saved = $("#" + sessionStorage.getItem("murimi-acct-tab")); if (saved && !saved.hidden) first = saved; } catch (e) { /* fine */ }
    selectTab(first);

    await refresh();
    $("#main").removeAttribute("aria-busy");
  }
  start();
})();
