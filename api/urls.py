from rest_framework import routers
from .views import RestaurantViewSet, DishViewSet, OrderViewSet, ReviewViewSet, RatingAggregateViewSet, CategoryViewSet
from django.urls import path, include
from api.views import VirtualWaiterView, my_restaurant, owner_dashboard_summary, sales_trend, orders_by_status, top_dishes

router = routers.DefaultRouter()
router.register(r"restaurants", RestaurantViewSet)
router.register(r"dishes", DishViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"reviews", ReviewViewSet)
router.register(r"ratings", RatingAggregateViewSet)
router.register(r"categories", CategoryViewSet, basename="category")


urlpatterns = [
    path("", include(router.urls)),
    path("me/", my_restaurant, name="my-restaurant"),
    path("owner/dashboard/summary/", owner_dashboard_summary, name="owner-dashboard-summary"),
    path("owner/dashboard/sales-trend/", sales_trend, name="owner-dashboard-sales-trend"),
    path("owner/dashboard/orders-by-status/", orders_by_status, name="owner-dashboard-orders-status"),
    path("owner/top-dishes/", top_dishes, name="owner-top-dishes"),
    path("chat/", VirtualWaiterView.as_view(), name="virtual_waiter"),
]
