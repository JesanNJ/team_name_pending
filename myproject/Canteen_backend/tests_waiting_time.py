import uuid
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from Canteen_backend.models import Canteen, Product, Menu, Order, OrderItem
from Canteen_backend.order_flow import promote_pending, is_order_quick_only
from Canteen_backend.wait_time import canteen_timeline
from Canteen_backend.serializers import OrderSerializer


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
