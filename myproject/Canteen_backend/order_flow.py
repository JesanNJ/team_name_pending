import logging
from django.conf import settings
from django.db import transaction
from .models import Canteen, Order
from .wait_config import get_station_for_product, MAX_PREPARING

logger = logging.getLogger(__name__)


def is_order_quick_only(order, canteen_id=None):
    """
    Returns True if an order contains ONLY quick-station items.
    Returns False if order has no items or has at least one live/bulk item.
    """
    cid = canteen_id or getattr(order, "canteen_id", None)
    items = list(order.items.all())
    if not items:
        return False

    for item in items:
        _, station_def = get_station_for_product(cid, item.product)
        if station_def.get("kind") != "quick":
            return False
    return True


def promote_pending(canteen_or_id):
    """
    Concurrency-safe promotion of pending orders to preparing for a canteen.
    - Limits concurrent non-quick preparing orders to MAX_PREPARING (default 15).
    - Quick-only orders skip the cap.
    - Lowest ID pending orders are promoted first (FIFO).
    """
    canteen_id = canteen_or_id.id if isinstance(canteen_or_id, Canteen) else canteen_or_id
    promoted_orders = []

    with transaction.atomic():
        # Concurrency safety: row-level lock on Canteen
        try:
            canteen = Canteen.objects.select_for_update().get(id=canteen_id)
        except Canteen.DoesNotExist:
            return []

        # Count preparing orders that consume kitchen slots (non-quick)
        preparing_orders = Order.objects.filter(
            canteen_id=canteen.id,
            status="preparing"
        ).prefetch_related("items__product")

        active_slot_count = sum(
            1 for ord in preparing_orders if not is_order_quick_only(ord, canteen.id)
        )

        max_prep = getattr(settings, "MAX_PREPARING", MAX_PREPARING)
        free_slots = max(0, max_prep - active_slot_count)

        # Pending orders in FIFO order
        pending_orders = Order.objects.filter(
            canteen_id=canteen.id,
            status="pending"
        ).prefetch_related("items__product").order_by("id")

        for ord in pending_orders:
            quick = is_order_quick_only(ord, canteen.id)
            if quick:
                ord.status = "preparing"
                ord.save(update_fields=["status"])
                promoted_orders.append(ord)
            elif free_slots > 0:
                ord.status = "preparing"
                ord.save(update_fields=["status"])
                free_slots -= 1
                promoted_orders.append(ord)

    return promoted_orders


def sweep_pending_orders():
    """
    Sweeps all canteens and promotes eligible pending orders.
    """
    canteen_ids = list(Canteen.objects.values_list("id", flat=True))
    total_promoted = []
    for cid in canteen_ids:
        total_promoted.extend(promote_pending(cid))
    return total_promoted
