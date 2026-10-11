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
    STAFF_CREDIT_MINUTES,
    STAFF_EXPRESS_ENABLED,
    STAFF_MAX_EXPRESS,
    STAFF_STATION_PRIORITY,
    STATION_IN_PROGRESS_ALLOWANCE,
    STAFF_BULK_PORTIONS_FIRST,
)
from .order_flow import is_order_quick_only, effective_time, get_staff_user_ids, is_staff_member


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
    Queue timeline calculation for all open orders of a canteen.
    Implements staff express lane and station-level priority:
    - Express admitted staff orders have starts_in_minutes = 0 and queue_position = None.
    - Staff orders at stations jump ahead of student orders not yet in progress,
      with a non-preemptive in-progress allowance: min(slots, student_units_preparing).
    - Student slot simulation includes staff orders so student wait times accurately grow.
    """
    cid = str(canteen_id)
    open_orders = list(
        Order.objects.filter(canteen_id=canteen_id, status__in=["pending", "preparing"])
        .select_related("user")
        .prefetch_related("items__product")
        .order_by("id")
    )

    menu_stocks = {
        m.product_id: m.stock
        for m in Menu.objects.filter(canteen_id=canteen_id)
    }

    user_ids = {o.user_id for o in open_orders if o.user_id}
    staff_ids = get_staff_user_ids(user_ids)

    cfg = get_canteen_config(canteen_id)
    stations_def = cfg.get("stations", {})

    now = django_tz.now()
    pack_min = getattr(settings, "PACKING_MINUTES", PACKING_MINUTES)
    max_prep = getattr(settings, "MAX_PREPARING", MAX_PREPARING)
    express_enabled = getattr(settings, "STAFF_EXPRESS_ENABLED", STAFF_EXPRESS_ENABLED)
    max_express = getattr(settings, "STAFF_MAX_EXPRESS", STAFF_MAX_EXPRESS)
    station_prio = getattr(settings, "STAFF_STATION_PRIORITY", STAFF_STATION_PRIORITY)
    in_prog_allowance = getattr(settings, "STATION_IN_PROGRESS_ALLOWANCE", STATION_IN_PROGRESS_ALLOWANCE)
    bulk_staff_first = getattr(settings, "STAFF_BULK_PORTIONS_FIRST", STAFF_BULK_PORTIONS_FIRST)

    preparing_orders = [o for o in open_orders if o.status == "preparing"]
    pending_orders = [o for o in open_orders if o.status == "pending"]

    # Order pending orders by effective priority
    pending_orders.sort(key=lambda ord: effective_time(ord, staff_ids))

    # Pre-calculate student preparing units per station for in-progress allowance
    student_prep_units_by_station = defaultdict(int)
    for ord in preparing_orders:
        if ord.user_id not in staff_ids:
            for it in ord.items.all():
                st_name, _ = get_station_for_product(cid, it.product)
                student_prep_units_by_station[st_name] += it.quantity

    # Pre-calculate total staff units across all open orders
    total_staff_units_by_station = defaultdict(int)
    total_staff_units_by_product = defaultdict(int)
    for ord in open_orders:
        if ord.user_id in staff_ids:
            for it in ord.items.all():
                st_name, _ = get_station_for_product(cid, it.product)
                total_staff_units_by_station[st_name] += it.quantity
                total_staff_units_by_product[it.product_id] += it.quantity

    timeline = {}

    # Track station backlogs sequentially per tier
    staff_cumul_station = defaultdict(int)
    staff_cumul_product = defaultdict(int)
    student_cumul_station = defaultdict(int)
    student_cumul_product = defaultdict(int)
    fifo_cumul_station = defaultdict(int)
    fifo_cumul_product = defaultdict(int)

    def get_units_ahead(ord_items, is_staff):
        if not station_prio:
            # Legacy FIFO fallback
            return defaultdict(int, fifo_cumul_station), defaultdict(int, fifo_cumul_product)

        if is_staff:
            ahead_st = defaultdict(int)
            for s_name, q in staff_cumul_station.items():
                ahead_st[s_name] = q

            if in_prog_allowance:
                for s_name, s_def in stations_def.items():
                    if s_def.get("kind") == "live":
                        slots = max(1, s_def.get("slots", 1))
                        ahead_st[s_name] += min(slots, student_prep_units_by_station[s_name])

            ahead_prod = defaultdict(int)
            if bulk_staff_first:
                for p_id, q in staff_cumul_product.items():
                    ahead_prod[p_id] = q
            else:
                for p_id, q in staff_cumul_product.items():
                    ahead_prod[p_id] += q
                for p_id, q in student_cumul_product.items():
                    ahead_prod[p_id] += q

            return ahead_st, ahead_prod
        else:
            # Student order: behind all staff orders + earlier student orders
            ahead_st = defaultdict(int)
            for s_name, q in total_staff_units_by_station.items():
                ahead_st[s_name] += q
            for s_name, q in student_cumul_station.items():
                ahead_st[s_name] += q

            ahead_prod = defaultdict(int)
            for p_id, q in total_staff_units_by_product.items():
                ahead_prod[p_id] += q
            for p_id, q in student_cumul_product.items():
                ahead_prod[p_id] += q

            return ahead_st, ahead_prod

    def record_order_units(ord_items, is_staff):
        for it in ord_items:
            st_name, _ = get_station_for_product(cid, it.product)
            if is_staff:
                staff_cumul_station[st_name] += it.quantity
                staff_cumul_product[it.product_id] += it.quantity
            else:
                student_cumul_station[st_name] += it.quantity
                student_cumul_product[it.product_id] += it.quantity
            fifo_cumul_station[st_name] += it.quantity
            fifo_cumul_product[it.product_id] += it.quantity

    # 1. Process PREPARING orders
    for ord in preparing_orders:
        items = list(ord.items.all())
        is_staff = ord.user_id in staff_ids
        quick = is_order_quick_only(ord, cid)

        ahead_st, ahead_prod = get_units_ahead(items, is_staff)
        own_prep, backlog = compute_order_prep_and_backlog(
            cid,
            items,
            ahead_st,
            ahead_prod,
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
            "own_prep": own_prep,
            "is_quick": quick,
            "is_staff": is_staff,
        }

        record_order_units(items, is_staff)

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

    active_slot_count = sum(1 for ord in preparing_orders if not timeline[ord.id]["is_quick"])
    staff_express_active = sum(
        1 for ord in preparing_orders if not timeline[ord.id]["is_quick"] and ord.user_id in staff_ids
    )

    # 3. Process PENDING orders in priority order
    waiting_queue_pos = 0

    for ord in pending_orders:
        items = list(ord.items.all())
        is_staff = ord.user_id in staff_ids
        quick = is_order_quick_only(ord, cid)

        ahead_st, ahead_prod = get_units_ahead(items, is_staff)
        own_prep, backlog = compute_order_prep_and_backlog(
            cid,
            items,
            ahead_st,
            ahead_prod,
            menu_stocks,
        )

        if quick:
            starts_in = 0
            queue_pos = None
            kitchen_finish = backlog
        elif is_staff and express_enabled and staff_express_active < max_express:
            # Staff Express Lane admission: immediate starts_in=0, queue_position=None
            starts_in = 0
            queue_pos = None
            slot_finish = own_prep
            heapq.heappush(slot_finish_times, slot_finish)
            active_slot_count += 1
            staff_express_active += 1
            kitchen_finish = backlog
        else:
            # Normal slot queueing (students, or staff exceeding express cap)
            waiting_queue_pos += 1
            queue_pos = waiting_queue_pos

            earliest_free = heapq.heappop(slot_finish_times)
            starts_in = int(math.ceil(earliest_free))
            slot_finish = earliest_free + own_prep
            heapq.heappush(slot_finish_times, slot_finish)
            active_slot_count += 1
            if is_staff:
                staff_express_active += 1

            kitchen_finish = max(backlog, slot_finish)

        wait_min = int(math.ceil(kitchen_finish + pack_min))
        exp_delivery = (now + timedelta(minutes=wait_min)).isoformat()

        timeline[ord.id] = {
            "wait_minutes": wait_min,
            "starts_in_minutes": starts_in,
            "queue_position": queue_pos,
            "expected_delivery_time": exp_delivery,
            "kitchen_finish": kitchen_finish,
            "own_prep": own_prep,
            "is_quick": quick,
            "is_staff": is_staff,
        }

        record_order_units(items, is_staff)

    return timeline


def estimate_order_wait(canteen_id, items_list, user=None):
    """
    Hypothetical wait time estimate for a cart / new order.
    Differentiates between staff (express estimate) and student.
    items_list can be a list of dicts: [{'product': Product, 'quantity': int}, ...]
    or [{'product_id': id, 'quantity': int}, ...]
    """
    cid = str(canteen_id)
    cfg = get_canteen_config(canteen_id)
    stations_def = cfg.get("stations", {})

    is_staff = is_staff_member(user) if user else False
    now = django_tz.now()
    pack_min = getattr(settings, "PACKING_MINUTES", PACKING_MINUTES)
    max_prep = getattr(settings, "MAX_PREPARING", MAX_PREPARING)
    express_enabled = getattr(settings, "STAFF_EXPRESS_ENABLED", STAFF_EXPRESS_ENABLED)
    max_express = getattr(settings, "STAFF_MAX_EXPRESS", STAFF_MAX_EXPRESS)
    station_prio = getattr(settings, "STAFF_STATION_PRIORITY", STAFF_STATION_PRIORITY)
    in_prog_allowance = getattr(settings, "STATION_IN_PROGRESS_ALLOWANCE", STATION_IN_PROGRESS_ALLOWANCE)
    bulk_staff_first = getattr(settings, "STAFF_BULK_PORTIONS_FIRST", STAFF_BULK_PORTIONS_FIRST)

    open_orders = list(
        Order.objects.filter(canteen_id=canteen_id, status__in=["pending", "preparing"])
        .select_related("user")
        .prefetch_related("items__product")
        .order_by("id")
    )

    menu_stocks = {
        m.product_id: m.stock
        for m in Menu.objects.filter(canteen_id=canteen_id)
    }

    user_ids = {o.user_id for o in open_orders if o.user_id}
    staff_ids = get_staff_user_ids(user_ids)

    preparing_orders = [o for o in open_orders if o.status == "preparing"]
    pending_orders = [o for o in open_orders if o.status == "pending"]

    # Normalize items_list into objects with .product and .quantity
    normalized_items = []
    for entry in items_list:
        if isinstance(entry, (tuple, list)):
            prod = entry[0]
            qty = int(entry[1])
        elif isinstance(entry, dict):
            prod = entry.get("product")
            if not prod and "product_id" in entry:
                from .models import Product
                prod = Product.objects.filter(id=entry["product_id"]).first()
            qty = int(entry.get("quantity", 1))
        else:
            prod = getattr(entry, "product", None)
            qty = getattr(entry, "quantity", 1)
        if prod:
            class ItemStub:
                def __init__(self, p, q):
                    self.product = p
                    self.quantity = q
            normalized_items.append(ItemStub(prod, qty))

    if not normalized_items:
        # Default empty cart estimate
        default_wait = 5
        return {
            "wait_minutes": default_wait,
            "starts_in_minutes": 0,
            "queue_position": None if is_staff else len(pending_orders) + 1,
            "range": f"{default_wait} to {default_wait + 2} min",
            "expected_delivery_time": (now + timedelta(minutes=default_wait)).isoformat(),
        }

    # Check if quick-only
    is_quick = True
    for it in normalized_items:
        _, st_def = get_station_for_product(cid, it.product)
        if st_def.get("kind") != "quick":
            is_quick = False
            break

    # Student units currently in preparing
    student_prep_units_by_station = defaultdict(int)
    for ord in preparing_orders:
        if ord.user_id not in staff_ids:
            for it in ord.items.all():
                st_name, _ = get_station_for_product(cid, it.product)
                student_prep_units_by_station[st_name] += it.quantity

    # Total open staff units
    total_staff_units_by_station = defaultdict(int)
    total_staff_units_by_product = defaultdict(int)
    for ord in open_orders:
        if ord.user_id in staff_ids:
            for it in ord.items.all():
                st_name, _ = get_station_for_product(cid, it.product)
                total_staff_units_by_station[st_name] += it.quantity
                total_staff_units_by_product[it.product_id] += it.quantity

    # Total open student units
    total_student_units_by_station = defaultdict(int)
    total_student_units_by_product = defaultdict(int)
    for ord in open_orders:
        if ord.user_id not in staff_ids:
            for it in ord.items.all():
                st_name, _ = get_station_for_product(cid, it.product)
                total_student_units_by_station[st_name] += it.quantity
                total_student_units_by_product[it.product_id] += it.quantity

    # Units ahead for this hypothetical order
    if is_staff and station_prio:
        ahead_st = defaultdict(int)
        for s_name, q in total_staff_units_by_station.items():
            ahead_st[s_name] = q
        if in_prog_allowance:
            for s_name, s_def in stations_def.items():
                if s_def.get("kind") == "live":
                    slots = max(1, s_def.get("slots", 1))
                    ahead_st[s_name] += min(slots, student_prep_units_by_station[s_name])

        ahead_prod = defaultdict(int)
        if bulk_staff_first:
            for p_id, q in total_staff_units_by_product.items():
                ahead_prod[p_id] = q
        else:
            for p_id, q in total_staff_units_by_product.items():
                ahead_prod[p_id] += q
            for p_id, q in total_student_units_by_product.items():
                ahead_prod[p_id] += q
    else:
        ahead_st = defaultdict(int)
        for s_name, q in total_staff_units_by_station.items():
            ahead_st[s_name] += q
        for s_name, q in total_student_units_by_station.items():
            ahead_st[s_name] += q

        ahead_prod = defaultdict(int)
        for p_id, q in total_staff_units_by_product.items():
            ahead_prod[p_id] += q
        for p_id, q in total_student_units_by_product.items():
            ahead_prod[p_id] += q

    own_prep, backlog = compute_order_prep_and_backlog(
        cid,
        normalized_items,
        ahead_st,
        ahead_prod,
        menu_stocks,
    )

    # Active slot tracking
    timeline = canteen_timeline(canteen_id)
    slot_finish_times = [
        timeline.get(ord.id, {}).get("kitchen_finish", 0.0)
        for ord in preparing_orders
        if not timeline.get(ord.id, {}).get("is_quick", False)
    ]
    while len(slot_finish_times) < max_prep:
        slot_finish_times.append(0.0)
    heapq.heapify(slot_finish_times)

    staff_express_active = sum(
        1 for ord in preparing_orders
        if not timeline.get(ord.id, {}).get("is_quick", False) and ord.user_id in staff_ids
    )

    # Replay pending orders in priority order into slot heap
    pending_orders.sort(key=lambda ord: effective_time(ord, staff_ids))
    for ord in pending_orders:
        ord_tl = timeline.get(ord.id, {})
        if not ord_tl.get("is_quick", False):
            ord_is_staff = ord.user_id in staff_ids
            if ord_is_staff and express_enabled and staff_express_active < max_express:
                heapq.heappush(slot_finish_times, ord_tl.get("own_prep", 0.0))
                staff_express_active += 1
            else:
                earliest = heapq.heappop(slot_finish_times)
                heapq.heappush(slot_finish_times, earliest + ord_tl.get("own_prep", 0.0))

    if is_quick:
        starts_in = 0
        queue_pos = None
        kitchen_finish = backlog
    elif is_staff and express_enabled and staff_express_active < max_express:
        starts_in = 0
        queue_pos = None
        kitchen_finish = backlog
    else:
        earliest_free = heapq.heappop(slot_finish_times)
        starts_in = int(math.ceil(earliest_free))
        slot_finish = earliest_free + own_prep
        kitchen_finish = max(backlog, slot_finish)
        queue_pos = len(pending_orders) + 1

    wait_min = int(math.ceil(kitchen_finish + pack_min))
    exp_delivery = (now + timedelta(minutes=wait_min)).isoformat()

    return {
        "wait_minutes": wait_min,
        "starts_in_minutes": starts_in,
        "queue_position": queue_pos,
        "range": f"{wait_min} to {wait_min + 2} min",
        "expected_delivery_time": exp_delivery,
    }
