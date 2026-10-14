/*
 * api.js - the "waiter" between the page and the kitchen (the server).
 *
 * app.js never touches data directly. It asks MarketAPI, e.g.
 *     MarketAPI.listListings({ crop: "Tomatoes", sort: "price_asc" })
 * and gets back a Promise with JSON-shaped objects.
 *
 * TODAY:  the answers come from mock.js (sample data in the browser).
 * LATER:  each function becomes a real fetch() to Django, for example
 *         fetch("/api/listings/?crop=Tomatoes&sort=price_asc")
 *         The comment above each function shows the future URL.
 * app.js will not need to change, because the shape of the answers stays the same.
 */
window.MarketAPI = (function () {
  const M = window.MURIMI_MOCK;

  // A small pause so the page behaves like it's talking to a real server.
  /* A small pause so the page behaves like it's talking to a real server.
     Add ?demo=offline (or ?demo=slow) to the page address to practise bad connections. */
  const DEMO = new URLSearchParams(location.search).get("demo");
  const wait = (ms = 250) => new Promise((resolve, reject) => setTimeout(() =>
    DEMO === "offline" ? reject(new TypeError("Failed to fetch")) : resolve(), DEMO === "slow" ? ms * 10 : ms));
  const copy = (x) => JSON.parse(JSON.stringify(x));

  /* For later: Django's CSRF token, copied from the cookie into a header. */
  function csrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  /* Today's market price for a crop + unit, or null if we have none.
     LATER: the server adds this to each listing (Lesson 10, fair-price meter). */
  // Latest market price per product and unit, filled in by meta() from the server (prices app).
  let PRICES = [];
  let FRESH_DAYS = 7;
  function marketPriceFor(crop, unit) {
    return PRICES.find((p) => p.crop === crop && p.unit === unit) || null;   // server sends the newest only
  }

  /* Compare an asking price with the market: "below", "at" or "above".
     Within 5% either way counts as "at the market". */
  function fairPrice(crop, unit, priceUsd) {
    const m = marketPriceFor(crop, unit);
    if (!m || !(priceUsd > 0)) return null;
    const diff = (priceUsd - m.usd) / m.usd;
    const band = diff < -0.05 ? "below" : diff > 0.05 ? "above" : "at";
    const age = -daysUntil(m.date);
    // An old price could mislead a farmer or buyer, so we say it's old instead of comparing.
    if (age > FRESH_DAYS) return { stale: true, age_days: age, usd: m.usd, market: m.market, date: m.date };
    return { usd: m.usd, market: m.market, date: m.date, diff: diff, band: band, age_days: age };
  }

  /* Whole days from today until a date ("2026-10-23" -> 9). 0 or less = ready now.
     LATER: the server works this out and sends it as ready_in_days. */
  function daysUntil(iso) {
    const today = new Date(); today.setHours(12, 0, 0, 0);
    return Math.round((new Date(iso + "T12:00:00") - today) / 86400000);
  }

  // ================= Accounts (log in, register, codes) =================
  // The same error shape the server will send: { error, errors: { field: message } }
  const fail = (status, error, errors) => ({ ok: false, status, body: { error, errors: errors || {} } });
  const okay = (status, body) => ({ ok: true, status, body });

  /* Turn what people type into one form: +263771234567.
     Same idea as the Hub's normalize_phone (the server's copy is the one that counts).
     Accepts 0771234567, 771234567, 263771234567, +263 77 123 4567, 00263... */
  function normalizePhone(raw) {
    let p = String(raw || "").replace(/[\s\-().]/g, "");
    if (p.startsWith("00")) p = "+" + p.slice(2);
    if (p.startsWith("263")) p = "+" + p;
    if (p.startsWith("0")) p = "+263" + p.slice(1);
    if (/^7\d{8}$/.test(p)) p = "+263" + p;
    return /^\+2637\d{8}$/.test(p) ? p : null;
  }
  const prettyPhone = (p) => p.replace(/^\+263(\d{2})(\d{3})(\d{4})$/, "+263 $1 $2 $3");

  // Demo "database" of users and the logged-in user. Lives in this browser only.
  function store(key, value) {
    try {
      if (value === undefined) return JSON.parse(localStorage.getItem(key) || "null");
      if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, JSON.stringify(value));
    } catch (e) { return null; }
  }

  /* REAL server calls. Every POST carries the CSRF token in the X-CSRFToken header
     (Django's middleware refuses POSTs without it). Answers always come back as
     { ok, status, body } with body = the JSON, or our friendly error on no connection. */
  async function call(method, url, data) {
    const opts = { method, credentials: "same-origin", headers: { Accept: "application/json" } };
    if (method !== "GET") {
      opts.headers["Content-Type"] = "application/json";
      opts.headers["X-CSRFToken"] = csrfToken();
      opts.body = JSON.stringify(data || {});
    }
    try {
      const res = await fetch(url, opts);
      let body = {};
      try { body = await res.json(); } catch (e) { body = { error: "The server sent an unexpected answer.", errors: {} }; }
      return { ok: res.ok, status: res.status, body };
    } catch (err) {
      return { ok: false, status: 0, body: { error: "Can't reach the server. Check your connection and try again.", errors: {} } };
    }
  }
  // The demo features (offers, listings...) still read "who am I" from here until they move to the server too.
  const remember = (user) => store("murimi-demo-session", user || null);

  // ================= Offers and orders =================
  // Demo "database": orders and listing changes saved in this browser.
  const loadOrders = () => store("murimi-demo-orders") || copy(M.ORDERS);
  const saveOrders = (rows) => store("murimi-demo-orders", rows);
  const qtyLeft = () => store("murimi-demo-qty") || {};          // { listingId: quantity_left }
  const soldOut = () => store("murimi-demo-soldout") || [];      // [listingId, ...]

  // "data:image/jpeg;base64,..." -> a file the form can send
  function dataUrlToBlob(dataUrl) {
    const [head, b64] = dataUrl.split(",");
    const bytes = atob(b64);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    return new Blob([arr], { type: head.slice(5, head.indexOf(";")) });
  }

  // Offers accepted in this browser (sample offers), per listing, until offers move to the server.
  const acceptedHere = () => store("murimi-demo-qty") || {};     // { listingId: quantity accepted here }

  /* THE STATUS RULES. The server will have the same table.
     action: which statuses it may start from, who may do it, and the new status.
     "receiver" = whoever received the offer, "sender" = whoever sent it:
       a normal offer on a listing:      buyer sends,  farmer receives (proposed_by "buyer")
       a supply offer on a buyer request: farmer sends, buyer receives  (proposed_by "farmer") */
  const TRANSITIONS = {
    accept:   { from: ["pending"],  who: "receiver", to: "accepted" },
    decline:  { from: ["pending"],  who: "receiver", to: "declined" },
    cancel:   { from: ["pending"],  who: "sender",   to: "cancelled" },
    complete: { from: ["accepted"], who: "either",   to: "completed" },
  };
  // Am I the one who sent this offer?
  const iSent = (o, me) => ((o.proposed_by || "buyer") === "farmer") === (o.farmer.id === me.id);
  const allowed = (t, o, me) => t.who === "either" || (t.who === "sender") === iSent(o, me);

  // ================= Buyer requests =================
  const madeReqs = () => store("murimi-demo-requests") || [];
  const reqExtra = () => store("murimi-demo-reqfill") || {};       // { requestId: { filled, suppliers } }
  const closedReqs = () => store("murimi-demo-reqclosed") || [];
  /* A request with what happened in this browser added on top. */
  function liveRequest(r) {
    const x = reqExtra()[r.id] || { filled: 0, suppliers: 0 };
    r.filled = r.filled + x.filled;
    r.suppliers = r.suppliers + x.suppliers;
    r.still_needed = Math.max(0, r.quantity - r.filled);
    if (closedReqs().includes(r.id)) r.status = "closed";
    return r;
  }
  const allRequests = () => copy(M.REQUESTS.concat(madeReqs())).map(liveRequest);

  /* An order as one person sees it. The other side's phone number is
     only included once the order is accepted (the "contact reveal"). */
  function viewFor(o, me) {
    const iAmFarmer = o.farmer.id === me.id;
    const other = iAmFarmer ? o.buyer : o.farmer;
    const revealed = o.status === "accepted" || o.status === "completed";
    const mine = iAmFarmer ? o.ratings.by_farmer : o.ratings.by_buyer;
    const theirs = iAmFarmer ? o.ratings.by_buyer : o.ratings.by_farmer;
    const can = Object.keys(TRANSITIONS).filter((a) => TRANSITIONS[a].from.includes(o.status) && allowed(TRANSITIONS[a], o, me));
    if (o.status === "completed" && !mine) can.push("rate");
    return {
      id: o.id, listing_id: o.listing_id, crop: o.crop, variety: o.variety, unit: o.unit,
      price_usd: o.price_usd, quantity: o.quantity, total_usd: Math.round(o.quantity * o.price_usd * 100) / 100,
      delivery: o.delivery, message: o.message, status: o.status,
      created_at: o.created_at, accepted_at: o.accepted_at || null, completed_at: o.completed_at || null,
      my_side: iAmFarmer ? "farmer" : "buyer",
      proposed_by: o.proposed_by || "buyer", i_sent: iSent(o, me),
      request_id: o.request_id || null, ready_on: o.ready_on || null,
      other_party: { name: other.name, phone: revealed ? other.phone : null },
      my_rating: mine || null, their_rating: theirs || null,
      can,
    };
  }

  return {
    // ---------- Accounts: REAL (accounts/api.py) ----------
    /* POST /api/auth/login/  { identifier: number, username or email, password } */
    async login({ identifier, password }) {
      const res = await call("POST", "/api/auth/login/", { identifier, password });
      if (res.ok) remember(res.body.user);
      return res;
    },

    /* POST /api/auth/register/  -> 201 { phone, code_sent }  (account waits for the WhatsApp code) */
    register(data) { return call("POST", "/api/auth/register/", data); },

    /* POST /api/auth/verify/  { code } -> { user, next: "done" } or { next: "new_password" } */
    async verifyCode(code) {
      const res = await call("POST", "/api/auth/verify/", { code });
      if (res.ok && res.body.user) remember(res.body.user);
      return res;
    },

    /* POST /api/auth/resend/ */
    resendCode() { return call("POST", "/api/auth/resend/"); },

    /* POST /api/auth/forgot/  { phone }  (same answer whether or not the number has an account) */
    forgotPassword(phone) { return call("POST", "/api/auth/forgot/", { phone }); },

    /* POST /api/auth/password/  { password }  (only after a correct reset code) */
    setNewPassword(password) { return call("POST", "/api/auth/password/", { password }); },

    /* GET /api/auth/me/  -> { user } or { user: null } */
    async me() {
      const res = await call("GET", "/api/auth/me/");
      if (!res.ok) return { user: store("murimi-demo-session") };   // offline: use what we last knew
      remember(res.body.user);
      return { user: res.body.user };
    },

    /* POST /api/auth/logout/ */
    async logout() {
      const res = await call("POST", "/api/auth/logout/");
      remember(null);
      return res;
    },

    normalizePhone,
    prettyPhone,

    /* REAL (Lesson 3): GET /api/health/   The waiter's first real trip to the kitchen.
       fetch() sends the request; the server answers with JSON; .json() reads it.
       Returns { ok, status, body } like every other function here. */
    async health() {
      try {
        const res = await fetch("/api/health/", { headers: { Accept: "application/json" } });
        return { ok: res.ok, status: res.status, body: await res.json() };
      } catch (err) {
        // No answer at all: the phone is offline, or the server isn't running.
        return { ok: false, status: 0, body: { error: "Can't reach the server.", errors: {} } };
      }
    },

    /* REAL: GET /api/meta/  (menus + latest market prices) */
    async meta() {
      const res = await call("GET", "/api/meta/");
      if (!res.ok) throw new Error(res.body.error);
      PRICES = res.body.prices || [];
      FRESH_DAYS = res.body.price_fresh_days || 7;
      return res.body;
    },

    /* REAL: GET /api/listings/?crop=&province=&max_price=&ready=&sell_today=&sort=&page=
       Throws when the connection fails, so the page can show "We couldn't load the produce". */
    async listListings(filters = {}) {
      const q = new URLSearchParams();
      ["crop", "province", "max_price", "ready", "sort", "page"].forEach((k) => { if (filters[k]) q.set(k, filters[k]); });
      if (filters.sell_today) q.set("sell_today", "1");
      if (DEMO === "offline") throw new TypeError("Failed to fetch");       // practise bad connections: ?demo=offline
      if (DEMO === "slow") await wait(2500);
      const res = await call("GET", "/api/listings/?" + q);
      if (!res.ok) throw new Error(res.body.error);
      return res.body;
    },

    /* REAL: GET /api/stats/  (SQL: SELECT province, COUNT(*) ... GROUP BY province) */
    async stats() {
      const res = await call("GET", "/api/stats/");
      if (!res.ok) throw new Error(res.body.error);
      return res.body;
    },

    /* LATER: GET /api/requests/   (open requests whose date hasn't passed, soonest first) */
    async listRequests() {
      await wait(150);
      const me = store("murimi-demo-session");
      const rows = allRequests()
        .filter((r) => r.status === "open" && daysUntil(r.needed_by) >= 0)      // WHERE status='open' AND needed_by >= today
        .sort((a, b) => a.needed_by.localeCompare(b.needed_by));               // ORDER BY needed_by
      rows.forEach((r) => { r.is_mine = !!(me && r.buyer.id === me.id); delete r.buyer.id; });
      return { results: rows };
    },

    /* LATER: POST /api/requests/   A buyer posts what they need. */
    async createRequest(data) {
      await wait(400);
      const me = store("murimi-demo-session");
      if (!me) return fail(401, "Please log in to post a request.");
      if (me.role === "farmer") return fail(403, "Your account is for selling. Posting requests needs a buyer account.");
      const errors = {};
      const qty = Number(data.quantity), max = data.max_price === "" || data.max_price == null ? null : Number(data.max_price);
      const allowedUnits = M.PRODUCT_UNITS[data.crop] || M.PRODUCT_UNITS._crops;
      if (!M.CROPS.concat(M.POULTRY).includes(data.crop)) errors.crop = "Choose a product from the list.";
      if (!allowedUnits.includes(data.unit)) errors.unit = "That unit doesn't fit this product.";
      if (!Number.isInteger(qty) || qty < 1 || qty > 1000000) errors.quantity = "Enter a whole number, 1 or more.";
      if (!M.PROVINCES.includes(data.province)) errors.province = "Choose the province where you need it.";
      const d = daysUntil(data.needed_by || "");
      if (!data.needed_by || isNaN(d)) errors.needed_by = "Choose the date you need it by.";
      else if (d < 1) errors.needed_by = "Choose a date from tomorrow onwards.";
      else if (d > 90) errors.needed_by = "Requests can be up to 3 months ahead.";
      if (!M.REPEATS.some((x) => x.value === data.repeat)) errors.repeat = "Choose how often you need it.";
      if (max !== null && !(max > 0)) errors.max_price = "Enter a price above 0, or leave it empty.";
      if (!["delivery", "pickup", "either"].includes(data.delivery)) errors.delivery = "Choose delivery or collection.";
      if (String(data.note || "").length > 300) errors.note = "Keep the note under 300 characters.";
      if (Object.keys(errors).length) return fail(400, "Please check the form.", errors);
      const r = {
        id: Date.now(), buyer: { id: me.id, name: me.name, kind: "Buyer" }, crop: data.crop, quantity: qty, unit: data.unit,
        filled: 0, suppliers: 0, province: data.province, district: String(data.district || "").trim().slice(0, 60),
        needed_by: data.needed_by, repeat: data.repeat, max_price_usd: max, delivery: data.delivery,
        note: String(data.note || "").trim(), status: "open", created_at: new Date().toISOString().slice(0, 19),
      };
      store("murimi-demo-requests", madeReqs().concat([r]));
      return okay(201, liveRequest(copy(r)));
    },

    /* LATER: POST /api/requests/<id>/supply/   A farmer offers to supply all or PART of a request. */
    async offerToSupply(requestId, data) {
      await wait(400);
      const me = store("murimi-demo-session");
      if (!me) return fail(401, "Please log in to offer.");
      if (me.role === "buyer") return fail(403, "Supplying needs a farmer account.");
      const r = allRequests().find((x) => x.id === requestId);
      if (!r || r.status !== "open") return fail(404, "This request is closed.");
      if (r.buyer.id === me.id) return fail(400, "This is your own request.");
      const errors = {};
      const qty = Number(data.quantity), price = Number(data.price);
      if (!Number.isInteger(qty) || qty < 1) errors.quantity = "Enter a whole number, 1 or more.";
      else if (qty > r.still_needed) errors.quantity = `They only need ${r.still_needed} more.`;
      if (!(price > 0)) errors.price = "Enter your price per unit.";
      const d = daysUntil(data.ready_on || "");
      if (!data.ready_on || isNaN(d) || d < 0) errors.ready_on = "Choose when you can supply it.";
      else if (d > M.READY_WINDOW_DAYS) errors.ready_on = `Offer to supply up to ${M.READY_WINDOW_DAYS} days ahead.`;
      if (Object.keys(errors).length) return fail(400, "Please check the form.", errors);
      const buyerUser = r.buyer.id === 1 ? { phone: "+263771234567" } : null;
      const o = {
        id: Date.now(), request_id: r.id, listing_id: null, proposed_by: "farmer", crop: r.crop,
        variety: String(data.variety || "").trim().slice(0, 60) || "As requested", unit: r.unit, price_usd: price,
        farmer: { id: me.id, name: me.name, phone: me.phone },
        buyer: { id: r.buyer.id, name: r.buyer.name, phone: buyerUser ? buyerUser.phone : "+26371255" + String(r.buyer.id).padStart(4, "0") },
        quantity: qty, delivery: r.delivery === "either" ? "delivery" : r.delivery, message: String(data.message || "").trim().slice(0, 300),
        ready_on: data.ready_on, status: "pending", created_at: new Date().toISOString().slice(0, 19), ratings: {},
      };
      saveOrders(loadOrders().concat([o]));
      return okay(201, viewFor(o, me));
    },

    /* LATER: GET /api/me/requests/ */
    async myRequests() {
      await wait(200);
      const me = store("murimi-demo-session");
      if (!me) return fail(401, "Please log in.");
      const orders = loadOrders();
      const rows = allRequests().filter((r) => r.buyer.id === me.id).sort((a, b) => b.created_at.localeCompare(a.created_at));
      rows.forEach((r) => (r.offers_waiting = orders.filter((o) => o.request_id === r.id && o.status === "pending").length));
      return okay(200, { results: rows });
    },

    /* LATER: POST /api/requests/<id>/close/  (only the buyer who posted it) */
    async closeRequest(id) {
      await wait(250);
      const me = store("murimi-demo-session");
      const r = allRequests().find((x) => x.id === id);
      if (!me || !r || r.buyer.id !== me.id) return fail(403, "Only the buyer who posted this can close it.");
      store("murimi-demo-reqclosed", closedReqs().concat([id]));
      return okay(200, { id, status: "closed" });
    },

    /* LATER: POST /api/listings/<id>/offers/  with header X-CSRFToken: csrfToken()
       The SERVER will check everything again (never trust the browser). */
    async sendOffer(listingId, data) {
      await wait(400);
      const me = store("murimi-demo-session");
      if (!me) return fail(401, "Please log in to send an offer.");
      const got = await call("GET", `/api/listings/${listingId}/`);       // the real listing
      const l = got.ok ? got.body : null;
      if (!l || l.sold_out || l.quantity_left < 1) return fail(404, "This listing is no longer available.");
      if (l.farmer.id === me.id) return fail(400, "This is your own listing.");
      const q = Number(data.quantity);
      if (!Number.isInteger(q) || q < 1 || q > l.quantity_left) {
        return fail(400, "Please check the form.", { quantity: `Choose between 1 and ${l.quantity_left}.` });
      }
      const order = {
        id: Date.now(), listing_id: l.id, crop: l.crop, variety: l.variety, unit: l.unit, price_usd: l.price_usd,
        farmer: { id: l.farmer.id || 1000 + l.id, name: l.farmer.name, phone: l.farmer.phone || "+26377" + String(1000000 + l.id).slice(-7) },
        buyer: { id: me.id, name: me.name, phone: me.phone },
        quantity: q, delivery: data.delivery, message: String(data.message || "").slice(0, 300),
        status: "pending", created_at: new Date().toISOString().slice(0, 19), ratings: {},
      };
      saveOrders(loadOrders().concat([order]));
      return okay(201, viewFor(order, me));
    },

    /* REAL: GET /api/listings/<id>/  (photos, description, farmer profile, similar listings) */
    getListing(id) { return call("GET", `/api/listings/${id}/`); },

    // ---------- My account ----------
    /* LATER: GET /api/me/offers/  (offers on MY listings, newest first) */
    async offersReceived() {
      await wait(200);
      const me = store("murimi-demo-session");
      if (!me) return fail(401, "Please log in.");
      const rows = loadOrders().filter((o) => o.farmer.id === me.id)      // WHERE farmer_id = me
        .sort((a, b) => b.created_at.localeCompare(a.created_at));       // ORDER BY created_at DESC
      return okay(200, { results: rows.map((o) => viewFor(o, me)) });
    },

    /* LATER: GET /api/me/orders/  (what I asked to buy) */
    async myOrders() {
      await wait(200);
      const me = store("murimi-demo-session");
      if (!me) return fail(401, "Please log in.");
      const rows = loadOrders().filter((o) => o.buyer.id === me.id)
        .sort((a, b) => b.created_at.localeCompare(a.created_at));
      return okay(200, { results: rows.map((o) => viewFor(o, me)) });
    },

    /* REAL: GET /api/me/listings/  (all MY listings, drafts and sold out too) */
    async myListings() {
      const res = await call("GET", "/api/me/listings/");
      if (!res.ok) return res;
      const orders = loadOrders();
      res.body.results.forEach((l) => {
        l.pending_offers = orders.filter((o) => o.listing_id === l.id && o.status === "pending").length;
      });
      return res;
    },

    /* LATER: POST /api/orders/<id>/<action>/   action = accept | decline | cancel | complete
       On the server, "accept" runs inside transaction.atomic() with select_for_update(),
       so two farmers' clicks (or two buyers) can never sell the same last crate twice. */
    async orderAction(orderId, action) {
      await wait(350);
      const me = store("murimi-demo-session");
      if (!me) return fail(401, "Please log in.");
      const rows = loadOrders();
      const o = rows.find((x) => x.id === orderId);
      if (!o || (o.farmer.id !== me.id && o.buyer.id !== me.id)) return fail(404, "Order not found.");
      const t = TRANSITIONS[action];
      if (!t) return fail(400, "Unknown action.");
      if (!allowed(t, o, me)) {
        return fail(403, t.who === "receiver" ? "Only the person who received this offer can answer it." : "Only the person who sent this offer can cancel it.");
      }
      if (!t.from.includes(o.status)) return fail(409, `This order is already ${o.status}.`);

      if (action === "accept" && o.request_id) {
        // A supply offer: check the request still needs this much, then count it as filled.
        const r = allRequests().find((x) => x.id === o.request_id);
        if (!r || r.status === "closed") return fail(409, "This request is closed.");
        if (o.quantity > r.still_needed) {
          return fail(409, r.still_needed > 0
            ? `Only ${r.still_needed} still needed, but this offer is for ${o.quantity}. Decline it, or ask the farmer for a smaller amount.`
            : "This request is already fully supplied.");
        }
        const ex = reqExtra(); const cur = ex[r.id] || { filled: 0, suppliers: 0 };
        ex[r.id] = { filled: cur.filled + o.quantity, suppliers: cur.suppliers + 1 };
        store("murimi-demo-reqfill", ex);
        o.accepted_at = new Date().toISOString().slice(0, 10);
      } else if (action === "accept") {
        // Only if there is enough left. (Server, next job: transaction.atomic + SELECT ... FOR UPDATE)
        const got = await call("GET", `/api/listings/${o.listing_id}/`);
        const left = got.ok ? got.body.quantity_left - (acceptedHere()[o.listing_id] || 0) : 0;
        if (left < o.quantity) {
          return fail(409, left > 0
            ? `Only ${left} left, but this offer asks for ${o.quantity}. Decline it, or ask the buyer to send a smaller offer.`
            : "This listing is sold out.");
        }
        store("murimi-demo-qty", Object.assign(acceptedHere(), { [o.listing_id]: (acceptedHere()[o.listing_id] || 0) + o.quantity }));
        o.accepted_at = new Date().toISOString().slice(0, 10);
      }
      if (action === "complete") o.completed_at = new Date().toISOString().slice(0, 10);
      o.status = t.to;
      saveOrders(rows);
      return okay(200, viewFor(o, me));
    },

    /* LATER: POST /api/orders/<id>/rating/  { stars: 1-5, comment }  once per side, after completed */
    async rateOrder(orderId, stars, comment) {
      await wait(350);
      const me = store("murimi-demo-session");
      if (!me) return fail(401, "Please log in.");
      const rows = loadOrders();
      const o = rows.find((x) => x.id === orderId);
      if (!o || (o.farmer.id !== me.id && o.buyer.id !== me.id)) return fail(404, "Order not found.");
      if (o.status !== "completed") return fail(409, "You can rate once the order is completed.");
      const key = o.farmer.id === me.id ? "by_farmer" : "by_buyer";
      if (o.ratings[key]) return fail(409, "You've already rated this order.");
      const n = Number(stars);
      if (!Number.isInteger(n) || n < 1 || n > 5) return fail(400, "Please check the form.", { stars: "Choose 1 to 5 stars." });
      o.ratings[key] = { stars: n, comment: String(comment || "").trim().slice(0, 300) };
      saveOrders(rows);
      return okay(201, viewFor(o, me));
    },

    /* REAL: POST /api/listings/<id>/sold-out/  (owner only) */
    markSoldOut(listingId) { return call("POST", `/api/listings/${listingId}/sold-out/`); },

    /* Demo only: put the sample offers and listings back to how they started. */
    resetDemo() { ["murimi-demo-orders", "murimi-demo-qty", "murimi-demo-requests", "murimi-demo-reqfill", "murimi-demo-reqclosed"].forEach((k) => store(k, null)); },

    /* REAL: POST /api/listings/  (a multipart form: the fields + up to 3 photo FILES).
       The page shrinks photos to small JPEGs first (data: addresses); here they become
       files again. The server checks everything again (never trust the browser). */
    async createListing(data) {
      const form = new FormData();
      ["crop", "variety", "quantity", "unit", "price", "price_zig", "available", "harvested_on", "province",
        "district", "delivery", "description", "status"].forEach((k) => { if (data[k] != null && data[k] !== "") form.append(k, data[k]); });
      if (data.sell_today) form.append("sell_today", "1");
      (data.photos || []).forEach((dataUrl, i) => form.append("photos", dataUrlToBlob(dataUrl), `photo-${i + 1}.jpg`));
      try {
        const res = await fetch("/api/listings/", { method: "POST", body: form, credentials: "same-origin",
          headers: { "X-CSRFToken": csrfToken(), Accept: "application/json" } });
        return { ok: res.ok, status: res.status, body: await res.json() };
      } catch (e) {
        return { ok: false, status: 0, body: { error: "Can't reach the server. Check your connection and try again.", errors: {} } };
      }
    },

    fairPrice,
    daysUntil,
    csrfToken,
  };
})();
