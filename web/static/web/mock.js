/*
 * mock.js - SAMPLE data, standing in for the database until we build the API.
 *
 * Every object here has the same shape the real JSON from /api/ will have,
 * so when the server is ready we delete this file and nothing else changes
 * except api.js.
 *
 * CROPS and PROVINCES copy the Hub's accounts/choices.py.
 */
window.MURIMI_MOCK = (function () {
  const CROPS = ["Maize", "Tobacco", "Tomatoes", "Potatoes", "Sugar beans", "Citrus", "Cotton", "Avocados", "Other"];

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
  ];

  // Today's market prices (like the Hub's PriceReport table). Sample values.
  const MARKET_PRICES = [
    { crop: "Tomatoes", unit: "crate", usd: 7.0, market: "Mbare Musika", date: "2026-10-12" },
    { crop: "Potatoes", unit: "pocket_15kg", usd: 9.0, market: "Mbare Musika", date: "2026-10-12" },
    { crop: "Maize", unit: "bag_50kg", usd: 16.0, market: "Mbare Musika", date: "2026-10-11" },
    { crop: "Maize", unit: "tonne", usd: 310.0, market: "GMB floor", date: "2026-10-08" },
    { crop: "Sugar beans", unit: "kg", usd: 2.1, market: "Mbare Musika", date: "2026-10-12" },
    { crop: "Citrus", unit: "crate", usd: 6.0, market: "Mbare Musika", date: "2026-10-12" },
    { crop: "Avocados", unit: "crate", usd: 12.0, market: "Mbare Musika", date: "2026-10-10" },
  ];

  const LISTINGS = [
    { id: 101, crop: "Tomatoes", variety: "Roma, grade A", quantity: 120, quantity_left: 84, unit: "crate", price_usd: 6.5,
      province: "Mashonaland East", district: "Murehwa", available_from: "2026-10-12", harvested_on: "2026-10-11",
      delivery: "both", sell_today: false, created_at: "2026-10-12T07:40:00",
      farmer: { name: "Tendai M.", verified: true, rating: 4.8, completed_orders: 31 } },
    { id: 102, crop: "Potatoes", variety: "BP1", quantity: 200, quantity_left: 200, unit: "pocket_15kg", price_usd: 9.5,
      province: "Manicaland", district: "Nyanga", available_from: "2026-10-14", harvested_on: "2026-10-10",
      delivery: "pickup", sell_today: false, created_at: "2026-10-12T15:10:00",
      farmer: { name: "Rudo C.", verified: true, rating: 4.6, completed_orders: 18 } },
    { id: 103, crop: "Tomatoes", variety: "Star 9003", quantity: 40, quantity_left: 40, unit: "crate", price_usd: 4.5,
      province: "Harare", district: "Domboshava", available_from: "2026-10-13", harvested_on: "2026-10-12",
      delivery: "delivery", sell_today: true, created_at: "2026-10-13T06:05:00",
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
      delivery: "pickup", sell_today: true, created_at: "2026-10-13T05:50:00",
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
  ];

  const REQUESTS = [
    { id: 501, buyer: { name: "FreshMart, Avondale", kind: "Supermarket" }, crop: "Tomatoes", quantity: 300, unit: "crate",
      filled: 180, province: "Harare", needed_by: "2026-10-17", repeat: "Every week", suppliers: 3 },
    { id: 502, buyer: { name: "Mzilikazi High School", kind: "School" }, crop: "Sugar beans", quantity: 1000, unit: "kg",
      filled: 250, province: "Bulawayo", needed_by: "2026-10-24", repeat: "Once", suppliers: 1 },
    { id: 503, buyer: { name: "Kuchikwata Restaurant", kind: "Restaurant" }, crop: "Potatoes", quantity: 40, unit: "pocket_15kg",
      filled: 0, province: "Harare", needed_by: "2026-10-15", repeat: "Every week", suppliers: 0 },
    { id: 504, buyer: { name: "Masvingo traders group", kind: "Traders" }, crop: "Maize", quantity: 60, unit: "tonne",
      filled: 22, province: "Masvingo", needed_by: "2026-11-02", repeat: "Once", suppliers: 2 },
  ];

  return { CROPS, PROVINCES, UNITS, MARKET_PRICES, LISTINGS, REQUESTS };
})();
