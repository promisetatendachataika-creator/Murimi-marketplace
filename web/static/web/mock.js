/*
 * mock.js - SAMPLE offers, orders and buyer requests, until they move to the server (next job).
 * Listings, market prices and accounts are already REAL (the database).
 * CROPS and PROVINCES copy accounts/choices.py.
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

  return { REPEATS, ORDERS, CROPS, POULTRY, PROVINCES, UNITS, PRODUCT_UNITS, READY_WINDOW_DAYS, REQUESTS };
})();
