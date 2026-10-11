from django.conf import settings

# Default packing and kitchen overhead time in minutes
PACKING_MINUTES = getattr(settings, "PACKING_MINUTES", 1)
MAX_PREPARING = getattr(settings, "MAX_PREPARING", 15)
STAFF_CREDIT_MINUTES = getattr(settings, "STAFF_CREDIT_MINUTES", 8)

# Standard station definitions
STANDARD_STATIONS = {
    "dosa_counter": {
        "kind": "live",
        "slots": 1,
        "minutes_per_unit": 2,
    },
    "juice_counter": {
        "kind": "live",
        "slots": 1,
        "minutes_per_unit": 2,
    },
    "biryani_pot": {
        "kind": "bulk",
        "plating_minutes": 2,
        "batch_size": 20,
        "batch_minutes": 25,
    },
    "ice_cream_station": {
        "kind": "quick",
        "minutes": 1,
    },
    "cool_drink_station": {
        "kind": "quick",
        "minutes": 1,
    },
    "quick_items": {
        "kind": "quick",
        "minutes": 1,
    },
    "default_station": {
        "kind": "quick",
        "minutes": 2,
    },
}

# Default item mappings
DEFAULT_ITEM_MAPPING = {
    # Test placeholders and standard aliases
    "dosa": "dosa_counter",
    "DOSA": "dosa_counter",
    "TEST_DOSA": "dosa_counter",
    "A006": "dosa_counter",   # Plain Dosa
    "A007": "dosa_counter",   # Masala Dosa
    "MAI19": "dosa_counter",  # Ghee Roast
    "MAI20": "dosa_counter",  # Masala Roast
    "MAI22": "dosa_counter",  # Plain Roast
    "MAI23": "dosa_counter",  # Podi Roast

    "juice": "juice_counter",
    "JUICE": "juice_counter",
    "TEST_JUICE": "juice_counter",
    "JUI4": "juice_counter",  # Badam Milk
    "JUI5": "juice_counter",  # Grape Juice
    "JUI6": "juice_counter",  # Pista Milk

    "biryani": "biryani_pot",
    "BIRYANI": "biryani_pot",
    "TEST_BIRYANI": "biryani_pot",
    "MAI16": "biryani_pot",   # Egg Fried Rice

    "ice_cream": "ice_cream_station",
    "ice cream": "ice_cream_station",
    "ICECREAM": "ice_cream_station",
    "TEST_ICECREAM": "ice_cream_station",
    "BAK16": "ice_cream_station",

    "cool_drink": "cool_drink_station",
    "cool drink": "cool_drink_station",
    "COOLDRINK": "cool_drink_station",
    "TEST_COOLDRINK": "cool_drink_station",
    "A001": "quick_items",
    "A002": "quick_items",
}

CANTEEN_CONFIGS = {
    # 1. Main Canteen (SOPANAM)
    "24c1a6a4-d9f9-426f-a0eb-8e30b7a86ce5": {
        "stations": STANDARD_STATIONS,
        "items": DEFAULT_ITEM_MAPPING,
        "default_station": "default_station",
    },
    # 2. IT Canteen
    "6dedf492-3b41-43c1-b40e-e7d5cd4e7b97": {
        "stations": STANDARD_STATIONS,
        "items": DEFAULT_ITEM_MAPPING,
        "default_station": "default_station",
    },
    # 3. MBA Canteen
    "bc65894a-1032-43c8-9b49-78fce23ac6e0": {
        "stations": STANDARD_STATIONS,
        "items": DEFAULT_ITEM_MAPPING,
        "default_station": "default_station",
    },
}


def get_canteen_config(canteen_id):
    """
    Returns the station and item config for a given canteen ID string.
    Falls back to the standard configuration if canteen_id is not specifically configured.
    """
    key = str(canteen_id)
    if key in CANTEEN_CONFIGS:
        return CANTEEN_CONFIGS[key]
    return {
        "stations": STANDARD_STATIONS,
        "items": DEFAULT_ITEM_MAPPING,
        "default_station": "default_station",
    }


def get_station_for_product(canteen_id, product):
    """
    Resolves the station configuration dict for a product in a canteen.
    Checks product_code, then name-based fallbacks.
    """
    cfg = get_canteen_config(canteen_id)
    stations = cfg.get("stations", STANDARD_STATIONS)
    items = cfg.get("items", DEFAULT_ITEM_MAPPING)
    default_station_name = cfg.get("default_station", "default_station")

    code = getattr(product, "product_code", "")
    name = getattr(product, "name", "").lower()

    # 1. Direct code lookup
    station_name = items.get(code)
    if not station_name:
        # 2. Case-insensitive code or name match
        for key, st in items.items():
            if key.lower() == code.lower() or key.lower() == name:
                station_name = st
                break

    # 3. Keyword heuristic if still not mapped
    if not station_name:
        if "dosa" in name or "roast" in name:
            station_name = "dosa_counter"
        elif "juice" in name:
            station_name = "juice_counter"
        elif "biryani" in name or "fried rice" in name:
            station_name = "biryani_pot"
        elif "ice cream" in name:
            station_name = "ice_cream_station"
        elif "cool drink" in name or "beverage" in getattr(product, "type", "").lower():
            station_name = "cool_drink_station"
        else:
            station_name = default_station_name

    station_def = stations.get(station_name, stations.get(default_station_name, {"kind": "quick", "minutes": 2}))
    return station_name, station_def
