from rest_framework.permissions import BasePermission

class IsRestaurantOwner(BasePermission):
    """
    Allows access only to restaurant owners for object-level permission.
    """

    def has_object_permission(self, request, view, obj):
        # obj can be Restaurant or Dish where obj.restaurant.owner applies
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        if hasattr(obj, "restaurant"):
            return obj.restaurant.owner == request.user
        return False
