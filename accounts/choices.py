"""
Shared lists. CROPS and PROVINCES must stay identical to Murimi Intelligent Hub's
accounts/choices.py, so the two projects can be joined later.
POULTRY is new for the marketplace; add the same list to the Hub when we link them.
"""

PROVINCES = [
    "Bulawayo", "Harare", "Manicaland", "Mashonaland Central", "Mashonaland East",
    "Mashonaland West", "Masvingo", "Matabeleland North", "Matabeleland South", "Midlands",
]

CROPS = ["Maize", "Tobacco", "Tomatoes", "Potatoes", "Sugar beans", "Citrus", "Cotton", "Avocados", "Other"]

POULTRY = ["Broilers", "Eggs"]

PRODUCTS = CROPS + POULTRY

# Django "choices" format: (value stored in the database, label shown to people)
PROVINCE_CHOICES = [(p, p) for p in PROVINCES]
PRODUCT_CHOICES = [(p, p) for p in PRODUCTS]

# Marketplace roles. (The Hub has farmer / landowner / investor / driver; when we link
# the projects, a Hub farmer becomes "farmer" here and investors/drivers become "buyer".)
ROLE_FARMER = "farmer"
ROLE_BUYER = "buyer"
ROLE_BOTH = "both"
ROLE_CHOICES = [
    (ROLE_FARMER, "Farmer (sells)"),
    (ROLE_BUYER, "Buyer"),
    (ROLE_BOTH, "Sells and buys"),
]

# Units a listing (or request) can be priced in, and which products may use which.
UNIT_CHOICES = [
    ("kg", "kg"),
    ("tonne", "tonne"),
    ("crate", "crate"),
    ("pocket_15kg", "15 kg pocket"),
    ("bag_50kg", "50 kg bag"),
    ("bird", "bird"),
    ("tray_30", "tray of 30 eggs"),
]
CROP_UNITS = ["kg", "tonne", "crate", "pocket_15kg", "bag_50kg"]
PRODUCT_UNITS = {"Broilers": ["bird", "kg"], "Eggs": ["tray_30"]}


def units_for(product):
    """The units that make sense for a product: birds for broilers, trays for eggs."""
    return PRODUCT_UNITS.get(product, CROP_UNITS)


# Buyers that are businesses (their full name is shown, e.g. "FreshMart").
BUSINESS_CHOICES = [("Supermarket", "Supermarket"), ("Restaurant", "Restaurant"), ("Hotel", "Hotel"),
                    ("School", "School"), ("Traders", "Traders"), ("Shop", "Shop"), ("Other", "Other business")]

DELIVERY_CHOICES = [("pickup", "Buyer collects"), ("delivery", "Farmer delivers"), ("both", "Collect or delivery")]

# A listing may go up at most this many days before it's ready ("coming soon").
READY_WINDOW_DAYS = 14
# A market price older than this is "out of date": the fair-price meter won't compare with it.
PRICE_FRESH_DAYS = 7
# "Must sell today" listings come off the market at this hour (Zimbabwe time).
SELL_TODAY_ENDS_HOUR = 18
