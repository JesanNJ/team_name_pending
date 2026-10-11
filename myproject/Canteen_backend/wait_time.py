import math
import heapq
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.utils import timezone as django_tz

from .models import Order, Menu
from .wait_config import (
    get_canteen_config,
    get_station_for_product,
    PACKING_MINUTES,
    MAX_PREPARING,
)
from .order_flow import is_order_quick_only


def compute_order_prep_and_backlog(
    canteen_id,
    order_items,
    units_ahead_by_station,
    units_ahead_by_product,
    menu_stocks,
):
    """
    Computes (own_prep, backlog) for an order given the current units ahead.
    order_items is an iterable of objects with .product and .quantity.
    """
    cfg = get_canteen_config(canteen_id)
    stations_def = cfg.get("stations", {})

    station_own_times = defaultdict(float)
    station_backlog_times = defaultdict(float)

    # Group items by station and product
    items_by_station = defaultdict(list)
    for it in order_items:
        st_name, st_def = get_station_for_product(canteen_id, it.product)
        items_by_station[st_name].append(it)

    for st_name, items in items_by_station.items():
        st_def = stations_def.get(st_name, {})
        kind = st_def.get("kind", "quick")
        own_units = sum(it.quantity for it in items)
        ahead_units = units_ahead_by_station[st_name]

        if kind == "live":
            slots = max(1, st_def.get("slots", 1))
            min_per_unit = st_def.get("minutes_per_unit", 2)
            # Own prep time alone
            own_t = math.ceil(own_units / slots) * min_per_unit
            # Backlog prep time including ahead units
            backlog_t = math.ceil((ahead_units + own_units) / slots) * min_per_unit
            station_own_times[st_name] = own_t
            station_backlog_times[st_name] = backlog_t

        elif kind == "quick":
            minutes = st_def.get("minutes", 1)
            # Quick items ignore queue
            station_own_times[st_name] = minutes
            station_backlog_times[st_name] = minutes

        elif kind == "bulk":
            plating_minutes = st_def.get("plating_minutes", 2)
            batch_size = max(1, st_def.get("batch_size", 20))
            batch_minutes = st_def.get("batch_minutes", 25)

            # Bulk items are evaluated per product
            own_t_max = 0
            backlog_t_max = 0

            for it in items:
                p_id = it.product.id
                initial_stock = menu_stocks.get(p_id, 0)
                ahead_p = units_ahead_by_product[p_id]

                # Own prep alone (assuming ample stock unless initial is 0)
                if it.quantity <= initial_stock:
                    it_own = plating_minutes
                else:
                    shortfall_own = it.quantity - max(0, initial_stock)
                    it_own = math.ceil(shortfall_own / batch_size) * batch_minutes
                own_t_max = max(own_t_max, it_own)

                # Backlog prep
                remaining = initial_stock - ahead_p
                if it.quantity <= remaining:
                    it_backlog = plating_minutes
                else:
                    shortfall_backlog = it.quantity - max(0, remaining)
                    it_backlog = math.ceil(shortfall_backlog / batch_size) * batch_minutes
                backlog_t_max = max(backlog_t_max, it_backlog)

            station_own_times[st_name] = own_t_max
            station_backlog_times[st_name] = backlog_t_max

        else:
            # Fallback
            station_own_times[st_name] = 2
            station_backlog_times[st_name] = 2

    def combine_times(station_times):
        group_totals = defaultdict(float)
        ungrouped = []
        for st_name, t in station_times.items():
            st_def = stations_def.get(st_name, {})
            grp = st_def.get("group")
            if grp:
                group_totals[grp] += t
            else:
                ungrouped.append(t)
        all_vals = list(group_totals.values()) + ungrouped
        return max(all_vals) if all_vals else 0.0

    own_prep = combine_times(station_own_times)
    backlog = combine_times(station_backlog_times)

    return own_prep, backlog


def canteen_timeline(canteen_id):
    """
    Single-pass calculation of queue timeline for all open orders of a canteen.
    Returns dict: {
        order_id: {
            "wait_minutes": int,
            "starts_in_minutes": int,
            "queue_position": int or None,
            "expected_delivery_time": ISO format string or None,
            "kitchen_finish": float,
        }
    }
    """
    cid = str(canteen_id)
    open_orders = (
        Order.objects.filter(canteen_id=canteen_id, status__in=["pending", "preparing"])
        .prefetch_related("items__product")
        .order_by("id")
    )

    # Menu stock lookup
    menu_stocks = {
        m.product_id: m.stock
        for m in Menu.objects.filter(canteen_id=canteen_id)
    }

    units_ahead_by_station = defaultdict(int)
    units_ahead_by_product = defaultdict(int)
    timeline = {}

    preparing_orders = [o for o in open_orders if o.status == "preparing"]
    pending_orders = [o for o in open_orders if o.status == "pending"]

    now = django_tz.now()
    pack_min = getattr(settings, "PACKING_MINUTES", PACKING_MINUTES)
    max_prep = getattr(settings, "MAX_PREPARING", MAX_PREPARING)

    # 1. Process PREPARING orders
    for ord in preparing_orders:
        items = list(ord.items.all())
        own_prep, backlog = compute_order_prep_and_backlog(
            cid,
            items,
            units_ahead_by_station,
            units_ahead_by_product,
            menu_stocks,
        )

        kitchen_finish = backlog
        wait_min = int(math.ceil(kitchen_finish + pack_min))
        exp_delivery = (now + timedelta(minutes=wait_min)).isoformat()

        timeline[ord.id] = {
            "wait_minutes": wait_min,
            "starts_in_minutes": 0,
            "queue_position": None,
            "expected_delivery_time": exp_delivery,
            "kitchen_finish": kitchen_finish,
            "is_quick": is_order_quick_only(ord, cid),
        }

        # Update cumulative ahead counters
        for it in items:
            st_name, _ = get_station_for_product(cid, it.product)
            units_ahead_by_station[st_name] += it.quantity
            units_ahead_by_product[it.product_id] += it.quantity

    # 2. Setup slot tracking for preparing slots
    slot_finish_times = [
        timeline[ord.id]["kitchen_finish"]
        for ord in preparing_orders
        if not timeline[ord.id]["is_quick"]
    ]

    # Pad up to MAX_PREPARING with 0 for free slots
    while len(slot_finish_times) < max_prep:
        slot_finish_times.append(0.0)

    heapq.heapify(slot_finish_times)

    # 3. Process PENDING orders (FIFO)
    for idx, ord in enumerate(pending_orders):
        queue_pos = idx + 1
        items = list(ord.items.all())
        quick = is_order_quick_only(ord, cid)

        own_prep, backlog = compute_order_prep_and_backlog(
            cid,
            items,
            units_ahead_by_station,
            units_ahead_by_product,
            menu_stocks,
        )

        if quick:
            starts_in = 0
            kitchen_finish = backlog
            wait_min = int(math.ceil(kitchen_finish + pack_min))
            exp_delivery = (now + timedelta(minutes=wait_min)).isoformat()
        else:
            earliest_free = heapq.heappop(slot_finish_times)
            starts_in = int(math.ceil(earliest_free))
            slot_finish = earliest_free + own_prep
            heapq.heappush(slot_finish_times, slot_finish)

            kitchen_finish = max(backlog, slot_finish)
            wait_min = int(math.ceil(kitchen_finish + pack_min))
            exp_delivery = (now + timedelta(minutes=wait_min)).isoformat()

        timeline[ord.id] = {
            "wait_minutes": wait_min,
            "starts_in_minutes": starts_in,
            "queue_position": queue_pos,
            "expected_delivery_time": exp_delivery,
            "kitchen_finish": kitchen_finish,
            "is_quick": quick,
        }

        # Update cumulative ahead counters
        for it in items:
            st_name, _ = get_station_for_product(cid, it.product)
            units_ahead_by_station[st_name] += it.quantity
            units_ahead_by_product[it.product_id] += it.quantity

    return timeline


def estimate_order_wait(canteen_id, items_list):
    """
    Hypothetical wait time estimate for a cart/new order.
    items_list can be a list of dicts: [{'product': Product, 'quantity': int}, ...]
    or [{'product_id': id, 'quantity': int}, ...]
    """
    cid = str(canteen_id)
    # Get current timeline to find state after all existing orders
    timeline = canteen_timeline(canteen_id)

    # Replay ahead units
    units_ahead_by_station = defaultdict(int)
    units_ahead_by_product = defaultdict(int)

    open_orders = (
        Order.objects.filter(canteen_id=canteen_id, status__in=["pending", "preparing"])
        .prefetch_related("items__product")
        .order_by("id")
    )
    for ord in open_orders:
        for it in ord.items.all():
            st_name, _ = get_station_for_product(cid, it.product)
            units_ahead_by_station[st_name] += it.quantity
            units_ahead_by_product[it.product_id] += it.quantity

    menu_stocks = {
        m.product_id: m.stock
        for m in Menu.objects.filter(canteen_id=canteen_id)
    }

    # Normalize items_list into objects with .product and .quantity
    normalized_items = []
    for entry in items_list:
        prod = entry.get("product")
        if not prod and "product_id" in entry:
            from .models import Product
            prod = Product.objects.filter(id=entry["product_id"]).first()
        if prod:
            qty = int(entry.get("quantity", 1))
            class ItemStub:
                def __init__(self, p, q):
                    self.product = p
                    self.quantity = q
            normalized_items.append(ItemStub(prod, qty))

    if not normalized_items:
        # Default empty cart estimate
        return {
            "wait_minutes": 5,
            "starts_in_minutes": 0,
            "queue_position": len([o for o in open_orders if o.status == "pending"]) + 1,
            "range": "5 to 7 min",
            "expected_delivery_time": (django_tz.now() + timedelta(minutes=5)).isoformat(),
        }

    # Check if quick-only
    is_quick = True
    for it in normalized_items:
        _, st_def = get_station_for_product(cid, it.product)
        if st_def.get("kind") != "quick":
            is_quick = False
            break

    own_prep, backlog = compute_order_prep_and_backlog(
        cid,
        normalized_items,
        units_ahead_by_station,
        units_ahead_by_product,
        menu_stocks,
    )

    pack_min = getattr(settings, "PACKING_MINUTES", PACKING_MINUTES)
    max_prep = getattr(settings, "MAX_PREPARING", MAX_PREPARING)
    now = django_tz.now()

    # Calculate queue slots
    preparing_orders = [o for o in open_orders if o.status == "preparing"]
    pending_orders = [o for o in open_orders if o.status == "pending"]

    slot_finish_times = [
        timeline.get(ord.id, {}).get("kitchen_finish", 0.0)
        for ord in preparing_orders
        if not timeline.get(ord.id, {}).get("is_quick", False)
    ]
    while len(slot_finish_times) < max_prep:
        slot_finish_times.append(0.0)
    heapq.heapify(slot_finish_times)

    for ord in pending_orders:
        if not timeline.get(ord.id, {}).get("is_quick", False):
            earliest = heapq.heappop(slot_finish_times)
            items = list(ord.items.all())
            o_prep, _ = compute_order_prep_and_backlog(
                cid, items, defaultdict(int), defaultdict(int), menu_stocks
            )
            heapq.heappush(slot_finish_times, earliest + o_prep)

    queue_pos = len(pending_orders) + 1
    if is_quick:
        starts_in = 0
        kitchen_finish = backlog
    else:
        earliest_free = heapq.heappop(slot_finish_times)
        starts_in = int(math.ceil(earliest_free))
        slot_finish = earliest_free + own_prep
        kitchen_finish = max(backlog, slot_finish)

    wait_min = int(math.ceil(kitchen_finish + pack_min))
    exp_delivery = (now + timedelta(minutes=wait_min)).isoformat()

    return {
        "wait_minutes": wait_min,
        "starts_in_minutes": starts_in,
        "queue_position": queue_pos,
        "range": f"{wait_min} to {wait_min + 2} min",
        "expected_delivery_time": exp_delivery,
    }
