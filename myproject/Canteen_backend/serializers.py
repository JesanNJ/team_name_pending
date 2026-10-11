from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Canteen, Product, Menu,Order, OrderItem, UserProfile
from rest_framework import serializers



class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password = validated_data['password']
        )

        
        UserProfile.objects.create(user=user, role="user")
        return user







class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        raw_login = attrs.get("username", "") or ""
        login_input = raw_login.strip()  # frontend sends "username" field (can be username or email)
        password = attrs.get("password")

        if not login_input:
            raise serializers.ValidationError("Username or email is required")

        # Determine if input is email or username (case-insensitive)
        if "@" in login_input:
            user_obj = User.objects.filter(email__iexact=login_input).first()
            if not user_obj:
                raise serializers.ValidationError("No account found with this email")
            username = user_obj.username
        else:
            user_obj = User.objects.filter(username__iexact=login_input).first()
            if not user_obj:
                # Also try email just in case user omitted @ or entered email
                user_obj = User.objects.filter(email__iexact=login_input).first()
            if not user_obj:
                raise serializers.ValidationError("No account found with this username")
            username = user_obj.username

        # Authenticate using the exact registered username
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")

        # Generate JWT tokens
        data = super().validate({
            "username": username,
            "password": password
        })

        # Add extra info
        data["username"] = user.username
        data["email"] = user.email
        return data
    


class CanteenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Canteen
        fields = ("id", "name", "location") 


class ProductSerializer(serializers.ModelSerializer):
    canteen_name = serializers.CharField(source="canteen.name", read_only=True)

    class Meta:
        model = Product
        fields = ( "product_code", "name", "price", "type","url")

class MenuSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.FloatField(source="product.price", read_only=True)
    product_type = serializers.CharField(source="product.type", read_only=True)
    product_url = serializers.CharField(source="product.url", read_only=True)
    product_id = serializers.CharField(source='product.id',read_only=True)


    class Meta:
        model = Menu
        fields = ["id", "canteen", 'product_id', "stock", "product_code", "product_name", "product_price", "product_type", "product_url", "is_active"]



class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.FloatField(source='price', read_only=True)
    product_url = serializers.CharField(source='product.image_url', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product_name', 'product_price', 'quantity', 'product_url']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    canteen_name = serializers.CharField(source='canteen.name', read_only=True)
    wait_minutes = serializers.SerializerMethodField()
    starts_in_minutes = serializers.SerializerMethodField()
    queue_position = serializers.SerializerMethodField()
    expected_delivery_time = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'canteen', 'canteen_name', 'total_price', 'status', 'created_at', 'items',
            'wait_minutes', 'starts_in_minutes', 'queue_position', 'expected_delivery_time', 'priority'
        ]

    def _get_order_timeline(self, obj):
        if obj.status not in ["pending", "preparing"]:
            return None

        request = self.context.get("request") if getattr(self, "context", None) else None
        timelines_cache = None
        if request is not None:
            if not hasattr(request, "_canteen_timelines_cache"):
                request._canteen_timelines_cache = {}
            timelines_cache = request._canteen_timelines_cache

        canteen_id = obj.canteen_id
        if timelines_cache is not None:
            if canteen_id not in timelines_cache:
                from .wait_time import canteen_timeline
                timelines_cache[canteen_id] = canteen_timeline(canteen_id)
            timeline = timelines_cache[canteen_id]
        else:
            from .wait_time import canteen_timeline
            timeline = canteen_timeline(canteen_id)

        return timeline.get(obj.id)

    def get_wait_minutes(self, obj):
        tl = self._get_order_timeline(obj)
        return tl.get("wait_minutes") if tl else None

    def get_starts_in_minutes(self, obj):
        tl = self._get_order_timeline(obj)
        return tl.get("starts_in_minutes") if tl else None

    def get_queue_position(self, obj):
        tl = self._get_order_timeline(obj)
        return tl.get("queue_position") if tl else None

    def get_expected_delivery_time(self, obj):
        tl = self._get_order_timeline(obj)
        return tl.get("expected_delivery_time") if tl else None

    def get_priority(self, obj):
        user = getattr(obj, "user", None)
        try:
            profile = getattr(user, "userprofile", None)
            if profile is not None:
                return getattr(profile, "role", "") == "staff"
        except Exception:
            pass

        request = self.context.get("request") if getattr(self, "context", None) else None
        if request is not None:
            if not hasattr(request, "_staff_user_ids_cache") or request._staff_user_ids_cache is None:
                from .order_flow import get_staff_user_ids
                parent = getattr(self, "parent", None)
                if parent and hasattr(parent, "instance") and parent.instance:
                    u_ids = {o.user_id for o in parent.instance if getattr(o, "user_id", None)}
                else:
                    u_ids = {obj.user_id} if getattr(obj, "user_id", None) else set()
                request._staff_user_ids_cache = get_staff_user_ids(u_ids)

            return obj.user_id in request._staff_user_ids_cache

        from .order_flow import is_staff_member
        return is_staff_member(user)




# For admin

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["role"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True,source='userprofile')

    class Meta:
        model = User
        fields = ["id", "username", "email", "profile"]
