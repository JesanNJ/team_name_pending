import logging
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Canteen, Order
from .wait_config import (
    get_station_for_product,
    MAX_PREPARING,
    STAFF_CREDIT_MINUTES,
    STAFF_EXPRESS_ENABLED,
    STAFF_MAX_EXPRESS,
)

logger = logging.getLogger(__name__)


def is_staff_member(user):
    """
    Checks if a user has UserProfile.role == "staff".
    Users without a UserProfile row are treated as non-staff and do not raise.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    try:
        profile = getattr(user, "userprofile", None)
        if profile is not None:
            return getattr(profile, "role", "") == "staff"
    except Exception:
        return False
    from .models import UserProfile
    return UserProfile.objects.filter(user=user, role="staff").exists()


def get_staff_user_ids(user_ids):
    """
    Given an iterable of user IDs, returns a set of user IDs that have UserProfile.role == "staff".
    Executes in a single query to prevent N+1 queries.
    Users without a UserProfile row are safely excluded and do not raise.
    """
    if not user_ids:
        return set()
    from .models import UserProfile
    return set(
        UserProfile.objects.filter(user_id__in=user_ids, role="staff").values_list("user_id", flat=True)
    )


def effective_time(order, staff_ids=None):
    """
    Sort key function for ordering pending orders with staff preference:
        When STAFF_EXPRESS_ENABLED is True:
            key = (0 if staff else 1, created_at, id)
        When STAFF_EXPRESS_ENABLED is False (legacy fallback):
            effective_time = order.created_at - STAFF_CREDIT_MINUTES (if staff)
            effective_time = order.created_at (otherwise)
    Ties broken by lower order.id.
    """
    is_staff = False
    if staff_ids is not None:
        is_staff = order.user_id in staff_ids
    elif getattr(order, "user", None):
        is_staff = is_staff_member(order.user)

    express_enabled = getattr(settings, "STAFF_EXPRESS_ENABLED", STAFF_EXPRESS_ENABLED)
    created = order.created_at or timezone.now()

    if express_enabled:
        return (0 if is_staff else 1, created, order.id)

    credit = getattr(settings, "STAFF_CREDIT_MINUTES", STAFF_CREDIT_MINUTES)
    eff_dt = created
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
    - Staff Express Lane: If STAFF_EXPRESS_ENABLED and staff_express_active < STAFF_MAX_EXPRESS,
      staff non-quick orders promote immediately past the cap.
    - Pending orders are promoted in priority order: (0 if staff else 1, created_at, id).
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
        preparing_orders = list(
            Order.objects.filter(
                canteen_id=canteen.id,
                status="preparing"
            ).prefetch_related("items__product")
        )

        prep_user_ids = {ord.user_id for ord in preparing_orders if ord.user_id}
        prep_staff_ids = get_staff_user_ids(prep_user_ids)

        active_count = 0
        staff_express_active = 0
        for ord in preparing_orders:
            if not is_order_quick_only(ord, canteen.id):
                active_count += 1
                if ord.user_id in prep_staff_ids:
                    staff_express_active += 1

        max_prep = getattr(settings, "MAX_PREPARING", MAX_PREPARING)
        express_enabled = getattr(settings, "STAFF_EXPRESS_ENABLED", STAFF_EXPRESS_ENABLED)
        max_express = getattr(settings, "STAFF_MAX_EXPRESS", STAFF_MAX_EXPRESS)

        # Pending orders ordered by priority
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
            is_staff = ord.user_id in staff_ids

            if quick:
                ord.status = "preparing"
                ord.save(update_fields=["status"])
                promoted_orders.append(ord)
            elif is_staff and express_enabled and staff_express_active < max_express:
                # Express lane: promote past cap
                ord.status = "preparing"
                ord.save(update_fields=["status"])
                active_count += 1
                staff_express_active += 1
                promoted_orders.append(ord)
            elif (max_prep - active_count) > 0:
                # Normal slot admission
                ord.status = "preparing"
                ord.save(update_fields=["status"])
                active_count += 1
                if is_staff:
                    staff_express_active += 1
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
