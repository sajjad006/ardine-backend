from rest_framework import serializers
from .models import Restaurant, Dish, Order, OrderItem, Category, Review, RatingAggregate
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")



# ─────────────────────────────────────────────
# DISH SERIALIZER
# ─────────────────────────────────────────────

class DishSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    model_3d = serializers.FileField(required=False, allow_null=True)

    # image_url = serializers.SerializerMethodField()
    # model_3d_url = serializers.SerializerMethodField()

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Dish
        fields = (
            "id",
            "restaurant",
            "name",
            "description",
            "price",
            "image",         # writable (upload)
            # "image_url",     # read-only (absolute URL)
            "model_3d",      # writable
            # "model_3d_url",  # read-only
            "is_active",
            "chef_special",
            "created_at",
            "category",
            "calories",
            "tags",
            "ingredients",
            "category_name",
            "average_rating",
            "total_reviews",
        )

    # def get_image_url(self, obj):
    #     request = self.context.get('request')
    #     if obj.image:
    #         if request:
    #             return request.build_absolute_uri(obj.image.url)
    #         return obj.image.url  # fallback
    #     return None

    # def get_model_3d_url(self, obj):
    #     request = self.context.get('request')
    #     if obj.model_3d:
    #         if request:
    #             return request.build_absolute_uri(obj.model_3d.url)
    #         return obj.model_3d.url  # fallback
    #     return None

class CategorySerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    dishes = DishSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "restaurant",
            "restaurant_name",
            "name",
            "description",
            "image",
            "is_active",
            "order_priority",
            "dishes",
        ]




# ─────────────────────────────────────────────
# RESTAURANT SERIALIZER
# ─────────────────────────────────────────────

class RestaurantSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    dishes = DishSerializer(many=True, read_only=True)
    logo = serializers.ImageField(required=False, allow_null=True)
    banner = serializers.ImageField(required=False, allow_null=True)

    # average_rating = serializers.ReadOnlyField(source="average_rating")
    # total_reviews = serializers.ReadOnlyField(source="total_reviews")

    class Meta:
        model = Restaurant
        fields = (
            "id",
            "owner",
            "name",
            "tagline",
            "logo",
            "banner",
            "average_rating",
            "total_reviews",
            "dishes",
        )



# ─────────────────────────────────────────────
# ORDER ITEM SERIALIZER
# Handles both "id" (from frontend) and "dish" fields
# ─────────────────────────────────────────────
class OrderItemSerializer(serializers.ModelSerializer):
    # Accept both "dish" and "id" as dish identifier
    dish = serializers.PrimaryKeyRelatedField(
        queryset=Dish.objects.all(), required=False
    )
    qty = serializers.IntegerField(required=False, write_only=True)

    # For response, include basic dish info
    dish_name = serializers.CharField(source="dish.name", read_only=True)
    dish_image = serializers.ImageField(source="dish.image", read_only=True)
    dish_category = serializers.CharField(source="dish.category", read_only=True)
    dish_model = serializers.FileField(source="dish.model_3d", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "dish",
            "name",
            "price",
            "quantity",
            "qty",
            "dish_name",
            "dish_image",
            "dish_category",
            "dish_model",
        ]
        extra_kwargs = {
            "quantity": {"required": False},
        }

    def to_internal_value(self, data):
        """
        Normalize incoming data:
        - Map 'id' → 'dish'
        - Map 'qty' → 'quantity'
        """
        if "dish" not in data and "id" in data:
            data["dish"] = data["id"]
        if "qty" in data and "quantity" not in data:
            data["quantity"] = data["qty"]
        return super().to_internal_value(data)


# ─────────────────────────────────────────────
# ORDER SERIALIZER
# ─────────────────────────────────────────────
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "restaurant",
            "total",
            "status",
            "created_at",
            "customer_name",
            "table_number",
            "items",
        ]
        read_only_fields = ["status", "created_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            dish = item_data.get("dish")
            name = item_data.get("name")
            price = item_data.get("price")
            quantity = item_data.get("quantity", 1)

            OrderItem.objects.create(
                order=order,
                dish=dish,
                name=name,
                price=price,
                quantity=quantity,
            )
        return order

    def to_representation(self, instance):
        """Custom output with restaurant info and nested items"""
        representation = super().to_representation(instance)
        representation["restaurant"] = RestaurantSerializer(
            instance.restaurant, context=self.context
        ).data
        representation["items"] = OrderItemSerializer(
            instance.items.all(), many=True, context=self.context
        ).data
        return representation


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    target_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user_name",
            "restaurant",
            "dish",
            "rating",
            "comment",
            "is_verified",
            "created_at",
            "target_name",
        ]

    def get_target_name(self, obj):
        if obj.dish:
            return obj.dish.name
        if obj.restaurant:
            return obj.restaurant.name
        return None


class RatingAggregateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingAggregate
        fields = ["average_rating", "total_reviews",]
