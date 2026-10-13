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
  const wait = (ms = 250) => new Promise((r) => setTimeout(r, ms));
  const copy = (x) => JSON.parse(JSON.stringify(x));

  /* For later: Django's CSRF token, copied from the cookie into a header. */
  function csrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  /* Today's market price for a crop + unit, or null if we have none.
     LATER: the server adds this to each listing (Lesson 10, fair-price meter). */
  function marketPriceFor(crop, unit) {
    const rows = M.MARKET_PRICES.filter((p) => p.crop === crop && p.unit === unit);
    rows.sort((a, b) => b.date.localeCompare(a.date)); // newest first, like ORDER BY date DESC
    return rows[0] || null;
  }

  /* Compare an asking price with the market: "below", "at" or "above".
     Within 5% either way counts as "at the market". */
  function fairPrice(crop, unit, priceUsd) {
    const m = marketPriceFor(crop, unit);
    if (!m || !(priceUsd > 0)) return null;
    const diff = (priceUsd - m.usd) / m.usd;
    const band = diff < -0.05 ? "below" : diff > 0.05 ? "above" : "at";
    return { usd: m.usd, market: m.market, date: m.date, diff: diff, band: band };
  }

  return {
    meta() {
      return Promise.resolve({ crops: M.CROPS, provinces: M.PROVINCES, units: M.UNITS });
    },

    /* LATER: GET /api/listings/?crop=&province=&max_price=&sell_today=&sort= */
    async listListings(filters = {}) {
      await wait();
      let rows = copy(M.LISTINGS).filter((l) => l.quantity_left > 0);    // WHERE quantity_left > 0
      if (filters.crop) rows = rows.filter((l) => l.crop === filters.crop);             // AND crop = ?
      if (filters.province) rows = rows.filter((l) => l.province === filters.province); // AND province = ?
      if (filters.max_price) rows = rows.filter((l) => l.price_usd <= Number(filters.max_price));
      if (filters.sell_today) rows = rows.filter((l) => l.sell_today);
      rows.forEach((l) => (l.market = fairPrice(l.crop, l.unit, l.price_usd)));

      const sorters = {                                                   // ORDER BY ...
        newest: (a, b) => b.created_at.localeCompare(a.created_at),
        price_asc: (a, b) => a.price_usd - b.price_usd,
        price_desc: (a, b) => b.price_usd - a.price_usd,
        fair: (a, b) => (a.market ? a.market.diff : 9) - (b.market ? b.market.diff : 9),
      };
      rows.sort(sorters[filters.sort] || sorters.newest);
      return { results: rows, count: rows.length };
    },

    /* LATER: GET /api/stats/  (SELECT province, COUNT(*) ... GROUP BY province) */
    async stats() {
      const live = M.LISTINGS.filter((l) => l.quantity_left > 0);
      const byProvince = {};
      live.forEach((l) => (byProvince[l.province] = (byProvince[l.province] || 0) + 1));
      const farmers = new Set(live.filter((l) => l.farmer.verified).map((l) => l.farmer.name));
      return { listings: live.length, verified_farmers: farmers.size, by_province: byProvince };
    },

    /* LATER: GET /api/requests/ */
    async listRequests() {
      await wait(150);
      return { results: copy(M.REQUESTS) };
    },

    /* LATER: POST /api/listings/<id>/offers/  with header X-CSRFToken: csrfToken()
       The SERVER will check everything again (never trust the browser). */
    async sendOffer(listingId, data) {
      await wait(400);
      const l = M.LISTINGS.find((x) => x.id === listingId);
      if (!l) return { ok: false, status: 404, body: { error: "This listing is no longer available." } };
      const q = Number(data.quantity);
      if (!Number.isInteger(q) || q < 1 || q > l.quantity_left) {
        return { ok: false, status: 400, body: { error: "Please check the form.",
          errors: { quantity: `Choose between 1 and ${l.quantity_left}.` } } };
      }
      return { ok: true, status: 201, body: { id: Date.now(), status: "pending", listing: listingId, quantity: q } };
    },

    /* LATER: POST /api/listings/ */
    async createListing(data) {
      await wait(400);
      return { ok: true, status: 201, body: { id: Date.now(), status: "active", ...data } };
    },

    fairPrice,
    csrfToken,
  };
})();
