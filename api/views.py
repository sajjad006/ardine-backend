from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Restaurant, Dish, Order
from .serializers import RestaurantSerializer, DishSerializer, OrderSerializer
from .permissions import IsRestaurantOwner
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from api.retrieval import retrieve_menu_items
from api.llm import generate_response
import json
from rest_framework.permissions import AllowAny


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.select_related("restaurant").all()
    serializer_class = DishSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)  # file upload support

    def get_permissions(self):
        # safe methods: anyone
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        # enforce restaurant ownership
        restaurant_id = self.request.data.get("restaurant")
        restaurant = None
        if restaurant_id:
            from .models import Restaurant
            restaurant = Restaurant.objects.get(id=restaurant_id)
            if restaurant.owner != self.request.user:
                raise PermissionError("Not the owner of the restaurant.")
        serializer.save()

    def get_queryset(self):
        qs = super().get_queryset()
        # optional: filter by restaurant query param
        restaurant = self.request.query_params.get("restaurant")
        if restaurant:
            qs = qs.filter(restaurant__id=restaurant)
        return qs

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.AllowAny()]  # allow customers to place orders
        return [permissions.IsAuthenticated()]


class VirtualWaiterView(APIView):
    authentication_classes = []      # Disable DRF authentication
    permission_classes = [AllowAny]  # Make endpoint public
    def post(self, request):
        try:
            restaurant_id = request.data.get("restaurant_id")
            user_query = request.data.get("user_query")

            if not restaurant_id or not user_query:
                return Response(
                    {"error": "Both 'restaurant_id' and 'user_query' are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                restaurant = Restaurant.objects.get(id=restaurant_id)
            except Restaurant.DoesNotExist:
                return Response({"error": "Restaurant not found."},
                                status=status.HTTP_404_NOT_FOUND)

            # ✅ Step 1: Retrieve relevant dishes
            retrieved_docs = retrieve_menu_items(restaurant_id, user_query, k=5)

            if not retrieved_docs:
                return Response({
                    "reply": "I'm sorry, I couldn't find matching dishes for your query.",
                    "context_items": []
                })

            # ✅ Step 2: Build context string
            menu_context = "\n".join([
                f"{d['meta']['name']} | Price: ₹{d['meta']['price']} | Calories: {d['meta']['calories']} | Tags: {d['meta']['tags']}"
                for d in retrieved_docs
            ])

            # ✅ Step 3: Generate waiter-like response using Groq LLM
            reply = generate_response(restaurant.name, menu_context, user_query)

            # ✅ Step 4: Build structured list of context items for frontend
            context_items = [
                {
                    "name": d["meta"]["name"],
                    "price": d["meta"]["price"],
                    "calories": d["meta"]["calories"],
                    "tags": d["meta"]["tags"]
                }
                for d in retrieved_docs
            ]

            # ✅ Step 5: Return response
            return Response({
                "restaurant": restaurant.name,
                "reply": reply,
                "context_items": context_items
            })

        except Exception as e:
            return Response(
                {"error": f"Unexpected error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
