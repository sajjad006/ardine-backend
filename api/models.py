from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from django.core.validators import FileExtensionValidator
import os
from django.template.loader import render_to_string
from weasyprint import HTML
from arbackend import settings

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

    @property
    def average_rating(self):
        agg = getattr(self, "rating_summary", None)
        return round(agg.average_rating, 1) if agg and agg.average_rating is not None else 0.0

    @property
    def total_reviews(self):
        agg = getattr(self, "rating_summary", None)
        return agg.total_reviews if agg else 0

    def __str__(self):
        return self.name
    
class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="restaurant/categories/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    order_priority = models.PositiveIntegerField(default=0, help_text="Used for ordering categories in menu display")

    class Meta:
        unique_together = ("restaurant", "name")
        ordering = ["order_priority", "name"]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

class Dish(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="dishes")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to=dish_image_upload_path, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="dishes")
    model_3d = models.FileField(upload_to=dish_model_upload_path, null=True, blank=True)  # .glb/.usdz
    video = models.FileField(upload_to='dish_videos/', null=True, blank=True, validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mov', 'webm'])])
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # category = models.CharField(max_length=100, blank=True)  # e.g., 'main', 'starter'
    calories = models.IntegerField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)  # e.g. ["spicy","vegan"]
    ingredients = models.JSONField(default=list, blank=True)  # e.g. ["chicken", "tomato"]
    chef_special = models.BooleanField(default=False)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    @property
    def average_rating(self):
        agg = getattr(self, "rating_summary", None)
        return round(agg.average_rating, 1) if agg and agg.average_rating is not None else 0.0

    @property
    def total_reviews(self):
        agg = getattr(self, "rating_summary", None)
        return agg.total_reviews if agg else 0

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
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    def subtotal(self):
        return self.price * self.quantity

    def discount_amount(self):
        return (self.subtotal() * self.discount_percent) / Decimal(100)

    def taxable_amount(self):
        return self.subtotal() - self.discount_amount()

    def gst_amount(self):
        return (self.taxable_amount() * self.gst_rate) / Decimal(100)

    def total_with_gst(self):
        return self.taxable_amount() + self.gst_amount()

    def __str__(self):
        return f"{self.name} x {self.quantity}"

    def __str__(self):
        return f"{self.name} x {self.quantity}"

class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_gst = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    bill_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    bill_discount_flat = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # new field
    pdf = models.FileField(upload_to="invoices/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def generate_invoice(cls, order, bill_discount_percent=0, bill_discount_flat=0):
        items = order.items.all()

        subtotal = sum([item.subtotal() for item in items])
        item_discounts = sum([item.discount_amount() for item in items])
        item_gst = sum([item.gst_amount() for item in items])

        taxable = subtotal - item_discounts

        # Calculate both discount types
        bill_discount_percent_value = (taxable * Decimal(bill_discount_percent)) / Decimal(100)
        bill_discount_total = bill_discount_percent_value + Decimal(bill_discount_flat)

        total_discount = item_discounts + bill_discount_total
        gst_total = item_gst
        total_amount = taxable - bill_discount_total + gst_total

        invoice = cls.objects.create(
            order=order,
            subtotal=subtotal,
            total_discount=total_discount,
            total_gst=gst_total,
            total_amount=total_amount,
            bill_discount_percent=bill_discount_percent,
            bill_discount_flat=bill_discount_flat,
        )
        return invoice
    
    def generate_pdf(self):
        """Render and save the invoice as PDF."""
        context = {
            "invoice": self,
            "order": self.order,
            "items": self.order.items.all(),
            "restaurant": self.order.restaurant,
        }

        html_string = render_to_string("invoices/invoice_template.html", context)
        pdf_file_path = os.path.join(settings.MEDIA_ROOT, f"invoices/{self.id}.pdf")

        os.makedirs(os.path.dirname(pdf_file_path), exist_ok=True)
        HTML(string=html_string, base_url=settings.MEDIA_ROOT).write_pdf(pdf_file_path)

        self.pdf.name = f"invoices/{self.id}.pdf"
        self.save(update_fields=["pdf"])
        return self.pdf.url

    def __str__(self):
        return f"Invoice {self.id} for {self.order.restaurant.name}"

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    restaurant_id = models.UUIDField()
    history = models.JSONField(default=list)  # [{"role": "user", "content": "..."}]
    cart = models.JSONField(default=list)     # [{"dish_id": "...", "name": "...", "qty": 2, "price": 200}]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

def update_rating_summary(instance):
    if instance.dish:
        dish = instance.dish
        agg, _ = RatingAggregate.objects.get_or_create(dish=dish)
        summary = Review.objects.filter(dish=dish).aggregate(avg=Avg("rating"), count=Count("id"))
        agg.average_rating = summary["avg"] or 0
        agg.total_reviews = summary["count"]
        agg.save()

    elif instance.restaurant:
        restaurant = instance.restaurant
        agg, _ = RatingAggregate.objects.get_or_create(restaurant=restaurant)
        summary = Review.objects.filter(restaurant=restaurant).aggregate(avg=Avg("rating"), count=Count("id"))
        agg.average_rating = summary["avg"] or 0
        agg.total_reviews = summary["count"]
        agg.save()

class Review(models.Model):
    """
    Stores individual user reviews for either a restaurant or a dish.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")
    restaurant = models.ForeignKey("Restaurant", on_delete=models.CASCADE, related_name="reviews", null=True, blank=True)
    dish = models.ForeignKey("Dish", on_delete=models.CASCADE, related_name="reviews", null=True, blank=True)

    rating = models.PositiveSmallIntegerField(default=0)  # 1–5
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)  # e.g., verified if ordered before

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(check=models.Q(rating__gte=0) & models.Q(rating__lte=5), name="rating_range_check"),
        ]

    def __str__(self):
        target = self.dish.name if self.dish else self.restaurant.name if self.restaurant else "Unknown"
        return f"{self.user} - {target} ({self.rating}/5)"

class RatingAggregate(models.Model):
    """
    Caches average ratings for performance (reduces expensive aggregation queries).
    Automatically updated when new reviews are added.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.OneToOneField("Restaurant", on_delete=models.CASCADE, related_name="rating_summary", null=True, blank=True)
    dish = models.OneToOneField("Dish", on_delete=models.CASCADE, related_name="rating_summary", null=True, blank=True)
    average_rating = models.FloatField(default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)

    def __str__(self):
        target = self.dish.name if self.dish else self.restaurant.name
        return f"{target}: {self.average_rating:.1f}⭐ ({self.total_reviews} reviews)"


@receiver(post_save, sender=Review)
def update_rating_on_save(sender, instance, **kwargs):
    update_rating_summary(instance)


@receiver(post_delete, sender=Review)
def update_rating_on_delete(sender, instance, **kwargs):
    update_rating_summary(instance)

@receiver(post_save, sender=Order)
def create_invoice_on_served(sender, instance, **kwargs):
    if instance.status == "served" and not hasattr(instance, "invoice"):
        invoice = Invoice.generate_invoice(order=instance)
        invoice.generate_pdf()