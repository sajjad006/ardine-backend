from rest_framework import routers
from .views import RestaurantViewSet, DishViewSet, OrderViewSet, ReviewViewSet, RatingAggregateViewSet, CategoryViewSet
from django.urls import path, include
from api.views import VirtualWaiterView

router = routers.DefaultRouter()
router.register(r"restaurants", RestaurantViewSet)
router.register(r"dishes", DishViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"reviews", ReviewViewSet)
router.register(r"ratings", RatingAggregateViewSet)
router.register(r"categories", CategoryViewSet, basename="category")


urlpatterns = [
    path("", include(router.urls)),
    path("chat/", VirtualWaiterView.as_view(), name="virtual_waiter"),
]
