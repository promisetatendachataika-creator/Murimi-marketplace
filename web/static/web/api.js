/*
 * api.js - the "waiter" between the page and the kitchen (the server).
 *
 * The pages never touch data directly. They ask MarketAPI, e.g.
 *     MarketAPI.listListings({ crop: "Tomatoes", sort: "price_asc" })
 * and get back JSON from Django (/api/...). Every function here is a REAL server call;
 * the comment above each one shows its address. The server checks everything again
 * (never trust the browser).
 */
window.MarketAPI = (function () {
  /* Add ?demo=offline (or ?demo=slow) to the page address to practise bad connections. */
  const DEMO = new URLSearchParams(location.search).get("demo");
  const wait = (ms = 250) => new Promise((resolve, reject) => setTimeout(() =>
    DEMO === "offline" ? reject(new TypeError("Failed to fetch")) : resolve(), DEMO === "slow" ? ms * 10 : ms));

  /* For later: Django's CSRF token, copied from the cookie into a header. */
  function csrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  /* Latest market price per product and unit, filled in by meta() from the server (prices app).
     Used by the Sell and Request forms; listings arrive with their own "market" comparison. */
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

  /* Whole days from today until a date ("2026-10-23" -> 9). 0 or less = ready now. */
  function daysUntil(iso) {
    const today = new Date(); today.setHours(12, 0, 0, 0);
    return Math.round((new Date(iso + "T12:00:00") - today) / 86400000);
  }

  // ================= Accounts (log in, register, codes) =================
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

  // A small note kept in this browser (who was last logged in). Never trusted by the server.
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
  // Remember who is logged in, so a page can still say hello when the connection drops.
  const remember = (user) => store("murimi-demo-session", user || null);

  /* Send the Sell form (creating or editing). A multipart form, because photos are FILES.
     The page shrinks photos to small JPEGs first (data: addresses); here they become files
     again. The server checks everything again (never trust the browser). */
  async function sendListing(url, data) {
    const form = new FormData();
    ["crop", "other_product", "variety", "quantity", "unit", "price", "price_zig", "available", "harvested_on",
      "province", "district", "delivery", "description", "status"].forEach((k) => { if (data[k] != null && data[k] !== "") form.append(k, data[k]); });
    if (data.sell_today) form.append("sell_today", "1");
    (data.photos || []).forEach((dataUrl, i) => form.append("photos", dataUrlToBlob(dataUrl), `photo-${i + 1}.jpg`));
    (data.remove_photos || []).forEach((id) => form.append("remove_photos", id));
    try {
      const res = await fetch(url, { method: "POST", body: form, credentials: "same-origin",
        headers: { "X-CSRFToken": csrfToken(), Accept: "application/json" } });
      return { ok: res.ok, status: res.status, body: await res.json() };
    } catch (e) {
      return { ok: false, status: 0, body: { error: "Can't reach the server. Check your connection and try again.", errors: {} } };
    }
  }

  // "data:image/jpeg;base64,..." -> a file the form can send
  function dataUrlToBlob(dataUrl) {
    const [head, b64] = dataUrl.split(",");
    const bytes = atob(b64);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    return new Blob([arr], { type: head.slice(5, head.indexOf(";")) });
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

    // ---------- Buyer requests: REAL (buyer_requests/api.py) ----------
    /* GET /api/requests/   (open requests whose date hasn't passed, soonest first) */
    async listRequests() {
      if (DEMO === "offline") throw new TypeError("Failed to fetch");
      const res = await call("GET", "/api/requests/");
      if (!res.ok) throw new Error(res.body.error);
      return res.body;
    },

    /* POST /api/requests/   A buyer posts what they need. */
    createRequest(data) { return call("POST", "/api/requests/", data); },

    /* POST /api/requests/<id>/supply/   A farmer offers to supply all or PART of a request. */
    offerToSupply(requestId, data) { return call("POST", `/api/requests/${requestId}/supply/`, data); },

    /* GET /api/me/requests/  (with offers_waiting on each) */
    myRequests() { return call("GET", "/api/me/requests/"); },

    /* POST /api/listings/<id>/report/  { reason, details }  (needs log-in; staff see it in the back office) */
    reportListing(listingId, data) { return call("POST", `/api/listings/${listingId}/report/`, data); },

    /* POST /api/requests/<id>/close/  (only the buyer who posted it) */
    closeRequest(id) { return call("POST", `/api/requests/${id}/close/`); },

    // ---------- Offers and orders: REAL (orders/api.py) ----------
    /* POST /api/listings/<id>/offers/  { quantity, delivery, message }
       The price comes from the listing on the server, never from the browser. */
    sendOffer(listingId, data) { return call("POST", `/api/listings/${listingId}/offers/`, data); },

    /* REAL: GET /api/listings/<id>/  (photos, description, farmer profile and reviews, similar listings) */
    getListing(id) { return call("GET", `/api/listings/${id}/`); },

    /* GET /api/me/offers/  (I'm the farmer: offers on my listings, and my supply offers) */
    offersReceived() { return call("GET", "/api/me/offers/"); },

    /* GET /api/me/orders/  (I'm the buyer: what I asked to buy, and supply offers to my requests) */
    myOrders() { return call("GET", "/api/me/orders/"); },

    /* GET /api/me/listings/  (all MY listings, drafts and sold out too, with pending_offers) */
    myListings() { return call("GET", "/api/me/listings/"); },

    /* POST /api/orders/<id>/<action>/   action = accept | decline | cancel | complete
       On the server, "accept" runs inside transaction.atomic() with select_for_update(),
       so two clicks can never sell the same last crate twice. */
    orderAction(orderId, action) { return call("POST", `/api/orders/${orderId}/${action}/`); },

    /* POST /api/orders/<id>/rating/  { stars: 1-5, comment }  once per side, after completed */
    rateOrder(orderId, stars, comment) { return call("POST", `/api/orders/${orderId}/rating/`, { stars: Number(stars), comment }); },

    /* REAL: POST /api/listings/<id>/publish/  (owner only: a draft goes on the market) */
    publishListing(listingId) { return call("POST", `/api/listings/${listingId}/publish/`); },

    /* REAL: POST /api/listings/<id>/sold-out/  (owner only) */
    markSoldOut(listingId) { return call("POST", `/api/listings/${listingId}/sold-out/`); },

    /* REAL: POST /api/listings/  (a multipart form: the fields + up to 3 photo FILES) */
    createListing(data) { return sendListing("/api/listings/", data); },

    /* REAL: POST /api/listings/<id>/edit/  (the same form; `remove_photos` drops photos by id).
       Offers already waiting keep the price they were sent at. */
    updateListing(id, data) { return sendListing(`/api/listings/${id}/edit/`, data); },

    fairPrice,
    daysUntil,
    csrfToken,
  };
})();