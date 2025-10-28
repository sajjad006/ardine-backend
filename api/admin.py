from django.contrib import admin
from django.utils.html import format_html
from .models import Invoice, Restaurant, Dish, Order, OrderItem, Category


# -----------------------------
# Inline for Dishes (within Restaurant)
# -----------------------------
class DishInline(admin.TabularInline):
    model = Dish
    extra = 1
    fields = ("name", "category", "price", "is_active")
    show_change_link = True


# -----------------------------
# Restaurant Admin
# -----------------------------
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "tagline", "logo_preview", "created_at")
    search_fields = ("name", "owner__username")
    list_filter = ("created_at",)
    inlines = [DishInline]
    ordering = ("name",)
    list_per_page = 20

    readonly_fields = ("created_at", "logo_preview", "banner_preview")

    fieldsets = (
        ("Basic Info", {
            "fields": ("owner", "name", "tagline")
        }),
        ("Branding", {
            "fields": ("logo", "logo_preview", "banner", "banner_preview"),
        }),
        ("Timestamps", {
            "fields": ("created_at",),
        }),
    )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:6px;"/>', obj.logo.url)
        return "—"
    logo_preview.short_description = "Logo"

    def banner_preview(self, obj):
        if obj.banner:
            return format_html('<img src="{}" width="120" height="40" style="object-fit:cover;border-radius:4px;"/>', obj.banner.url)
        return "—"
    banner_preview.short_description = "Banner"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant", "is_active", "order_priority", "image_preview")
    list_filter = ("restaurant", "is_active")
    search_fields = ("name", "restaurant__name")
    inlines = [DishInline]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="60" style="border-radius:6px;" />', obj.image.url)
        return "—"

    image_preview.short_description = "Image Preview"


# -----------------------------
# Dish Admin
# -----------------------------
@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = (
        "name", "restaurant", "category", "price",
        "calories", "is_active", "chef_special", "image_preview", "created_at", "video"
    )
    list_filter = ("restaurant", "category", "is_active")
    search_fields = ("name", "description", "tags", "ingredients")
    ordering = ("restaurant", "category", "name")
    list_editable = ("price", "is_active")
    list_per_page = 25

    readonly_fields = ("created_at", "image_preview", "model_link")

    fieldsets = (
        ("Dish Details", {
            "fields": (
                "restaurant", "name", "description",
                "category", "price", "is_active", "chef_special"
            )
        }),
        ("Media", {
            "fields": ("image", "image_preview", "model_3d", "model_link", "video"),
            "description": "Upload a food image and optionally a 3D model (.glb/.usdz)."
        }),
        ("Nutrition & Ingredients", {
            "fields": ("calories", "tags", "ingredients"),
        }),
        ("Timestamps", {
            "fields": ("created_at",),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:6px;"/>', obj.image.url)
        return "—"
    image_preview.short_description = "Image"

    def model_link(self, obj):
        if obj.model_3d:
            return format_html('<a href="{}" target="_blank">View 3D Model</a>', obj.model_3d.url)
        return "—"
    model_link.short_description = "3D Model"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("name", "price", "quantity", "dish")
    can_delete = False
    show_change_link = False



# -----------------------------
# Order Admin
# -----------------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "restaurant",
        "customer_name",
        "table_number",
        "status",
        "total",
        "created_at",
    )
    list_filter = ("status", "restaurant", "created_at")
    search_fields = ("id", "customer_name", "table_number")
    readonly_fields = ("created_at",)
    inlines = [OrderItemInline]

    fieldsets = (
        ("Order Details", {
            "fields": (
                "restaurant",
                "status",
                "total",
                "created_at",
            )
        }),
        ("Customer Info", {
            "fields": (
                "customer_name",
                "table_number",
            )
        }),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "price", "quantity", "dish", "gst_rate", "discount_percent")
    search_fields = ("order__id", "name", "dish__name")
    list_filter = ("dish__restaurant",)
    readonly_fields = ("order", "name", "price", "quantity", "dish", "gst_rate", "discount_percent")

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "subtotal", "total_discount", "total_gst", "total_amount", "created_at")
    search_fields = ("order__id",)
    readonly_fields = ("id", "order", "subtotal", "total_discount", "total_gst", "total_amount", "bill_discount_percent", "created_at")

