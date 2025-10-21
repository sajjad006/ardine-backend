from django.db import models
from django.contrib.auth.models import User
import uuid

def dish_image_upload_path(instance, filename):
    return f"restaurants/{instance.restaurant.id}/images/{filename}"

def dish_model_upload_path(instance, filename):
    return f"restaurants/{instance.restaurant.id}/models/{filename}"

class Restaurant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="restaurants")
    name = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300, blank=True)
    logo = models.ImageField(upload_to="restaurant/logos/", null=True, blank=True)
    banner = models.ImageField(upload_to="restaurant/banners/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Dish(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="dishes")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to=dish_image_upload_path, null=True, blank=True)
    model_3d = models.FileField(upload_to=dish_model_upload_path, null=True, blank=True)  # .glb/.usdz
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    category = models.CharField(max_length=100, blank=True)  # e.g., 'main', 'starter'
    calories = models.IntegerField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)  # e.g. ["spicy","vegan"]
    ingredients = models.JSONField(default=list, blank=True)  # e.g. ["chicken", "tomato"]

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"

class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("preparing", "Preparing"),
        ("served", "Served"),
        ("cancelled", "Cancelled"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="orders")
    # items = models.JSONField()  # simple array of {dish_id, name, price, qty}
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    table_number = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - {self.restaurant.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    dish = models.ForeignKey(Dish, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)  # snapshot name
    price = models.DecimalField(max_digits=8, decimal_places=2)  # snapshot price
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.name} x {self.quantity}"

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    restaurant_id = models.UUIDField()
    history = models.JSONField(default=list)  # [{"role": "user", "content": "..."}]
    cart = models.JSONField(default=list)     # [{"dish_id": "...", "name": "...", "qty": 2, "price": 200}]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
