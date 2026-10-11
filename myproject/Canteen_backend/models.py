from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
import random


# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name="userprofile")
    ROLE_CHOICES = (("admin","Admin"), ("user","User"), ("staff","Staff"))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")


@receiver(post_save, sender=UserProfile)
def sync_staff_group(sender, instance, **kwargs):
    from django.contrib.auth.models import Group
    staff_group, _ = Group.objects.get_or_create(name="Staff")
    if instance.role == "staff":
        instance.user.groups.add(staff_group)
    else:
        instance.user.groups.remove(staff_group)


class Canteen(models.Model):
    id = models.UUIDField(
        primary_key=True,      # makes it the primary key
        default=uuid.uuid4,    # automatically generates a unique UUID
        editable=False
    )
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name
    

class Product(models.Model):
    product_code = models.CharField(max_length=20, unique=True)  # small varchar code
    name = models.CharField(max_length=100)
    price = models.FloatField()
    type = models.CharField(max_length=50, choices=[("Beverages", "Beverages"), ("Veg", "Veg"), ("Non-Veg", "Non-Veg"), ("Snacks", "Snacks")])
    url = models.URLField(max_length=300, blank=True)
    canteen = models.ForeignKey('Canteen', on_delete=models.CASCADE, related_name='products', null=True, blank=True,
                default=uuid.UUID('24c1a6a4-d9f9-426f-a0eb-8e30b7a86ce5'))
    

    def __str__(self):
        return f"{self.name} ({self.canteen.name})"
    

class Menu(models.Model):
    canteen = models.ForeignKey(Canteen, on_delete=models.CASCADE, related_name="menu_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="menu_entries")
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('canteen', 'product')  # One product per canteen

    def __str__(self):
        return f"{self.product.name} in {self.canteen.name} (Stock: {self.stock})"
    
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    canteen = models.ForeignKey("Canteen", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("user", "canteen")

    def __str__(self):
        return f"{self.user.username} - {self.canteen.name}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('prepared', 'Prepared / Ready to Pickup'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    canteen = models.ForeignKey('Canteen', on_delete=models.CASCADE)
    total_price = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.FloatField() 
