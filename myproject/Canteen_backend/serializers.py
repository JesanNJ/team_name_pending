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
        login_input = attrs.get("username")  # frontend sends "username"
        password = attrs.get("password")

        # Check if input is email
        if "@" in login_input:
            try:
                user_obj = User.objects.get(email=login_input)
                username = user_obj.username  # get actual username
            except User.DoesNotExist:
                raise serializers.ValidationError("No account found with this email")
        else:
            username = login_input
            try:
                user_obj = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError("No account found with this username")

        # Authenticate using the real username
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")

        data = super().validate({"username": username, "password": password})
        data["username"] = user.username
        data["email"] = user.email
        return data


    def validate(self, attrs):
        login_input = attrs.get("username")  # frontend sends "username" field
        password = attrs.get("password")

        # Determine if input is email or username
        if "@" in login_input:
            try:
                user_obj = User.objects.get(email=login_input)
                username = user_obj.username
            except User.DoesNotExist:
                raise serializers.ValidationError("No account found with this email")
        else:
            username = login_input
            try:
                user_obj = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError("No account found with this username")

        # Authenticate
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

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'canteen', 'canteen_name', 'total_price', 'status', 'created_at', 'items',
            'wait_minutes', 'starts_in_minutes', 'queue_position', 'expected_delivery_time'
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
