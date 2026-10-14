/*
 * mock.js - SAMPLE data, standing in for the database until we build the API.
 *
 * Every object here has the same shape the real JSON from /api/ will have,
 * so when the server is ready we delete this file and nothing else changes
 * except api.js.
 *
 * CROPS and PROVINCES copy the Hub's accounts/choices.py exactly.
 * POULTRY is new for the marketplace. When we link with the Hub, the Hub's
 * choices.py gets the same POULTRY list, so both sides still match.
 */
window.MURIMI_MOCK = (function () {
  const CROPS = ["Maize", "Tobacco", "Tomatoes", "Potatoes", "Sugar beans", "Citrus", "Cotton", "Avocados", "Other"];
  const POULTRY = ["Broilers", "Eggs"];

  // A listing may go up at most this many days before it is ready to sell.
  const READY_WINDOW_DAYS = 14;

  // Dates counted from today, so the "coming soon" samples always look right.
  const day = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };

  const PROVINCES = [
    "Bulawayo", "Harare", "Manicaland", "Mashonaland Central", "Mashonaland East",
    "Mashonaland West", "Masvingo", "Matabeleland North", "Matabeleland South", "Midlands",
  ];

  const UNITS = [
    { value: "kg", label: "kg" },
    { value: "tonne", label: "tonne" },
    { value: "crate", label: "crate" },
    { value: "pocket_15kg", label: "15 kg pocket" },
    { value: "bag_50kg", label: "50 kg bag" },
    { value: "bird", label: "bird" },
    { value: "tray_30", label: "tray of 30 eggs" },
  ];

  // Which units make sense for which product (the server will check this too).
  const PRODUCT_UNITS = {
    Broilers: ["bird", "kg"],
    Eggs: ["tray_30"],
    _crops: ["kg", "tonne", "crate", "pocket_15kg", "bag_50kg"],
  };

  // Today's market prices (like the Hub's PriceReport table). Sample values.
  // Today's market prices (like the Hub's PriceReport table). Sample values.
  // The GMB maize price is deliberately 12 days old, to show how the meter treats old prices.
  const MARKET_PRICES = [
    { crop: "Tomatoes", unit: "crate", usd: 7.0, market: "Mbare Musika", date: day(-1) },
    { crop: "Potatoes", unit: "pocket_15kg", usd: 9.0, market: "Mbare Musika", date: day(-1) },
    { crop: "Maize", unit: "bag_50kg", usd: 16.0, market: "Mbare Musika", date: day(-2) },
    { crop: "Maize", unit: "tonne", usd: 310.0, market: "GMB floor", date: day(-12) },
    { crop: "Sugar beans", unit: "kg", usd: 2.1, market: "Mbare Musika", date: day(-1) },
    { crop: "Citrus", unit: "crate", usd: 6.0, market: "Mbare Musika", date: day(-2) },
    { crop: "Avocados", unit: "crate", usd: 12.0, market: "Mbare Musika", date: day(-3) },
    { crop: "Broilers", unit: "bird", usd: 5.5, market: "Mbare Musika", date: day(-1) },
    { crop: "Eggs", unit: "tray_30", usd: 4.5, market: "Mbare Musika", date: day(-1) },
  ];

  // A market price older than this many days is "old": the meter says so instead of comparing.
  const PRICE_FRESH_DAYS = 7;
  // "Must sell today" listings come off the market at this hour (24-hour clock), Zimbabwe time.
  const SELL_TODAY_ENDS_HOUR = 18;

  const LISTINGS = [
    { id: 101, crop: "Tomatoes", variety: "Roma, grade A", quantity: 120, quantity_left: 84, unit: "crate", price_usd: 6.5,
      province: "Mashonaland East", district: "Murehwa", available_from: "2026-10-12", harvested_on: "2026-10-11",
      delivery: "both", sell_today: false, created_at: "2026-10-12T07:40:00",
      farmer: { id: 1, name: "Tendai M.", verified: true, rating: 4.8, completed_orders: 31 } },
    { id: 102, crop: "Potatoes", variety: "BP1", quantity: 200, quantity_left: 200, unit: "pocket_15kg", price_usd: 9.5,
      province: "Manicaland", district: "Nyanga", available_from: "2026-10-14", harvested_on: "2026-10-10",
      delivery: "pickup", sell_today: false, created_at: "2026-10-12T15:10:00",
      farmer: { name: "Rudo C.", verified: true, rating: 4.6, completed_orders: 18 } },
    { id: 103, crop: "Tomatoes", variety: "Star 9003", quantity: 40, quantity_left: 40, unit: "crate", price_usd: 4.5,
      province: "Harare", district: "Domboshava", available_from: "2026-10-13", harvested_on: "2026-10-12",
      delivery: "delivery", sell_today: true, created_at: day(0) + "T06:05:00",
      farmer: { name: "Blessing N.", verified: false, rating: 4.2, completed_orders: 5 } },
    { id: 104, crop: "Maize", variety: "White, dry", quantity: 30, quantity_left: 22, unit: "tonne", price_usd: 295,
      province: "Mashonaland West", district: "Chinhoyi", available_from: "2026-10-01", harvested_on: "2026-07-20",
      delivery: "pickup", sell_today: false, created_at: "2026-10-09T10:00:00",
      farmer: { name: "Chipo Farms", verified: true, rating: 4.9, completed_orders: 52 } },
    { id: 105, crop: "Sugar beans", variety: "Nua 45", quantity: 800, quantity_left: 650, unit: "kg", price_usd: 2.3,
      province: "Midlands", district: "Gokwe", available_from: "2026-10-05", harvested_on: "2026-09-28",
      delivery: "both", sell_today: false, created_at: "2026-10-10T09:20:00",
      farmer: { name: "Farai D.", verified: true, rating: 4.5, completed_orders: 12 } },
    { id: 106, crop: "Avocados", variety: "Hass", quantity: 60, quantity_left: 60, unit: "crate", price_usd: 11.0,
      province: "Manicaland", district: "Chipinge", available_from: "2026-10-12", harvested_on: "2026-10-11",
      delivery: "delivery", sell_today: false, created_at: "2026-10-12T11:45:00",
      farmer: { name: "Mai Ropafadzo", verified: true, rating: 5.0, completed_orders: 9 } },
    { id: 107, crop: "Citrus", variety: "Valencia oranges", quantity: 90, quantity_left: 35, unit: "crate", price_usd: 6.8,
      province: "Masvingo", district: "Chiredzi", available_from: "2026-10-07", harvested_on: "2026-10-06",
      delivery: "both", sell_today: false, created_at: "2026-10-08T08:30:00",
      farmer: { name: "Tinashe G.", verified: false, rating: 4.0, completed_orders: 3 } },
    { id: 108, crop: "Maize", variety: "Green mealies", quantity: 50, quantity_left: 50, unit: "bag_50kg", price_usd: 14.0,
      province: "Mashonaland Central", district: "Bindura", available_from: "2026-10-13", harvested_on: "2026-10-12",
      delivery: "pickup", sell_today: true, created_at: day(0) + "T05:50:00",
      farmer: { name: "Kuda S.", verified: true, rating: 4.7, completed_orders: 22 } },
    { id: 109, crop: "Potatoes", variety: "Mondial", quantity: 80, quantity_left: 80, unit: "pocket_15kg", price_usd: 8.2,
      province: "Matabeleland South", district: "Gwanda", available_from: "2026-10-11", harvested_on: "2026-10-09",
      delivery: "both", sell_today: false, created_at: "2026-10-11T13:00:00",
      farmer: { name: "Sipho Ndlovu", verified: true, rating: 4.4, completed_orders: 14 } },
    { id: 110, crop: "Tomatoes", variety: "Roma", quantity: 25, quantity_left: 25, unit: "crate", price_usd: 7.5,
      province: "Bulawayo", district: "Umguza", available_from: "2026-10-12", harvested_on: "2026-10-11",
      delivery: "delivery", sell_today: false, created_at: "2026-10-12T16:20:00",
      farmer: { name: "Nomsa K.", verified: false, rating: 0, completed_orders: 0 } },
    { id: 111, crop: "Sugar beans", variety: "Speckled", quantity: 300, quantity_left: 120, unit: "kg", price_usd: 1.9,
      province: "Matabeleland North", district: "Lupane", available_from: "2026-10-03", harvested_on: "2026-09-25",
      delivery: "pickup", sell_today: false, created_at: "2026-10-04T10:10:00",
      farmer: { name: "Thandeka M.", verified: true, rating: 4.3, completed_orders: 7 } },
    { id: 112, crop: "Citrus", variety: "Lemons", quantity: 40, quantity_left: 40, unit: "crate", price_usd: 5.0,
      province: "Mashonaland East", district: "Mutoko", available_from: "2026-10-13", harvested_on: "2026-10-12",
      delivery: "both", sell_today: false, created_at: "2026-10-13T08:15:00",
      farmer: { name: "Garikai T.", verified: true, rating: 4.6, completed_orders: 16 } },
    { id: 113, crop: "Tobacco", variety: "Flue-cured, leaf grade", quantity: 2400, quantity_left: 2400, unit: "kg", price_usd: 3.1,
      province: "Mashonaland West", district: "Karoi", available_from: "2026-10-10", harvested_on: "2026-09-20",
      delivery: "pickup", sell_today: false, created_at: "2026-10-10T12:00:00",
      farmer: { name: "Tatenda R.", verified: true, rating: 4.5, completed_orders: 11 } },
    { id: 114, crop: "Cotton", variety: "Seed cotton, grade A", quantity: 1500, quantity_left: 900, unit: "kg", price_usd: 0.45,
      province: "Midlands", district: "Gokwe", available_from: "2026-10-02", harvested_on: "2026-09-15",
      delivery: "pickup", sell_today: false, created_at: "2026-10-06T09:00:00",
      farmer: { name: "Memory Z.", verified: false, rating: 4.1, completed_orders: 4 } },

    // ---- Poultry ----
    { id: 115, crop: "Broilers", variety: "Live, about 2 kg each", quantity: 300, quantity_left: 240, unit: "bird", price_usd: 5.0,
      province: "Harare", district: "Ruwa", available_from: day(-2), harvested_on: day(-2),
      delivery: "both", sell_today: false, created_at: day(-2) + "T08:00:00",
      farmer: { id: 15, name: "Nyasha P.", phone: "+263772000115", verified: true, rating: 4.7, completed_orders: 26 } },
    { id: 116, crop: "Eggs", variety: "Large, brown", quantity: 120, quantity_left: 95, unit: "tray_30", price_usd: 4.2,
      province: "Mashonaland East", district: "Marondera", available_from: day(-1), harvested_on: day(-1),
      delivery: "delivery", sell_today: false, created_at: day(-1) + "T07:30:00",
      farmer: { id: 16, name: "Mai Tafadzwa", phone: "+263772000116", verified: true, rating: 4.9, completed_orders: 40 } },
    { id: 117, crop: "Eggs", variety: "Mixed sizes", quantity: 40, quantity_left: 40, unit: "tray_30", price_usd: 3.8,
      province: "Bulawayo", district: "Cowdray Park", available_from: day(0), harvested_on: day(0),
      delivery: "pickup", sell_today: false, created_at: day(0) + "T06:45:00",
      farmer: { name: "Sibusiso M.", verified: false, rating: 4.3, completed_orders: 6 } },

    // ---- Coming soon: not ready yet, at most 2 weeks away ----
    { id: 118, crop: "Broilers", variety: "Live, will be 6 weeks old", quantity: 500, quantity_left: 500, unit: "bird", price_usd: 5.2,
      province: "Mashonaland West", district: "Norton", available_from: day(6), harvested_on: null,
      delivery: "both", sell_today: false, created_at: day(0) + "T09:10:00",
      farmer: { name: "Chiedza F.", verified: true, rating: 4.8, completed_orders: 19 } },
    { id: 119, crop: "Tomatoes", variety: "Roma, still on the vine", quantity: 200, quantity_left: 200, unit: "crate", price_usd: 6.0,
      province: "Manicaland", district: "Mutasa", available_from: day(9), harvested_on: null,
      delivery: "pickup", sell_today: false, created_at: day(-1) + "T14:00:00",
      farmer: { name: "Tonderai K.", verified: true, rating: 4.6, completed_orders: 15 } },
    { id: 120, crop: "Maize", variety: "Green mealies", quantity: 80, quantity_left: 80, unit: "bag_50kg", price_usd: 13.0,
      province: "Mashonaland East", district: "Goromonzi", available_from: day(13), harvested_on: null,
      delivery: "both", sell_today: false, created_at: day(0) + "T10:30:00",
      farmer: { name: "Rutendo B.", verified: false, rating: 4.2, completed_orders: 3 } },
  ];

  /* Buyer requests ("I need ..."). filled = how much farmers have already agreed to supply.
     Farmers can each supply PART of a request: that is how small farms fill big orders. */
  const REQUESTS = [
    { id: 501, buyer: { id: 51, name: "FreshMart", kind: "Supermarket" }, crop: "Tomatoes", quantity: 300, unit: "crate",
      filled: 180, province: "Harare", district: "Avondale", needed_by: day(3), repeat: "weekly", suppliers: 3,
      max_price_usd: 6.8, delivery: "delivery", note: "Firm, grade A only. Delivery to our Avondale store before 8 am.", status: "open", created_at: day(-4) + "T08:00:00" },
    { id: 502, buyer: { id: 54, name: "Mzilikazi High School", kind: "School" }, crop: "Sugar beans", quantity: 1000, unit: "kg",
      filled: 250, province: "Bulawayo", district: "Mzilikazi", needed_by: day(10), repeat: "once", suppliers: 1,
      max_price_usd: null, delivery: "either", note: "For the boarding kitchen. Clean, dry beans.", status: "open", created_at: day(-3) + "T10:00:00" },
    { id: 503, buyer: { id: 52, name: "Kuchikwata Restaurant", kind: "Restaurant" }, crop: "Potatoes", quantity: 40, unit: "pocket_15kg",
      filled: 0, province: "Harare", district: "Borrowdale", needed_by: day(2), repeat: "weekly", suppliers: 0,
      max_price_usd: 9.5, delivery: "delivery", note: "", status: "open", created_at: day(-1) + "T09:00:00" },
    { id: 504, buyer: { id: 57, name: "Masvingo traders group", kind: "Traders" }, crop: "Maize", quantity: 60, unit: "tonne",
      filled: 22, province: "Masvingo", district: "Masvingo town", needed_by: day(19), repeat: "once", suppliers: 2,
      max_price_usd: 300, delivery: "pickup", note: "We collect with our own trucks.", status: "open", created_at: day(-6) + "T12:00:00" },
    // Tendai (the demo account) is also a buyer: maize for his workers' rations.
    { id: 505, buyer: { id: 1, name: "Tendai Moyo", kind: "Buyer" }, crop: "Maize", quantity: 30, unit: "bag_50kg",
      filled: 0, province: "Mashonaland East", district: "Murehwa", needed_by: day(12), repeat: "monthly", suppliers: 0,
      max_price_usd: 15, delivery: "delivery", note: "Dry white maize for farm workers' rations.", status: "open", created_at: day(-1) + "T16:00:00" },
  ];

  const REPEATS = [
    { value: "once", label: "Once" }, { value: "weekly", label: "Every week" },
    { value: "fortnightly", label: "Every 2 weeks" }, { value: "monthly", label: "Every month" },
  ];

  // One sample account to try logging in with (demo only).
  const USERS = [
    { id: 1, name: "Tendai Moyo", phone: "+263771234567", username: "tendai", role: "both",
      password: "murimi2026", phone_verified: true },
  ];
  // In test mode every WhatsApp code is this (the real server prints its code in the server window).
  const DEMO_CODE = "123456";

  // A listing Tendai saved as a draft: only Tendai sees it, in My account.
  const DRAFTS = [
    { id: 121, crop: "Potatoes", variety: "BP1", quantity: 60, quantity_left: 60, unit: "pocket_15kg", price_usd: 9.0,
      province: "Mashonaland East", district: "Murehwa", available_from: day(10), harvested_on: null,
      delivery: "pickup", sell_today: false, created_at: day(0) + "T08:00:00", status: "draft",
      farmer: { id: 1, name: "Tendai M.", verified: true, rating: 4.8, completed_orders: 31 } },
  ];

  /* Offers and orders (one table: an offer becomes an order when the farmer accepts).
     status: pending -> accepted -> completed, or declined / cancelled.
     The phone numbers are only shown to the other side after "accepted". */
  const buyer = (id, name, phone) => ({ id, name, phone });
  const tendaiSells = (id, b, qty, delivery, status, when, extra) => Object.assign({
    id, listing_id: 101, crop: "Tomatoes", variety: "Roma, grade A", unit: "crate", price_usd: 6.5,
    farmer: { id: 1, name: "Tendai Moyo", phone: "+263771234567" }, buyer: b,
    quantity: qty, delivery, message: "", status, created_at: day(when) + "T09:00:00", ratings: {},
  }, extra || {});
  const ORDERS = [
    tendaiSells(9001, buyer(51, "FreshMart, Avondale", "+263712555001"), 20, "delivery", "pending", 0,
      { message: "Can you deliver on Friday morning?" }),
    tendaiSells(9002, buyer(52, "Kuchikwata Restaurant", "+263712555002"), 8, "pickup", "pending", -1),
    tendaiSells(9003, buyer(53, "Mai Chipo (Mbare trader)", "+263712555003"), 70, "pickup", "pending", -1,
      { message: "I can take a big load if the price is right." }),
    tendaiSells(9004, buyer(54, "Mzilikazi High School", "+263712555004"), 16, "delivery", "accepted", -2,
      { accepted_at: day(-2) }),
    tendaiSells(9005, buyer(55, "Farai's Greengrocer", "+263712555005"), 20, "pickup", "completed", -6,
      { accepted_at: day(-6), completed_at: day(-4), ratings: { by_buyer: { stars: 5, comment: "Fresh and well packed." } } }),
    tendaiSells(9006, buyer(56, "J. Banda", "+263712555006"), 2, "delivery", "declined", -3),
    // Tendai as a buyer
    { id: 9101, listing_id: 115, crop: "Broilers", variety: "Live, about 2 kg each", unit: "bird", price_usd: 5.0,
      farmer: { id: 15, name: "Nyasha P.", phone: "+263772000115" }, buyer: buyer(1, "Tendai Moyo", "+263771234567"),
      quantity: 40, delivery: "pickup", message: "For a family function on Saturday.", status: "accepted",
      created_at: day(-1) + "T12:00:00", accepted_at: day(-1), ratings: {} },
    // A farmer offering to supply PART of Tendai's request 505 (Tendai, the buyer, decides)
    { id: 9201, request_id: 505, listing_id: null, proposed_by: "farmer", crop: "Maize", variety: "White, dry", unit: "bag_50kg", price_usd: 14.0,
      farmer: { id: 20, name: "Rutendo B.", phone: "+263772000120" }, buyer: buyer(1, "Tendai Moyo", "+263771234567"),
      quantity: 20, delivery: "delivery", message: "I can bring 20 bags on Saturday. The other 10 maybe next month.",
      ready_on: day(3), status: "pending", created_at: day(0) + "T08:30:00", ratings: {} },
    { id: 9102, listing_id: 116, crop: "Eggs", variety: "Large, brown", unit: "tray_30", price_usd: 4.2,
      farmer: { id: 16, name: "Mai Tafadzwa", phone: "+263772000116" }, buyer: buyer(1, "Tendai Moyo", "+263771234567"),
      quantity: 10, delivery: "delivery", message: "", status: "pending", created_at: day(0) + "T07:50:00", ratings: {} },
  ];

  // What farmers wrote about their listings (by listing id).
  const DESCRIPTIONS = {
    101: "Firm Roma tomatoes, picked yesterday morning and packed in clean crates of about 30 kg. Good for supermarkets and restaurants: even size, no cracks. I can deliver within 40 km of Murehwa, or you can collect from the farm on the Mutoko road.",
    102: "BP1 potatoes from Nyanga, washed and graded. Packed in 15 kg pockets. Collection from the farm only.",
    103: "Ripe tomatoes that must go today. Good for sauce, relish and street vendors. Lower price for a quick sale.",
    104: "Dry white maize, moisture checked. Stored in a clean shed. Minimum 1 tonne per buyer.",
    115: "Healthy broilers, about 2 kg live weight, raised on commercial feed. Vaccinated. Collect in your own crates or we deliver in Harare east.",
    116: "Large brown eggs collected every morning. Delivered in trays of 30 to shops and restaurants in Marondera and Harare.",
    118: "Our next batch reaches 6 weeks on the ready date. Reserve now for weddings, funerals and functions.",
    119: "Roma tomatoes still on the vine, first picking expected on the ready date. Reserve now and I will confirm two days before.",
  };

  // Sample photos a farmer uploaded (only listing 101 has them in the demo).
  const PHOTOS = { 101: ["img/sample/listing-101-1.webp", "img/sample/listing-101-2.webp", "img/sample/listing-101-3.webp"] };

  // Farmer profiles, joined to listings by the farmer's name in the demo (by id on the server).
  const FARMERS = {
    "Tendai M.": { member_since: "2025-03", verified_on: "2025-04-12",
      reviews: [
        { by: "Farai's Greengrocer", stars: 5, comment: "Fresh and well packed.", date: day(-4) },
        { by: "Hotel Monomotapa kitchen", stars: 5, comment: "Delivered on time, every crate full.", date: day(-20) },
        { by: "Mai Rufaro", stars: 4, comment: "Good tomatoes. Came a little late.", date: day(-35) },
      ] },
    "Nyasha P.": { member_since: "2024-11", verified_on: "2024-12-02",
      reviews: [{ by: "Mbare trader", stars: 5, comment: "Birds were healthy and heavy.", date: day(-9) }] },
    "Mai Tafadzwa": { member_since: "2024-06", verified_on: "2024-07-20",
      reviews: [{ by: "Pick n Pay Marondera", stars: 5, comment: "No broken eggs in 40 trays.", date: day(-6) }] },
  };

  return { PRICE_FRESH_DAYS, SELL_TODAY_ENDS_HOUR, REPEATS, DESCRIPTIONS, PHOTOS, FARMERS, DRAFTS, ORDERS, USERS, DEMO_CODE, CROPS, POULTRY, PROVINCES, UNITS, PRODUCT_UNITS, READY_WINDOW_DAYS, MARKET_PRICES, LISTINGS, REQUESTS };
})();
