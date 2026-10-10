# Waiting-Time Estimation — Design Spec

Status: **design only, nothing implemented yet.**
Project: Canteen Management System (Django REST + React/Vite)

## 1. Goal

Show every order an estimated "ready in N minutes".

Requirements:

1. **Each canteen works separately.** One canteen's load never affects another's.
2. **Each order gets its own time.** It depends on the items in the order and its position in the queue.
3. **Items are prepared differently**: bulk (biryani), live counters (dosa, roast), ready items (ice cream, cool drink).
4. **No database changes.** No new model fields, no migrations. Everything is computed from existing data plus a config in code.

## 2. Existing data we use (no changes)

| Model | Fields used |
|---|---|
| `Order` | `id`, `canteen`, `status`, `created_at` |
| `OrderItem` | `order`, `product`, `quantity` |
| `Product` | `product_code`, `name`, `type` |
| `Menu` | `canteen`, `product`, `stock` |
| `Canteen` | `id` (UUID) |

Order statuses: `pending → preparing → prepared → delivered`.
An order is **open** (still consuming kitchen time) while `status in ("pending", "preparing")`.

## 3. Concepts

### Stations
Every item is made at a **station**. A canteen defines its own stations.

| Kind | Example | Behaviour |
|---|---|---|
| `live` | dosa, roast | Made to order by a limited number of cooks, so it queues |
| `bulk` | biryani | Cooked in batches; portions served from the pot |
| `quick` | ice cream, cool drink | Ready item, fixed small time, no queue |

### Why config (not DB)
`Product.type` only has Beverages / Veg / Non-Veg / Snacks, so it cannot tell biryani from dosa.
Items are mapped to stations by **canteen id + `product_code`** in a config module.

## 4. Config format (`wait_config.py`, in code)

```python
PACKING_MINUTES = 1
STOCK_DECREMENTED_ON_ORDER = False  # see section 6 (bulk rule)

CANTEEN_CONFIG = {
    # key = Canteen.id as string (see seed_db.py for the three UUIDs)
    "24c1a6a4-d9f9-426f-a0eb-8e30b7a86ce5": {          # Main Canteen
        "stations": {
            "dosa_counter": {"kind": "live", "slots": 1, "minutes_per_unit": 2, "group": "cook1"},
            "biryani_pot":  {"kind": "bulk", "plating_minutes": 2, "batch_size": 20, "batch_minutes": 25},
            "juice_counter":{"kind": "live", "slots": 1, "minutes_per_unit": 2},
            "ready_items":  {"kind": "quick", "minutes": 1},
        },
        # product_code -> station name  (fill from seed_db.py / Menu)
        "items": {
            "XXXX": "dosa_counter",
            "YYYY": "biryani_pot",
        },
        "default_station": "ready_items",   # items not listed above
    },
    # IT canteen, MBA canteen ... add the same way
}
```

Notes:
- `slots` = number of cooks/tawas working in parallel at that live station. Current assumption: **1 tawa, 1 cook = `slots: 1`**.
- `group` (optional): stations sharing the same person. Stations in the **same group add up**; different groups run in parallel. Leave out when a station has its own cook.
- Unknown canteen or item falls back to `default_station`, then to a global default of 5 minutes.

## 5. Algorithm

For an order `O` in canteen `C`:

1. If `O.status` not in (`pending`, `preparing`): return `None` (no estimate).
2. Collect **units ahead** per station: sum of `OrderItem.quantity`, grouped by station, over orders where
   `canteen == C`, `status in (pending, preparing)`, `id < O.id`.
3. Collect **own units** per station from `O`'s items.
4. Compute each station's wait (section 6).
5. Combine:
   - stations in the same `group`: **sum** their waits,
   - different groups / no group: **max** (they work in parallel),
   - add `PACKING_MINUTES`.
6. Return `ceil(result)`. In the UI show a range, for example `N` to `N+2` min.

## 6. Station rules

**Live**
```
wait = ceil( (units_ahead + own_units) / slots ) * minutes_per_unit
```

**Quick**
```
wait = minutes          # ignores queue
```

**Bulk** (per product at that pot)
```
remaining = stock - units_ahead          if not STOCK_DECREMENTED_ON_ORDER
remaining = stock                        otherwise
if own_units <= remaining:
    wait = plating_minutes
else:
    shortfall = own_units - max(remaining, 0)
    wait = ceil(shortfall / batch_size) * batch_minutes
```
`Menu.stock` is the portions currently in the pot. Today `place_order` does **not** reduce stock, so keep `STOCK_DECREMENTED_ON_ORDER = False` unless that is changed (changing it is a code change; ask first).

## 7. Worked example (1 tawa, 1 cook)

Order: **3 biryani, 6 dosa, 1 ice cream, 3 juice, 1 cool drink**.
Stations: dosa 2 min each (1 slot), juice 2 min each (1 slot), biryani plating 2 min, ready items 1 min, packing 1 min.

| Scenario | Dosa | Juice | Biryani | Ready | Total |
|---|---|---|---|---|---|
| A: quiet | 6 × 2 = 12 | 3 × 2 = 6 | 2 | 1 | max(12) + 1 = **13 min** |
| B: busy (8 dosas, 2 juices ahead) | (8+6) × 2 = 28 | (2+3) × 2 = 10 | 2 | 1 | max(28) + 1 = **29 min** |
| C: biryani short (1 left, need 3), quiet dosa | 12 | 6 | ceil(2/20) × 25 = 25 | 1 | max(25) + 1 = **26 min** |

Use these as unit tests.

Open design choice (case C): hold everything until the whole order is ready, or show per-item times so students can collect in parts. Pick one before building the UI.

## 8. Where to wire it in

1. **New file** `myproject/Canteen_backend/wait_config.py` (section 4).
2. **New file** `myproject/Canteen_backend/wait_time.py` with `estimate_wait_minutes(order)` (sections 5 and 6).
3. **Edit** `myproject/Canteen_backend/serializers.py`: add `wait_minutes = serializers.SerializerMethodField()` to `OrderSerializer`, add it to `Meta.fields`, and implement `get_wait_minutes` by calling the function above.
4. (Optional) New endpoint `GET /api/canteens/<uuid>/wait-time/` for the cart page, returning the current queue wait for a canteen.
5. **Frontend:** show `order.wait_minutes` on `Orders.jsx` / `OrderCard.jsx` for pending/preparing orders; show "Ready for pickup" once `prepared`.

`OrderSerializer` is used by `/api/orders/` and `/api/orders/<status>/`, so every order list gets the field automatically.

Performance: about 2 queries per open order. Fine for canteen-sized lists. Batch per canteen if lists grow.

## 9. Things to fix or know

- `orders_by_status` is **not filtered by canteen** and admins are **not tied to a canteen**, so every admin sees every canteen's orders. The wait calculation itself is per canteen, but the admin UI is not.
- `Menu.stock` is never decremented; the bulk rule depends on it (see section 6).
- `add_to_cart` does not check that the product belongs to that canteen's menu.
- The estimates are only as good as the config numbers, so tune them with real kitchen timings.

## 10. Information still needed

1. Per canteen: the list of stations, with product codes for each.
2. Per live station: number of cooks/tawas and minutes per item.
3. Per bulk item: batch size and cook time.
4. Does one cook cover several live stations (use `group`)?
5. Case C behaviour: hold everything, or collect in parts?

## 11. Working agreements

- **Ask before changing any code.**
- **Do not commit or push** until explicitly told; confirm twice before pushing.
