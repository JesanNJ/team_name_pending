import uuid
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.core.management import call_command
from rest_framework.test import APIRequestFactory, force_authenticate
from Canteen_backend.models import Canteen, Product, Menu, Order, OrderItem, UserProfile
from Canteen_backend.order_flow import (
    promote_pending,
    is_order_quick_only,
    effective_time,
    is_staff_member,
    get_staff_user_ids,
)
from Canteen_backend.wait_time import canteen_timeline
from Canteen_backend.serializers import OrderSerializer
from Canteen_backend.views import orders_by_status, user_orders


class WaitingTimeAndOrderFlowTests(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username="testuser", password="password")

        # Create canteen
        self.canteen = Canteen.objects.create(
            id=uuid.uuid4(),
            name="Test Canteen",
            location="Campus Center"
        )

        # Create products matching standard stations
        # Dosa (live, 1 slot, 2 min)
        self.prod_dosa = Product.objects.create(
            product_code="TEST_DOSA",
            name="Masala Dosa",
            price=50.0,
            type="Veg",
            canteen=self.canteen
        )
        # Juice (live, 1 slot, 2 min)
        self.prod_juice = Product.objects.create(
            product_code="TEST_JUICE",
            name="Grape Juice",
            price=40.0,
            type="Beverages",
            canteen=self.canteen
        )
        # Biryani (bulk, plating 2 min, batch 20, batch_minutes 25)
        self.prod_biryani = Product.objects.create(
            product_code="TEST_BIRYANI",
            name="Egg Biryani",
            price=120.0,
            type="Non-Veg",
            canteen=self.canteen
        )
        # Ice cream (quick, 1 min)
        self.prod_icecream = Product.objects.create(
            product_code="TEST_ICECREAM",
            name="Vanilla Ice Cream",
            price=30.0,
            type="Snacks",
            canteen=self.canteen
        )
        # Cool drink (quick, 1 min)
        self.prod_cooldrink = Product.objects.create(
            product_code="TEST_COOLDRINK",
            name="Cool Drink",
            price=25.0,
            type="Beverages",
            canteen=self.canteen
        )

        # Set default ample stock
        self.menu_dosa = Menu.objects.create(canteen=self.canteen, product=self.prod_dosa, stock=50, is_active=True)
        self.menu_juice = Menu.objects.create(canteen=self.canteen, product=self.prod_juice, stock=50, is_active=True)
        self.menu_biryani = Menu.objects.create(canteen=self.canteen, product=self.prod_biryani, stock=50, is_active=True)
        self.menu_icecream = Menu.objects.create(canteen=self.canteen, product=self.prod_icecream, stock=50, is_active=True)
        self.menu_cooldrink = Menu.objects.create(canteen=self.canteen, product=self.prod_cooldrink, stock=50, is_active=True)

    def _create_order(self, items_with_qty, status="pending"):
        """Helper to create an order with items"""
        order = Order.objects.create(
            user=self.user,
            canteen=self.canteen,
            total_price=100.0,
            status=status
        )
        for prod, qty in items_with_qty:
            OrderItem.objects.create(
                order=order,
                product=prod,
                quantity=qty,
                price=prod.price
            )
        return order

    def test_1_quiet_kitchen(self):
        """
        Test 1: Quiet kitchen (Case A in design spec)
        Order: 3 biryani, 6 dosa, 1 ice cream, 3 juice, 1 cool drink.
        Dosa: 6 * 2 = 12 min
        Juice: 3 * 2 = 6 min
        Biryani: 2 min (ample stock)
        Ice cream: 1 min, Cool drink: 1 min
        Packing: 1 min
        Expected: max(12) + 1 = 13 min
        """
        order = self._create_order([
            (self.prod_biryani, 3),
            (self.prod_dosa, 6),
            (self.prod_icecream, 1),
            (self.prod_juice, 3),
            (self.prod_cooldrink, 1),
        ], status="preparing")

        tl = canteen_timeline(self.canteen.id)
        self.assertEqual(tl[order.id]["wait_minutes"], 13)
        self.assertEqual(tl[order.id]["starts_in_minutes"], 0)

        serializer = OrderSerializer(order)
        self.assertEqual(serializer.data["wait_minutes"], 13)

    def test_2_busy_kitchen_with_queue(self):
        """
        Test 2: Busy kitchen with queue ahead (Case B in design spec)
        Ahead: 8 dosas, 2 juices in prior orders.
        Order: 6 dosa, 3 juice, 3 biryani, 1 ice cream, 1 cool drink.
        Dosa: (8 + 6) * 2 = 28 min
        Juice: (2 + 3) * 2 = 10 min
        Biryani: 2 min
        Packing: 1 min
        Expected: max(28) + 1 = 29 min
        """
        # Ahead order
        self._create_order([
            (self.prod_dosa, 8),
            (self.prod_juice, 2),
        ], status="preparing")

        # Current order
        order = self._create_order([
            (self.prod_biryani, 3),
            (self.prod_dosa, 6),
            (self.prod_icecream, 1),
            (self.prod_juice, 3),
            (self.prod_cooldrink, 1),
        ], status="preparing")

        tl = canteen_timeline(self.canteen.id)
        self.assertEqual(tl[order.id]["wait_minutes"], 29)

    def test_3_bulk_item_stock_exhaustion(self):
        """
        Test 3: Bulk-item stock exhaustion triggers batch delay (Case C in design spec)
        Biryani: stock remaining = 1, need 3. Shortfall = 2 -> ceil(2/20) * 25 = 25 min.
        Dosa: 6 * 2 = 12 min. Juice: 3 * 2 = 6 min.
        Packing: 1 min.
        Expected: max(25) + 1 = 26 min
        """
        self.menu_biryani.stock = 1
        self.menu_biryani.save()

        order = self._create_order([
            (self.prod_biryani, 3),
            (self.prod_dosa, 6),
            (self.prod_icecream, 1),
            (self.prod_juice, 3),
            (self.prod_cooldrink, 1),
        ], status="preparing")

        tl = canteen_timeline(self.canteen.id)
        self.assertEqual(tl[order.id]["wait_minutes"], 26)

    def test_4_quick_only_items_independent_of_queue(self):
        """
        Test 4: Quick-only items: independent of queue
        Prior orders have 20 dosas in queue.
        Order has only quick items: 1 ice cream, 1 cool drink.
        Quick wait: max(1, 1) = 1 min + packing 1 min = 2 min.
        """
        # Busy live orders ahead
        self._create_order([(self.prod_dosa, 20)], status="preparing")

        # Quick-only order
        quick_order = self._create_order([
            (self.prod_icecream, 1),
            (self.prod_cooldrink, 1),
        ], status="preparing")

        self.assertTrue(is_order_quick_only(quick_order, self.canteen.id))
        tl = canteen_timeline(self.canteen.id)
        self.assertEqual(tl[quick_order.id]["wait_minutes"], 2)

    def test_5_order_flow_cap_15_preparing_limit(self):
        """
        Test 5: Order flow cap: 15 preparing limit
        Create 15 live-station orders; all 15 move to preparing.
        A 16th live-station order stays in pending.
        A quick-only order moves to preparing immediately (skips cap).
        """
        orders = []
        for i in range(15):
            ord = self._create_order([(self.prod_dosa, 1)], status="pending")
            orders.append(ord)

        # Promote pending orders
        promote_pending(self.canteen)

        for ord in orders:
            ord.refresh_from_db()
            self.assertEqual(ord.status, "preparing")

        # 16th live order
        ord_16 = self._create_order([(self.prod_dosa, 1)], status="pending")
        promote_pending(self.canteen)
        ord_16.refresh_from_db()
        self.assertEqual(ord_16.status, "pending")

        # Quick-only order placed
        quick_ord = self._create_order([(self.prod_icecream, 1)], status="pending")
        promote_pending(self.canteen)
        quick_ord.refresh_from_db()
        self.assertEqual(quick_ord.status, "preparing")

    def test_6_promotion_cascades_when_slot_frees_up(self):
        """
        Test 6: Promotion cascades when slot frees up
        15 live orders in preparing + 1 live order in pending.
        When 1 preparing order moves to prepared (or cancelled), pending order is promoted.
        """
        orders = []
        for i in range(15):
            ord = self._create_order([(self.prod_dosa, 1)], status="pending")
            orders.append(ord)
        promote_pending(self.canteen)

        ord_16 = self._create_order([(self.prod_dosa, 1)], status="pending")
        promote_pending(self.canteen)
        ord_16.refresh_from_db()
        self.assertEqual(ord_16.status, "pending")

        # Complete 1 order
        first_ord = orders[0]
        first_ord.status = "prepared"
        first_ord.save()

        # Slot freed: promote pending
        promoted = promote_pending(self.canteen)
        ord_16.refresh_from_db()
        self.assertEqual(ord_16.status, "preparing")
        self.assertIn(ord_16, promoted)

    @override_settings(MAX_PREPARING=3)
    def test_7_pending_order_wait_time_includes_queue_wait(self):
        """
        Test 7: Pending order wait time includes queue wait
        With MAX_PREPARING = 3:
        3 preparing orders with finishes [2, 3, 5].
        3 pending orders arrive.
        For 3rd pending order:
        starts_in = 5, own_prep = 12, backlog = 22 -> ready_in = max(22, 5 + 12) + 1 = 23.
        """
        from Canteen_backend.wait_config import CANTEEN_CONFIGS
        CANTEEN_CONFIGS[str(self.canteen.id)] = {
            "stations": {
                "s1": {"kind": "live", "slots": 1, "minutes_per_unit": 2},
                "s2": {"kind": "live", "slots": 1, "minutes_per_unit": 3},
                "s3": {"kind": "live", "slots": 1, "minutes_per_unit": 5},
                "dosa_station": {"kind": "live", "slots": 1, "minutes_per_unit": 2},
            },
            "items": {
                "P_S1": "s1",
                "P_S2": "s2",
                "P_S3": "s3",
                "TEST_DOSA": "dosa_station",
            },
            "default_station": "dosa_station",
        }

        # 3 preparing orders on separate stations to get initial slot finish times [2, 3, 5]
        p_prod1 = Product.objects.create(product_code="P_S1", name="P1", price=10, type="Veg", canteen=self.canteen)
        p_prod2 = Product.objects.create(product_code="P_S2", name="P2", price=10, type="Veg", canteen=self.canteen)
        p_prod3 = Product.objects.create(product_code="P_S3", name="P3", price=10, type="Veg", canteen=self.canteen)

        self._create_order([(p_prod1, 1)], status="preparing") # finishes at 2
        self._create_order([(p_prod2, 1)], status="preparing") # finishes at 3
        self._create_order([(p_prod3, 1)], status="preparing") # finishes at 5

        # 3 pending orders
        # Pending 1 takes slot freeing at 2, orders 3 dosas (prep 6 -> slot becomes 8)
        self._create_order([(self.prod_dosa, 3)], status="pending")
        # Pending 2 takes slot freeing at 3, orders 2 dosas (prep 4 -> slot becomes 7)
        self._create_order([(self.prod_dosa, 2)], status="pending")
        # Pending 3 takes slot freeing at 5 (min of 8, 7, 5 = 5)
        # Orders 6 dosas: own_prep = 12.
        # Ahead dosas at dosa_station = 3 + 2 = 5. Total backlog = (5 + 6) * 2 = 22.
        ord_pending_3 = self._create_order([(self.prod_dosa, 6)], status="pending")

        tl = canteen_timeline(self.canteen.id)
        entry = tl[ord_pending_3.id]
        self.assertEqual(entry["queue_position"], 3)
        self.assertEqual(entry["starts_in_minutes"], 5)
        self.assertEqual(entry["wait_minutes"], 23)

        # Verify serializer output
        ser = OrderSerializer(ord_pending_3)
        self.assertEqual(ser.data["queue_position"], 3)
        self.assertEqual(ser.data["starts_in_minutes"], 5)
        self.assertEqual(ser.data["wait_minutes"], 23)
        self.assertIsNotNone(ser.data["expected_delivery_time"])


class StaffPriorityOrderFlowTests(TestCase):
    def setUp(self):
        self.staff_group, _ = Group.objects.get_or_create(name="Staff")
        self.student_a = User.objects.create_user(username="student_a", password="password")
        self.student_b = User.objects.create_user(username="student_b", password="password")
        self.staff_c = User.objects.create_user(username="staff_c", password="password")
        self.staff_d = User.objects.create_user(username="staff_d", password="password")

        UserProfile.objects.create(user=self.student_a, role="user")
        UserProfile.objects.create(user=self.student_b, role="user")
        UserProfile.objects.create(user=self.staff_c, role="staff")
        UserProfile.objects.create(user=self.staff_d, role="staff")

        self.canteen = Canteen.objects.create(
            id=uuid.uuid4(),
            name="Main Canteen",
            location="Campus"
        )
        self.prod_live = Product.objects.create(
            product_code="TEST_LIVE_STAFF",
            name="Staff Dosa",
            price=50.0,
            type="Veg",
            canteen=self.canteen
        )
        self.prod_dosa = Product.objects.create(
            product_code="TEST_DOSA",
            name="Masala Dosa",
            price=50.0,
            type="Veg",
            canteen=self.canteen
        )
        self.prod_juice = Product.objects.create(
            product_code="TEST_JUICE",
            name="Grape Juice",
            price=40.0,
            type="Beverages",
            canteen=self.canteen
        )
        self.prod_biryani = Product.objects.create(
            product_code="TEST_BIRYANI",
            name="Egg Biryani",
            price=120.0,
            type="Non-Veg",
            canteen=self.canteen
        )
        self.prod_icecream = Product.objects.create(
            product_code="TEST_ICECREAM",
            name="Vanilla Ice Cream",
            price=30.0,
            type="Snacks",
            canteen=self.canteen
        )
        self.prod_cooldrink = Product.objects.create(
            product_code="TEST_COOLDRINK",
            name="Cool Drink",
            price=25.0,
            type="Beverages",
            canteen=self.canteen
        )

        Menu.objects.create(canteen=self.canteen, product=self.prod_live, stock=50, is_active=True)
        Menu.objects.create(canteen=self.canteen, product=self.prod_dosa, stock=50, is_active=True)
        Menu.objects.create(canteen=self.canteen, product=self.prod_juice, stock=50, is_active=True)
        Menu.objects.create(canteen=self.canteen, product=self.prod_biryani, stock=50, is_active=True)
        Menu.objects.create(canteen=self.canteen, product=self.prod_icecream, stock=50, is_active=True)
        Menu.objects.create(canteen=self.canteen, product=self.prod_cooldrink, stock=50, is_active=True)

        self.base_time = timezone.now()

    def _create_order(self, user, minutes_offset=0, canteen=None, status="pending", items=None):
        target_canteen = canteen or self.canteen
        ord = Order.objects.create(
            user=user,
            canteen=target_canteen,
            status=status,
            total_price=50.0
        )
        if items:
            for prod, qty in items:
                OrderItem.objects.create(order=ord, product=prod, quantity=qty, price=prod.price)
        else:
            OrderItem.objects.create(order=ord, product=self.prod_live, quantity=1, price=50.0)
        Order.objects.filter(id=ord.id).update(
            created_at=self.base_time + timedelta(minutes=minutes_offset)
        )
        ord.refresh_from_db()
        return ord

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_1_staff_express_promoted_immediately_over_cap_student_stays_pending(self):
        """
        1. Staff places an order while 15 student orders are preparing: it becomes
           'preparing' immediately and a student order that was pending stays pending.
        """
        prep_orders = [self._create_order(self.student_a, -10 + i, status="preparing") for i in range(15)]
        ord_pending_student = self._create_order(self.student_b, 0, status="pending")
        ord_staff = self._create_order(self.staff_c, 1, status="pending")

        promoted = promote_pending(self.canteen)
        ord_staff.refresh_from_db()
        ord_pending_student.refresh_from_db()

        self.assertEqual(ord_staff.status, "preparing")
        self.assertEqual(ord_pending_student.status, "pending")
        self.assertIn(ord_staff, promoted)
        self.assertNotIn(ord_pending_student, promoted)

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_2_staff_orders_count_towards_active_total(self):
        """
        2. Staff orders count towards the total: with 15 preparing including 3 staff,
           a pending student is not promoted until active_count < 15.
        """
        prep_students = [self._create_order(self.student_a, -10 + i, status="preparing") for i in range(12)]
        prep_staff = [self._create_order(self.staff_c, -5 + i, status="preparing") for i in range(3)]
        ord_student = self._create_order(self.student_b, 0, status="pending")

        promoted = promote_pending(self.canteen)
        ord_student.refresh_from_db()
        self.assertEqual(ord_student.status, "pending")
        self.assertEqual(len(promoted), 0)

        # Free 1 slot by completing one student order
        prep_students[0].status = "prepared"
        prep_students[0].save()

        promoted2 = promote_pending(self.canteen)
        ord_student.refresh_from_db()
        self.assertEqual(ord_student.status, "preparing")
        self.assertIn(ord_student, promoted2)

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_3_guardrail_5_staff_express_6th_stays_pending(self):
        """
        3. Guardrail: with 5 staff express orders preparing, a 6th staff order stays pending,
           and is promoted before any pending student when a slot frees.
        """
        prep_students = [self._create_order(self.student_a, -10 + i, status="preparing") for i in range(10)]
        prep_staff = [self._create_order(self.staff_c, -5 + i, status="preparing") for i in range(5)]

        ord_student = self._create_order(self.student_b, 0, status="pending")
        ord_staff_6 = self._create_order(self.staff_d, 1, status="pending")

        promoted = promote_pending(self.canteen)
        ord_staff_6.refresh_from_db()
        ord_student.refresh_from_db()
        self.assertEqual(ord_staff_6.status, "pending")
        self.assertEqual(ord_student.status, "pending")

        # Free a slot
        prep_students[0].status = "prepared"
        prep_students[0].save()

        promoted2 = promote_pending(self.canteen)
        ord_staff_6.refresh_from_db()
        ord_student.refresh_from_db()
        self.assertEqual(ord_staff_6.status, "preparing")
        self.assertEqual(ord_student.status, "pending")
        self.assertIn(ord_staff_6, promoted2)

    @override_settings(
        MAX_PREPARING=15,
        STAFF_EXPRESS_ENABLED=True,
        STAFF_STATION_PRIORITY=True,
        STATION_IN_PROGRESS_ALLOWANCE=True,
        STAFF_BULK_PORTIONS_FIRST=True
    )
    def test_4_bill_estimates_with_in_progress_allowance(self):
        """
        4. Bill 3 biryani, 6 dosa, 1 ice cream, 3 juice, 1 cool drink, with 5 student dosas
           and 2 student juices ahead at the stations (student orders preparing):
           - student wait_minutes = 23 (existing expectation)
           - staff wait_minutes = 15 (dosa: (1 allowance + 6) * 2 = 14, plus 1 packing; starts_in_minutes = 0)
        """
        from Canteen_backend.wait_time import estimate_order_wait
        # 5 student dosas and 2 student juices ahead preparing
        self._create_order(
            self.student_a,
            minutes_offset=-10,
            status="preparing",
            items=[(self.prod_dosa, 5), (self.prod_juice, 2)]
        )

        bill_items = [
            (self.prod_biryani, 3),
            (self.prod_dosa, 6),
            (self.prod_icecream, 1),
            (self.prod_juice, 3),
            (self.prod_cooldrink, 1),
        ]

        # Estimate for student
        est_student = estimate_order_wait(self.canteen.id, bill_items, user=self.student_b)
        self.assertEqual(est_student["wait_minutes"], 23)

        # Estimate for staff
        est_staff = estimate_order_wait(self.canteen.id, bill_items, user=self.staff_c)
        self.assertEqual(est_staff["wait_minutes"], 15)
        self.assertEqual(est_staff["starts_in_minutes"], 0)

        # Confirm via canteen_timeline as well
        ord_staff = self._create_order(self.staff_c, minutes_offset=0, status="preparing", items=bill_items)
        tl = canteen_timeline(self.canteen.id)
        self.assertEqual(tl[ord_staff.id]["wait_minutes"], 15)
        self.assertEqual(tl[ord_staff.id]["starts_in_minutes"], 0)

    @override_settings(
        MAX_PREPARING=15,
        STAFF_EXPRESS_ENABLED=True,
        STAFF_STATION_PRIORITY=True,
        STATION_IN_PROGRESS_ALLOWANCE=True,
        STAFF_BULK_PORTIONS_FIRST=True
    )
    def test_5_same_staff_bill_when_no_student_units_at_stations(self):
        """
        5. Same staff bill when no student units are at the stations: wait_minutes = 13.
        """
        from Canteen_backend.wait_time import estimate_order_wait
        bill_items = [
            (self.prod_biryani, 3),
            (self.prod_dosa, 6),
            (self.prod_icecream, 1),
            (self.prod_juice, 3),
            (self.prod_cooldrink, 1),
        ]

        est_staff = estimate_order_wait(self.canteen.id, bill_items, user=self.staff_c)
        self.assertEqual(est_staff["wait_minutes"], 13)
        self.assertEqual(est_staff["starts_in_minutes"], 0)

        ord_staff = self._create_order(self.staff_c, minutes_offset=0, status="preparing", items=bill_items)
        tl = canteen_timeline(self.canteen.id)
        self.assertEqual(tl[ord_staff.id]["wait_minutes"], 13)
        self.assertEqual(tl[ord_staff.id]["starts_in_minutes"], 0)

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_6_student_wait_and_starts_in_grow_when_staff_order_arrives(self):
        """
        6. A student's wait_minutes and starts_in_minutes after a staff order arrives are greater
           than or equal to before, and strictly greater for at least one student order.
        """
        # 15 preparing orders so student is pending
        for i in range(15):
            self._create_order(self.student_a, -10 + i, status="preparing", items=[(self.prod_dosa, 1)])

        ord_student = self._create_order(self.student_b, 0, status="pending", items=[(self.prod_dosa, 2)])

        tl_before = canteen_timeline(self.canteen.id)[ord_student.id]

        # Staff order arrives with express lane (placed into preparing)
        ord_staff = self._create_order(self.staff_c, 1, status="preparing", items=[(self.prod_dosa, 4)])

        tl_after = canteen_timeline(self.canteen.id)[ord_student.id]

        self.assertGreaterEqual(tl_after["wait_minutes"], tl_before["wait_minutes"])
        self.assertGreaterEqual(tl_after["starts_in_minutes"], tl_before["starts_in_minutes"])
        self.assertTrue(
            tl_after["wait_minutes"] > tl_before["wait_minutes"] or
            tl_after["starts_in_minutes"] > tl_before["starts_in_minutes"]
        )

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_7_orders_already_preparing_never_displaced(self):
        """
        7. Orders already 'preparing' are never displaced.
        """
        prep_orders = [self._create_order(self.student_a, -10 + i, status="preparing") for i in range(15)]
        prep_ids = [o.id for o in prep_orders]

        self._create_order(self.staff_c, 0, status="pending")
        promote_pending(self.canteen)

        still_prep = Order.objects.filter(id__in=prep_ids, status="preparing").count()
        self.assertEqual(still_prep, 15)

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_8_canteen_isolation(self):
        """
        8. A staff order in canteen X changes nothing in canteen Y.
        """
        canteen_y = Canteen.objects.create(id=uuid.uuid4(), name="Canteen Y", location="North")
        prod_y = Product.objects.create(
            product_code="TEST_Y_PROD",
            name="Item Y",
            price=40.0,
            type="Veg",
            canteen=canteen_y
        )
        ord_y = Order.objects.create(user=self.student_a, canteen=canteen_y, status="pending", total_price=40.0)
        OrderItem.objects.create(order=ord_y, product=prod_y, quantity=1, price=40.0)

        tl_before = canteen_timeline(canteen_y.id)[ord_y.id]

        # Create staff order in self.canteen (canteen X)
        self._create_order(self.staff_c, 0, canteen=self.canteen)

        tl_after = canteen_timeline(canteen_y.id)[ord_y.id]
        self.assertEqual(tl_before["queue_position"], tl_after["queue_position"])
        self.assertEqual(tl_before["wait_minutes"], tl_after["wait_minutes"])
        self.assertEqual(tl_before["starts_in_minutes"], tl_after["starts_in_minutes"])

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_9_quick_only_orders_behavior_unchanged(self):
        """
        9. Quick-only orders behave exactly as before.
        """
        # Fill preparing slots
        for i in range(15):
            self._create_order(self.student_a, -10 + i, status="preparing")

        quick_ord = self._create_order(
            self.student_b,
            0,
            status="pending",
            items=[(self.prod_icecream, 1), (self.prod_cooldrink, 1)]
        )
        self.assertTrue(is_order_quick_only(quick_ord, self.canteen.id))

        promote_pending(self.canteen)
        quick_ord.refresh_from_db()
        self.assertEqual(quick_ord.status, "preparing")

        tl = canteen_timeline(self.canteen.id)
        self.assertEqual(tl[quick_ord.id]["wait_minutes"], 2)
        self.assertEqual(tl[quick_ord.id]["starts_in_minutes"], 0)
        self.assertIsNone(tl[quick_ord.id]["queue_position"])

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_10_promote_and_timeline_agreement(self):
        """
        10. promote_pending and canteen_timeline agree on which orders are staff-express and on ordering.
        """
        # 15 preparing orders so cap is reached
        for i in range(15):
            self._create_order(self.student_a, -20 + i, status="preparing")

        ord_stu1 = self._create_order(self.student_a, 0, status="pending")
        ord_staff = self._create_order(self.staff_c, 1, status="pending")
        ord_stu2 = self._create_order(self.student_b, 2, status="pending")

        tl = canteen_timeline(self.canteen.id)
        # Staff is express admitted
        self.assertEqual(tl[ord_staff.id]["starts_in_minutes"], 0)
        self.assertIsNone(tl[ord_staff.id]["queue_position"])
        # Students are in queue
        self.assertEqual(tl[ord_stu1.id]["queue_position"], 1)
        self.assertEqual(tl[ord_stu2.id]["queue_position"], 2)

        # promote_pending promotes staff first past cap
        promoted = promote_pending(self.canteen)
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0].id, ord_staff.id)

    @override_settings(MAX_PREPARING=15, STAFF_MAX_EXPRESS=5, STAFF_EXPRESS_ENABLED=True)
    def test_11_query_count_does_not_grow_with_orders(self):
        """
        11. The orders endpoint query count does not grow with the number of orders (no N+1).
        """
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        factory = APIRequestFactory()

        # Batch 1: 3 orders
        [self._create_order(self.student_a, i) for i in range(3)]
        req1 = factory.get(f"/api/orders/pending/?canteen_id={self.canteen.id}")
        force_authenticate(req1, user=self.staff_c)

        with CaptureQueriesContext(connection) as ctx1:
            resp1 = orders_by_status(req1, status="pending")
        count_3 = len(ctx1)

        # Batch 2: Add 7 more orders (total 10 orders)
        [self._create_order(self.staff_d, i + 10) for i in range(7)]
        req2 = factory.get(f"/api/orders/pending/?canteen_id={self.canteen.id}")
        force_authenticate(req2, user=self.staff_c)

        with CaptureQueriesContext(connection) as ctx2:
            resp2 = orders_by_status(req2, status="pending")
        count_10 = len(ctx2)

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(count_3, count_10)

    @override_settings(
        MAX_PREPARING=15,
        STAFF_EXPRESS_ENABLED=False,
        STAFF_STATION_PRIORITY=False,
        STAFF_CREDIT_MINUTES=8
    )
    def test_12_express_disabled_reproduces_previous_behaviour(self):
        """
        12. STAFF_EXPRESS_ENABLED = False and STAFF_STATION_PRIORITY = False reproduce
            the previous behaviour (8-minute bounded credit, no cap skipping).
        """
        prep_orders = [self._create_order(self.student_a, -10 + i, status="preparing") for i in range(15)]

        ord_stu = self._create_order(self.student_a, 0)
        ord_staff_late = self._create_order(self.staff_c, 9)  # 9 min later -> eff 12:01 vs student 12:00

        # No cap skip: when 15 are preparing, staff cannot skip cap
        promoted = promote_pending(self.canteen)
        self.assertEqual(len(promoted), 0)

        # Free 1 slot
        prep_orders[0].status = "prepared"
        prep_orders[0].save()

        # Student placed 9 min earlier beats staff placed 9 min later (exceeds 8 min credit)
        promoted2 = promote_pending(self.canteen)
        self.assertEqual(len(promoted2), 1)
        self.assertEqual(promoted2[0].id, ord_stu.id)

    @override_settings(MAX_PREPARING=15, STAFF_CREDIT_MINUTES=8, STAFF_EXPRESS_ENABLED=False)
    def test_role_staff_not_in_group_is_treated_as_staff(self):
        """
        A user with role 'staff' and NOT in the group is treated as staff.
        """
        u_staff = User.objects.create_user(username="solo_staff", password="password")
        UserProfile.objects.create(user=u_staff, role="staff")
        u_staff.groups.remove(self.staff_group)
        self.assertNotIn(self.staff_group, u_staff.groups.all())

        self.assertTrue(is_staff_member(u_staff))
        self.assertIn(u_staff.id, get_staff_user_ids([u_staff.id]))

        ord_staff = self._create_order(u_staff, 10)
        eff_time, _ = effective_time(ord_staff)
        self.assertEqual(eff_time, ord_staff.created_at - timedelta(minutes=8))
        self.assertTrue(OrderSerializer(ord_staff).data["priority"])

    @override_settings(MAX_PREPARING=15, STAFF_CREDIT_MINUTES=8, STAFF_EXPRESS_ENABLED=False)
    def test_user_in_group_with_role_user_is_not_treated_as_staff(self):
        """
        A user in the 'Staff' group with role 'user' is NOT treated as staff.
        """
        u_imposter = User.objects.create_user(username="imposter", password="password")
        UserProfile.objects.create(user=u_imposter, role="user")
        u_imposter.groups.add(self.staff_group)
        self.assertIn(self.staff_group, u_imposter.groups.all())

        self.assertFalse(is_staff_member(u_imposter))
        self.assertNotIn(u_imposter.id, get_staff_user_ids([u_imposter.id]))

        ord_imposter = self._create_order(u_imposter, 10)
        eff_time, _ = effective_time(ord_imposter)
        self.assertEqual(eff_time, ord_imposter.created_at)
        self.assertFalse(OrderSerializer(ord_imposter).data["priority"])

    @override_settings(MAX_PREPARING=15, STAFF_CREDIT_MINUTES=8, STAFF_EXPRESS_ENABLED=False)
    def test_user_with_no_userprofile_does_not_crash_and_is_non_staff(self):
        """
        A user with no UserProfile does not crash and is non-staff.
        """
        u_none = User.objects.create_user(username="noprofile", password="password")
        UserProfile.objects.filter(user=u_none).delete()
        self.assertFalse(UserProfile.objects.filter(user=u_none).exists())

        self.assertFalse(is_staff_member(u_none))
        self.assertEqual(get_staff_user_ids([u_none.id]), set())

        ord_none = self._create_order(u_none, 10)
        eff_time, _ = effective_time(ord_none)
        self.assertEqual(eff_time, ord_none.created_at)
        self.assertFalse(OrderSerializer(ord_none).data["priority"])

    @override_settings(MAX_PREPARING=15, STAFF_CREDIT_MINUTES=8)
    def test_get_staff_user_ids_50_users_executes_exactly_one_query(self):
        """
        get_staff_user_ids for 50 user ids executes exactly one query.
        """
        u_ids = []
        for i in range(50):
            u = User.objects.create_user(username=f"bulk_user_{i}", password="password")
            role = "staff" if i % 2 == 0 else "user"
            UserProfile.objects.create(user=u, role=role)
            u_ids.append(u.id)

        with self.assertNumQueries(1):
            staff_ids = get_staff_user_ids(u_ids)

        self.assertEqual(len(staff_ids), 25)

    @override_settings(MAX_PREPARING=15, STAFF_CREDIT_MINUTES=8)
    def test_sync_staff_group_command_dry_run_and_execution(self):
        """
        The sync_staff_group command in --dry-run changes nothing; a real run fixes a
        mismatched group and a second run reports no changes.
        """
        from io import StringIO

        u_staff_mismatch = User.objects.create_user(username="mismatch_staff", password="password")
        UserProfile.objects.create(user=u_staff_mismatch, role="staff")
        u_staff_mismatch.groups.remove(self.staff_group)

        u_user_mismatch = User.objects.create_user(username="mismatch_user", password="password")
        UserProfile.objects.create(user=u_user_mismatch, role="user")
        u_user_mismatch.groups.add(self.staff_group)

        # 1. Dry run
        out_dry = StringIO()
        call_command("sync_staff_group", dry_run=True, stdout=out_dry)
        self.assertNotIn(self.staff_group, u_staff_mismatch.groups.all())
        self.assertIn(self.staff_group, u_user_mismatch.groups.all())

        # 2. Real run
        out_real = StringIO()
        call_command("sync_staff_group", stdout=out_real)
        self.assertIn(self.staff_group, u_staff_mismatch.groups.all())
        self.assertNotIn(self.staff_group, u_user_mismatch.groups.all())

        # 3. Second run reports no changes
        out_second = StringIO()
        call_command("sync_staff_group", stdout=out_second)
        self.assertIn("already fully in sync", out_second.getvalue())
