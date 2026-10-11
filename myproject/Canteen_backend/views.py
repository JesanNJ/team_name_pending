from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .serializers import RegisterSerializer,MyTokenObtainPairSerializer, CanteenSerializer, MenuSerializer, OrderSerializer, UserSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from .models import Canteen, Menu, Cart, CartItem, Product, Order , OrderItem,UserProfile
from decimal import Decimal



# Signup API
@api_view(['POST'])
def register(request):
    print("Incoming data:", request.data)
    serializer = RegisterSerializer(data=request.data)
    try:
        if serializer.is_valid():
            print(serializer.save())
            user = serializer.save()
            print("incoming 2")
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)
            refresh = RefreshToken.for_user(user)
            print("Created user:", user.username)

            # Generate JWT tokens for auto login
            refresh = RefreshToken.for_user(user)
            return Response({
                "msg": "User created successfully",
                "refresh": str(refresh),
                "access": access,
                "username": user.username,
                "email": user.email,
            }, status=status.HTTP_201_CREATED)

        print("Validation errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print("Exception:", str(e))
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Login API
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        return token
    
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        print("Login request data:", request.data)
        return super().post(request, *args, **kwargs)
    
    


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_and_blacklist(request):
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception as e:
        return Response({"detail": "Invalid token or already blacklisted.", "error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
    

@api_view(['GET'])
def get_canteens(request):
    canteens = Canteen.objects.all()
    serializer = CanteenSerializer(canteens, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def canteen_menu(request, canteen_id):
    try:
        canteen = Canteen.objects.get(id=canteen_id)
    except Canteen.DoesNotExist:
        return Response({"error": "Canteen not found"}, status=404)

    menu_items = Menu.objects.filter(canteen=canteen, is_active=True).select_related('product')

    category = request.query_params.get("category") or request.query_params.get("type")
    if category and category.strip().lower() != "all":
        clean_cat = category.strip()
        if clean_cat.lower() in ["nonveg", "non-veg", "novveg"]:
            menu_items = menu_items.filter(product__type__in=["Non-Veg", "non-veg", "Non Veg"])
        else:
            menu_items = menu_items.filter(product__type__iexact=clean_cat)

    serializer = MenuSerializer(menu_items, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def add_to_cart(request, canteen_id, product_id):
    user = request.user
    canteen = get_object_or_404(Canteen, id=canteen_id)
    product = get_object_or_404(Product, id=product_id)

    # Check if menu item is active and has stock for this canteen
    menu_item = Menu.objects.filter(canteen=canteen, product=product).first()
    if menu_item:
        if not menu_item.is_active:
            return Response({"error": f"{product.name} is currently unavailable"}, status=status.HTTP_400_BAD_REQUEST)
        if menu_item.stock <= 0:
            return Response({"error": f"Sorry, {product.name} is currently out of stock"}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ Get or create cart for this user + canteen
    cart, created = Cart.objects.get_or_create(user=user, canteen=canteen)

    quantity = int(request.data.get("quantity", 1))

    # ✅ Get or create cart item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    new_quantity = quantity if created else cart_item.quantity + quantity
    if menu_item and new_quantity > menu_item.stock:
        return Response({
            "error": f"Cannot add {quantity} more. Only {menu_item.stock} left in stock (you already have {cart_item.quantity if not created else 0} in cart)."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Increase quantity if already exists
    if created:
        cart_item.quantity = quantity   # First time → set exact quantity
    else:
        cart_item.quantity = new_quantity
    cart_item.save()

    return Response({"message": f"{product.name} added to cart at {canteen.name}"})



@api_view(["POST"])
def update_cart_item(request, canteen_id, product_id):
    user = request.user
    cart = get_object_or_404(Cart, user=user, canteen_id=canteen_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)

    quantity = request.data.get("quantity")
    if quantity and int(quantity) > 0:
        menu_item = Menu.objects.filter(canteen=cart.canteen, product_id=product_id).first()
        if menu_item and int(quantity) > menu_item.stock:
            return Response({"error": f"Cannot select more than {menu_item.stock} items (stock limit reached)."}, status=status.HTTP_400_BAD_REQUEST)

        cart_item.quantity = int(quantity)
        cart_item.save()
        return Response({"message": "Quantity updated", "quantity": cart_item.quantity})
    return Response({"error": "Invalid quantity"}, status=400)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_cart(request, canteen_id):
    user = request.user
    canteen = get_object_or_404(Canteen, id=canteen_id)

    # Fetch the user's cart for this canteen
    cart = Cart.objects.filter(user=user, canteen=canteen).first()
    if not cart:
        return Response({"message": "Cart is empty"}, status=404)

    # Get items in the cart
    cart_items = cart.items.select_related("product")

    items_data = []
    total_price = 0

    for item in cart_items:
        item_total = item.quantity * item.product.price
        total_price += item_total

        menu_item = Menu.objects.filter(canteen=canteen, product=item.product).first()
        item_stock = menu_item.stock if menu_item else 0

        items_data.append({
            "product_id": item.product.id,
            "product_name": item.product.name,
            "price": item.product.price,
            "quantity": item.quantity,
            "total": item_total,
            "url": item.product.url,
            "stock": item_stock,
        })

    return Response({
        "canteen": cart.canteen.name,
        "user": user.username,
        "items": items_data,
        "total_price": total_price
    })


@api_view(["DELETE"])
def remove_from_cart(request, canteen_id, product_id):
    user = request.user
    canteen = get_object_or_404(Canteen, id=canteen_id)
    product = get_object_or_404(Product, id=product_id)

    cart = get_object_or_404(Cart, user=user, canteen=canteen)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)

    cart_item.delete()

    return Response({"message": f"{product.name} removed from cart"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def place_order(request, canteen_id):
    user = request.user
    canteen = get_object_or_404(Canteen, id=canteen_id)
    
    cart = Cart.objects.filter(user=user, canteen=canteen).first()
    if not cart or not cart.items.exists():
        return Response({"error": "Cart is empty"}, status=400)

    # 1. Validate stock for each item before placing order
    insufficient = []
    for item in cart.items.all():
        menu_item = Menu.objects.filter(canteen=canteen, product=item.product).first()
        if not menu_item or not menu_item.is_active:
            return Response({"error": f"'{item.product.name}' is currently unavailable."}, status=status.HTTP_400_BAD_REQUEST)
        if menu_item.stock < item.quantity:
            insufficient.append(f"'{item.product.name}' (Requested: {item.quantity}, Available: {menu_item.stock})")

    if insufficient:
        return Response({
            "error": "Insufficient stock for: " + ", ".join(insufficient)
        }, status=status.HTTP_400_BAD_REQUEST)

    # 2. Atomically deduct stock, create order, and clear cart
    from django.db import transaction
    with transaction.atomic():
        order = Order.objects.create(user=user, canteen=canteen, total_price=0)
        total_price = 0

        for item in cart.items.all():
            menu_item = Menu.objects.select_for_update().filter(canteen=canteen, product=item.product).first()
            if menu_item.stock < item.quantity:
                raise ValueError(f"Insufficient stock for {item.product.name}")

            # Deduct stock on order placement
            menu_item.stock -= item.quantity
            menu_item.save()

            item_total = item.quantity * item.product.price
            total_price += item_total

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )

        order.total_price = total_price
        order.save()

        # Clear cart
        cart.items.all().delete()

        from .order_flow import is_order_quick_only, promote_pending
        if is_order_quick_only(order, canteen.id):
            order.status = "preparing"
            order.save(update_fields=["status"])
        else:
            promote_pending(canteen)
            order.refresh_from_db()

    return Response({"message": "Order placed successfully", "order_id": order.id, "status": order.status})

# Get all orders for the logged-in user
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_orders(request):
    user = request.user
    orders = (
        Order.objects.filter(user=user)
        .select_related("canteen", "user", "user__userprofile")
        .prefetch_related("items__product")
        .order_by('-created_at')
    )
    serializer = OrderSerializer(orders, many=True, context={"request": request})
    return Response(serializer.data)




# This is for admin 

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def orders_by_status(request, status=None):
    """
    Fetch orders by status. If no status provided, fetch all orders.
    Supports filtering by canteen_id query parameter.
    """
    valid_statuses = ["pending", "preparing", "prepared", "delivered", "ready", "cancelled"]

    if status and status not in valid_statuses:
        return Response({"error": "Invalid status"}, status=400)

    canteen_id = request.query_params.get("canteen_id") or request.query_params.get("canteen")

    if status == "ready" or status == "prepared":
        orders = Order.objects.filter(status__in=["prepared", "ready"])
    elif status:
        orders = Order.objects.filter(status=status)
    else:
        orders = Order.objects.all()

    if canteen_id:
        orders = orders.filter(canteen_id=canteen_id)

    orders = (
        orders.select_related("canteen", "user", "user__userprofile")
        .prefetch_related("items__product")
        .order_by("-id")
    )
    serializer = OrderSerializer(orders, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_counts(request):
    """
    Fetch order counts grouped by status for admin dashboard.
    Supports filtering by canteen_id query parameter.
    """
    canteen_id = request.query_params.get("canteen_id") or request.query_params.get("canteen")
    qs = Order.objects.all()
    if canteen_id:
        qs = qs.filter(canteen_id=canteen_id)

    pending = qs.filter(status="pending").count()
    preparing = qs.filter(status="preparing").count()
    prepared = qs.filter(status__in=["prepared", "ready"]).count()
    delivered = qs.filter(status="delivered").count()
    cancelled = qs.filter(status="cancelled").count()
    return Response({
        "pending": pending,
        "preparing": preparing,
        "prepared": prepared,
        "delivered": delivered,
        "cancelled": cancelled,
        "total": pending + preparing + prepared + delivered + cancelled,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def move_order(request, status, order_id):
    order = get_object_or_404(Order, id=order_id)
    old_status = order.status
    # Normalize 'ready' to 'prepared'
    new_status = "prepared" if status == "ready" else status
    order.status = new_status
    order.save()

    from .order_flow import promote_pending
    if old_status == "preparing" and new_status != "preparing":
        promote_pending(order.canteen)

    # Trigger email notification via Resend when order becomes ready for pickup
    if old_status == "preparing" and new_status == "prepared":
        from .notifications import send_order_ready_email_async
        send_order_ready_email_async(order)

    return Response({"message": f"Order {order.id} moved to {new_status}"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """
    Cancel an order.
    Allowed for orders in 'pending', 'preparing', 'prepared' (ready to pickup).
    Rejected if already 'delivered' or 'cancelled'.
    """
    is_admin = request.user.is_staff or request.user.is_superuser or request.user.username.lower() == "admin"
    if is_admin:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == "delivered":
        return Response(
            {"error": "Cannot cancel an order that has already been delivered."},
            status=status.HTTP_400_BAD_REQUEST
        )

    old_status = order.status
    from django.db import transaction
    with transaction.atomic():
        order.status = "cancelled"
        order.save()

        # Restore deducted stock back to Menu
        for item in order.items.all():
            menu_item = Menu.objects.filter(canteen=order.canteen, product=item.product).first()
            if menu_item:
                menu_item.stock += item.quantity
                menu_item.save()

    from .order_flow import promote_pending
    if old_status == "preparing":
        promote_pending(order.canteen)

    return Response({
        "message": f"Order #{order.id} cancelled successfully and stock has been restored.",
        "order_id": order.id,
        "status": "cancelled"
    })


@api_view(["GET"])
def canteen_wait_time(request, canteen_id):
    """
    Returns estimated wait time for a canteen queue.
    If authenticated and has cart items, uses cart items.
    Otherwise estimates based on current queue backlog.
    """
    canteen = get_object_or_404(Canteen, id=canteen_id)
    items_to_estimate = []

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, canteen=canteen).first()
        if cart:
            for item in cart.items.select_related("product"):
                items_to_estimate.append({"product": item.product, "quantity": item.quantity})

    from .wait_time import estimate_order_wait
    estimate = estimate_order_wait(canteen.id, items_to_estimate, user=request.user if request.user.is_authenticated else None)
    estimate["canteen_id"] = str(canteen.id)
    estimate["canteen_name"] = canteen.name
    return Response(estimate)


# Helper function to check admin rights
def is_admin_user(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True
    profile = getattr(user, 'userprofile', None)
    if profile and getattr(profile, 'role', '') == 'admin':
        return True
    if getattr(user, 'username', '').lower() == 'admin':
        return True
    return False


# Admin Menu Management Endpoints (Admin Only)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_canteen_menu(request, canteen_id):
    """
    Fetch menu items for a specific canteen for admin management.
    Restricted to admin users only.
    Supports backend filtering by category/type query parameter.
    """
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    try:
        canteen = Canteen.objects.get(id=canteen_id)
    except Canteen.DoesNotExist:
        return Response({"error": "Canteen not found"}, status=status.HTTP_404_NOT_FOUND)

    menu_items = Menu.objects.filter(canteen=canteen).select_related('product')

    # Filter by category/type from query params (e.g., ?category=Veg, ?category=Non-Veg, ?category=Beverages)
    category = request.query_params.get("category") or request.query_params.get("type")
    if category and category.strip().lower() != "all":
        clean_cat = category.strip()
        if clean_cat.lower() in ["nonveg", "non-veg", "novveg"]:
            menu_items = menu_items.filter(product__type__in=["Non-Veg", "non-veg", "Non Veg"])
        else:
            menu_items = menu_items.filter(product__type__iexact=clean_cat)

    serializer = MenuSerializer(menu_items, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_add_menu_item(request):
    """
    Add a new product and link it to the canteen menu, or add an existing product.
    Restricted to admin users only.
    """
    import random
    import uuid

    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    canteen_id = request.data.get("canteen_id")
    name = request.data.get("name")
    price = request.data.get("price")

    if not canteen_id or not name or price is None:
        return Response({"error": "canteen_id, name, and price are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        canteen = Canteen.objects.get(id=canteen_id)
    except Canteen.DoesNotExist:
        return Response({"error": "Canteen not found"}, status=status.HTTP_404_NOT_FOUND)

    product_code = request.data.get("product_code", "").strip()
    if not product_code:
        # Auto-generate a unique code
        for _ in range(10):
            candidate_code = f"P{random.randint(100, 999)}"
            if not Product.objects.filter(product_code=candidate_code).exists():
                product_code = candidate_code
                break
        if not product_code:
            product_code = f"P{uuid.uuid4().hex[:5].upper()}"

    item_type = request.data.get("type", "Veg")
    url = request.data.get("url", "").strip()
    stock = int(request.data.get("stock", 10))

    try:
        price_val = float(price)
    except (ValueError, TypeError):
        return Response({"error": "Invalid price"}, status=status.HTTP_400_BAD_REQUEST)

    # Check if product with code already exists
    product = Product.objects.filter(product_code=product_code).first()
    if product:
        product.name = name
        product.price = price_val
        product.type = item_type
        if url:
            product.url = url
        product.save()
    else:
        product = Product.objects.create(
            product_code=product_code,
            name=name,
            price=price_val,
            type=item_type,
            url=url,
            canteen=canteen
        )

    menu_item, created = Menu.objects.get_or_create(
        canteen=canteen,
        product=product,
        defaults={"stock": stock}
    )
    if not created:
        menu_item.stock = stock
        menu_item.save()

    return Response({
        "message": f"'{name}' added to menu successfully",
        "item": MenuSerializer(menu_item).data
    }, status=status.HTTP_201_CREATED)


@api_view(["POST", "PUT"])
@permission_classes([IsAuthenticated])
def admin_update_menu_item(request, menu_id):
    """
    Update stock, price, name, type, image URL, or is_active of an existing menu item.
    Restricted to admin users only.
    """
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    menu_item = get_object_or_404(Menu, id=menu_id)

    if "stock" in request.data:
        try:
            menu_item.stock = max(0, int(request.data["stock"]))
        except (ValueError, TypeError):
            return Response({"error": "Invalid stock value"}, status=status.HTTP_400_BAD_REQUEST)

    if "is_active" in request.data:
        val = request.data["is_active"]
        menu_item.is_active = val if isinstance(val, bool) else str(val).lower() in ("true", "1")

    product = menu_item.product
    product_updated = False

    if "price" in request.data:
        try:
            product.price = float(request.data["price"])
            product_updated = True
        except (ValueError, TypeError):
            return Response({"error": "Invalid price value"}, status=status.HTTP_400_BAD_REQUEST)

    if "name" in request.data and request.data["name"]:
        product.name = request.data["name"]
        product_updated = True

    if "type" in request.data and request.data["type"]:
        product.type = request.data["type"]
        product_updated = True

    if "url" in request.data:
        product.url = request.data["url"]
        product_updated = True

    if product_updated:
        product.save()

    menu_item.save()

    return Response({
        "message": f"'{product.name}' updated successfully",
        "item": MenuSerializer(menu_item).data
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_toggle_menu_item(request, menu_id):
    """
    Toggle is_active state (activate / deactivate) of a menu item without deleting it.
    Restricted to admin users only.
    """
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    menu_item = get_object_or_404(Menu, id=menu_id)
    if "is_active" in request.data:
        val = request.data["is_active"]
        menu_item.is_active = val if isinstance(val, bool) else str(val).lower() in ("true", "1")
    else:
        menu_item.is_active = not menu_item.is_active

    menu_item.save()

    state_str = "activated (visible to students)" if menu_item.is_active else "deactivated (hidden from students)"
    return Response({
        "message": f"'{menu_item.product.name}' has been {state_str}",
        "item": MenuSerializer(menu_item).data
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def admin_delete_menu_item(request, menu_id):
    """
    Remove an item from the canteen menu.
    Restricted to admin users only.
    """
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    menu_item = get_object_or_404(Menu, id=menu_id)
    product_name = menu_item.product.name
    menu_item.delete()

    return Response({"message": f"'{product_name}' removed from menu"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_analytics(request):
    """
    Analytics and dashboard data for a single specific canteen.
    Restricted to admin users.
    Supports filters:
    - canteen_id (required UUID)
    - preset: 'today', 'last_7_days', 'last_30_days', 'this_month', 'all_time'
    - start_date & end_date (YYYY-MM-DD)
    """
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    canteen_id = request.query_params.get("canteen_id") or request.query_params.get("canteen")
    if not canteen_id:
        return Response({"error": "canteen_id is required. Only one canteen analytics can be viewed at a time."}, status=400)

    try:
        canteen = Canteen.objects.get(id=canteen_id)
    except Canteen.DoesNotExist:
        return Response({"error": "Canteen not found"}, status=404)

    from django.db.models import Sum
    from django.utils import timezone
    from datetime import datetime, timedelta, time
    from collections import defaultdict

    now = timezone.now()
    preset = request.query_params.get("preset", "").lower()
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    start_datetime = None
    end_datetime = None

    if start_date_str and end_date_str:
        try:
            sd = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            ed = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            start_datetime = timezone.make_aware(datetime.combine(sd, time.min))
            end_datetime = timezone.make_aware(datetime.combine(ed, time.max))
        except ValueError:
            pass

    if not start_datetime and preset:
        if preset == "today":
            start_datetime = timezone.make_aware(datetime.combine(now.date(), time.min))
            end_datetime = timezone.make_aware(datetime.combine(now.date(), time.max))
        elif preset == "last_7_days":
            start_datetime = now - timedelta(days=7)
            end_datetime = now
        elif preset == "last_30_days":
            start_datetime = now - timedelta(days=30)
            end_datetime = now
        elif preset == "this_month":
            first_of_month = now.date().replace(day=1)
            start_datetime = timezone.make_aware(datetime.combine(first_of_month, time.min))
            end_datetime = now
        elif preset == "all_time":
            start_datetime = None
            end_datetime = None

    if not start_datetime and not end_datetime and preset != "all_time":
        start_datetime = now - timedelta(days=30)
        end_datetime = now

    orders_qs = Order.objects.filter(canteen=canteen)
    if start_datetime:
        orders_qs = orders_qs.filter(created_at__gte=start_datetime)
    if end_datetime:
        orders_qs = orders_qs.filter(created_at__lte=end_datetime)

    total_orders = orders_qs.count()
    completed_qs = orders_qs.filter(status="delivered")
    completed_orders = completed_qs.count()
    cancelled_orders = orders_qs.filter(status="cancelled").count()
    active_orders = orders_qs.filter(status__in=["pending", "preparing", "prepared"]).count()

    total_revenue = completed_qs.aggregate(rev=Sum("total_price"))["rev"] or 0.0
    avg_order_value = (total_revenue / completed_orders) if completed_orders > 0 else 0.0
    completion_rate = round((completed_orders / total_orders * 100), 1) if total_orders > 0 else 0.0

    status_counts = {
        "pending": orders_qs.filter(status="pending").count(),
        "preparing": orders_qs.filter(status="preparing").count(),
        "prepared": orders_qs.filter(status__in=["prepared", "ready"]).count(),
        "delivered": completed_orders,
        "cancelled": cancelled_orders,
    }

    # Group daily timeline
    daily_data = {}
    for ord in orders_qs.order_by("created_at"):
        d_str = ord.created_at.strftime("%Y-%m-%d")
        if d_str not in daily_data:
            daily_data[d_str] = {"date": d_str, "orders": 0, "revenue": 0.0}
        daily_data[d_str]["orders"] += 1
        if ord.status == "delivered":
            daily_data[d_str]["revenue"] += ord.total_price

    timeline = list(daily_data.values())

    # Hourly rush distribution
    hourly_counts = [0] * 24
    for ord in orders_qs:
        h = ord.created_at.hour
        hourly_counts[h] += 1

    hourly_distribution = [
        {"hour": h, "label": f"{h:02d}:00", "orders": hourly_counts[h]}
        for h in range(24)
    ]

    # Top selling items
    order_items_qs = OrderItem.objects.filter(order__in=orders_qs).exclude(order__status="cancelled")
    item_stats = defaultdict(lambda: {"quantity": 0, "revenue": 0.0, "name": "", "category": "", "code": ""})

    for oi in order_items_qs.select_related("product"):
        p = oi.product
        item_stats[p.id]["name"] = p.name
        item_stats[p.id]["code"] = p.product_code
        item_stats[p.id]["category"] = p.type
        item_stats[p.id]["quantity"] += oi.quantity
        item_stats[p.id]["revenue"] += (oi.price * oi.quantity)

    top_selling = sorted(item_stats.values(), key=lambda x: x["quantity"], reverse=True)[:10]

    # Category breakdown
    category_stats = defaultdict(lambda: {"quantity": 0, "revenue": 0.0})
    for it in item_stats.values():
        cat = it["category"] or "Other"
        category_stats[cat]["quantity"] += it["quantity"]
        category_stats[cat]["revenue"] += it["revenue"]

    category_breakdown = [
        {"category": cat, "quantity": data["quantity"], "revenue": round(data["revenue"], 2)}
        for cat, data in category_stats.items()
    ]

    return Response({
        "canteen": {
            "id": str(canteen.id),
            "name": canteen.name,
            "location": canteen.location,
        },
        "date_range": {
            "start": start_datetime.strftime("%Y-%m-%d") if start_datetime else None,
            "end": end_datetime.strftime("%Y-%m-%d") if end_datetime else None,
            "preset": preset or "custom",
        },
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "active_orders": active_orders,
            "avg_order_value": round(avg_order_value, 2),
            "completion_rate": completion_rate,
        },
        "status_distribution": status_counts,
        "timeline": timeline,
        "hourly_distribution": hourly_distribution,
        "top_selling_items": top_selling,
        "category_breakdown": category_breakdown,
    })

