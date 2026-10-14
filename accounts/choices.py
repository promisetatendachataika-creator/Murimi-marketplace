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
