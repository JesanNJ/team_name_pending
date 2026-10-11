import logging
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Canteen, Order
from .wait_config import get_station_for_product, MAX_PREPARING, STAFF_CREDIT_MINUTES

logger = logging.getLogger(__name__)


def is_staff_member(user):
    """
    Checks if a user belongs to the Django auth Group named 'Staff'.
    Does not use Django's is_staff flag.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if hasattr(user, "_prefetched_objects_cache") and "groups" in user._prefetched_objects_cache:
        return any(g.name == "Staff" for g in user.groups.all())
    return user.groups.filter(name="Staff").exists()


def get_staff_user_ids(user_ids):
    """
    Given an iterable of user IDs, returns a set of user IDs that belong to the 'Staff' group.
    Executes in a single query to prevent N+1 queries.
    """
    if not user_ids:
        return set()
    from django.contrib.auth.models import User
    return set(
        User.objects.filter(groups__name="Staff", id__in=user_ids).values_list("id", flat=True)
    )


def effective_time(order, staff_ids=None):
    """
    Sort key function for ordering pending orders with staff preference:
        effective_time = order.created_at - STAFF_CREDIT_MINUTES (if order user is staff)
        effective_time = order.created_at (otherwise)
    Ties broken by lower order.id.
    Returns: (effective_datetime, order.id)
    """
    credit = getattr(settings, "STAFF_CREDIT_MINUTES", STAFF_CREDIT_MINUTES)
    is_staff = False
    if staff_ids is not None:
        is_staff = order.user_id in staff_ids
    elif getattr(order, "user", None):
        is_staff = is_staff_member(order.user)

    eff_dt = order.created_at or timezone.now()
    if is_staff:
        eff_dt = eff_dt - timedelta(minutes=credit)

    return (eff_dt, order.id)


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
    - Promoted by ascending effective_time; ties broken by lower order id.
    - Orders already preparing are NEVER displaced/preempted.
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

        # Pending orders ordered by effective_time, ties broken by lower id
        pending_orders = list(
            Order.objects.filter(
                canteen_id=canteen.id,
                status="pending"
            ).prefetch_related("items__product")
        )

        user_ids = {ord.user_id for ord in pending_orders if ord.user_id}
        staff_ids = get_staff_user_ids(user_ids)

        pending_orders.sort(key=lambda ord: effective_time(ord, staff_ids))

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
