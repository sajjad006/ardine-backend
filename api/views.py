from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Restaurant, Dish, Order, ChatSession, RatingAggregate, Review, Category, OrderItem
from .serializers import RestaurantSerializer, DishSerializer, OrderSerializer, RatingAggregateSerializer, ReviewSerializer, CategorySerializer
from .permissions import IsRestaurantOwner
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Case, When, Value, IntegerField
from rest_framework.views import APIView
from api.retrieval import retrieve_menu_items
from api.llm import generate_response
import json
from rest_framework.permissions import AllowAny
from datetime import timedelta
from django.db.models import Sum
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.db.models import Count, F


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.select_related("restaurant").all()
    serializer_class = DishSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)  # file upload support

    # def get_permissions(self):
    #     # safe methods: anyoneF
    #     if self.request.method in permissions.SAFE_METHODS:
    #         return [permissions.AllowAny()]
    #     return [permissions.IsAuthenticated()]

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

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.filter(restaurant__owner=user)

        # Define your custom order preference
        status_order = Case(
            When(status="pending", then=Value(1)),
            When(status="accepted", then=Value(2)),
            When(status="preparing", then=Value(3)),
            When(status="served", then=Value(4)),
            When(status="cancelled", then=Value(5)),
            default=Value(6),
            output_field=IntegerField(),
        )

        # Apply custom ordering (pending → accepted → preparing → served → cancelled)
        queryset = queryset.annotate(
            status_order=status_order
        ).order_by("status_order", "-created_at")

        return queryset

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().select_related("restaurant", "dish")
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        dish_id = self.request.query_params.get("dish")
        restaurant_id = self.request.query_params.get("restaurant")
        qs = self.queryset
        if dish_id:
            qs = qs.filter(dish_id=dish_id)
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)
        return qs.order_by("-created_at")


class RatingAggregateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RatingAggregate.objects.all().select_related("restaurant", "dish")
    serializer_class = RatingAggregateSerializer
    permission_classes = [AllowAny]

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().select_related("restaurant")
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
            queryset = super().get_queryset()
            restaurant_id = self.request.query_params.get("restaurant")
            if restaurant_id:
                queryset = queryset.filter(restaurant_id=restaurant_id)
            return queryset.order_by("order_priority")

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_restaurant(request):
    try:
        restaurant = Restaurant.objects.get(owner=request.user)
        serializer = RestaurantSerializer(restaurant, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Restaurant.DoesNotExist:
        return Response(
            {"detail": "No restaurant found for this owner."},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def owner_dashboard_summary(request):
    user = request.user
    restaurant = user.restaurants.first()
    if not restaurant:
        return Response({"detail":"No restaurant"}, status=404)

    now = timezone.now()
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_24 = now - timedelta(hours=24)

    sales_today = Order.objects.filter(restaurant=restaurant, created_at__gte=start_day).aggregate(Sum('total'))['total__sum'] or 0
    orders_today = Order.objects.filter(restaurant=restaurant, created_at__gte=start_day).count()
    pending_count = Order.objects.filter(restaurant=restaurant, status='pending').count()
    new_24 = Order.objects.filter(restaurant=restaurant, created_at__gte=last_24).count()

    return Response({
        "sales_today": sales_today,
        "orders_today": orders_today,
        "pending": pending_count,
        "new_last_24h": new_24,
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales_trend(request):
    days = int(request.query_params.get('days', 7))
    user = request.user
    restaurant = user.restaurants.first()
    start = timezone.now().date() - timedelta(days=days-1)

    qs = (Order.objects.filter(restaurant=restaurant, created_at__date__gte=start)
          .annotate(day=TruncDate('created_at'))
          .values('day')
          .annotate(total=Sum('total'))
          .order_by('day'))
    # normalize to include missing days client-side or server-side
    return Response(list(qs))

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def orders_by_status(request):
    user = request.user
    restaurant = user.restaurants.first()
    qs = Order.objects.filter(restaurant=restaurant).values('status').annotate(count=Count('id'))
    return Response(list(qs))

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def top_dishes(request):
    days = int(request.query_params.get('days', 30))
    limit = int(request.query_params.get('limit', 6))
    restaurant = request.user.restaurants.first()
    since = timezone.now() - timedelta(days=days)
    # join OrderItem -> Order -> Restaurant
    qs = (OrderItem.objects.filter(order__restaurant=restaurant, order__created_at__gte=since)
          .values('dish', 'name')
          .annotate(total_qty=Sum('quantity'), total_revenue=Sum(F('price')*F('quantity')))
          .order_by('-total_qty')[:limit])
    return Response(list(qs))

class VirtualWaiterView(APIView):
    """
    POST /api/assistant/chat/
    Body:
    {
        "restaurant_id": "<uuid>",
        "user_query": "user message",
        "session_id": "<optional chat session id>"
    }

    Returns structured chat response with context, intent, and updated cart.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            restaurant_id = request.data.get("restaurant_id")
            user_query = request.data.get("user_query")
            session_id = request.data.get("session_id")

            if not restaurant_id or not user_query:
                return Response(
                    {"error": "Both 'restaurant_id' and 'user_query' are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 1️⃣ Create or load ChatSession
            chat_session = None
            if session_id:
                chat_session = ChatSession.objects.filter(id=session_id).first()
            if not chat_session:
                chat_session = ChatSession.objects.create(restaurant_id=restaurant_id)

            chat_history = chat_session.history
            cart = chat_session.cart

            # 2️⃣ Retrieve relevant dishes from Chroma
            retrieved_docs = retrieve_menu_items(restaurant_id, user_query, k=5)
            context_items = [
                {
                    "id": d["meta"]["item_id"],
                    "name": d["meta"]["name"],
                    "price": d["meta"]["price"],
                    "calories": d["meta"]["calories"],
                    "tags": d["meta"]["tags"]
                }
                for d in retrieved_docs
            ]
            menu_context = "\n".join([
                f"{d['meta']['name']} | ₹{d['meta']['price']} | {d['meta']['calories']} kcal | {d['meta']['tags']}"
                for d in retrieved_docs
            ])

            restaurant = Restaurant.objects.get(id=restaurant_id)

            # 3️⃣ Generate structured LLM response (intent + reply + items)
            result = generate_response(
                restaurant.name,
                menu_context,
                user_query,
                chat_history,
                cart
            )

            intent = result.get("intent", "chat")
            reply = result.get("reply", "")
            mentioned_items = [name.lower() for name in result.get("items", [])]

            # 4️⃣ Execute intents
            if intent == "add_to_cart":
                added = []
                for item in context_items:
                    if item["name"].lower() in mentioned_items:
                        cart.append({
                            "dish_id": item["id"],
                            "name": item["name"],
                            "price": item["price"],
                            "qty": 1
                        })
                        added.append(item["name"])
                if added:
                    chat_session.cart = cart
                    reply = f"✅ Added {', '.join(added)} to your cart."

            elif intent == "describe_dish":
                described = []
                for item in context_items:
                    if item["name"].lower() in mentioned_items:
                        dish = Dish.objects.filter(
                            name__iexact=item["name"],
                            restaurant_id=restaurant_id
                        ).first()
                        if dish:
                            reply = (
                                f"{dish.name}: {dish.description or 'No description available.'} "
                                f"(₹{dish.price}, {dish.calories or 'N/A'} kcal)"
                            )
                            described.append(dish.name)
                if not described and not reply:
                    reply = "Could you clarify which dish you'd like me to describe?"

            elif intent == "confirm_order":
                if not cart:
                    reply = "Your cart is empty. Please add some dishes first."
                else:
                    total = sum(float(i["price"]) * i["qty"] for i in cart)
                    order = Order.objects.create(
                        restaurant_id=restaurant_id,
                        items=cart,
                        total=total,
                        status="pending",
                        customer_name="Guest",
                        table_number="Virtual"
                    )
                    chat_session.cart = []
                    reply = f"🧾 Your order (#{order.id}) has been placed! Total ₹{total:.2f}."

            # 5️⃣ Update memory (history)
            chat_history.append({"role": "user", "content": user_query})
            chat_history.append({
                "role": "assistant",
                "content": reply,
                "intent": intent,
                "context_items": context_items
            })
            chat_session.history = chat_history
            chat_session.save()

            # 6️⃣ Final structured response
            return Response({
                "session_id": str(chat_session.id),
                "intent": intent,
                "reply": reply,
                "context_items": context_items,
                "cart": chat_session.cart,
                "history": chat_session.history[-5:]  # last few turns
            })

        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant not found."}, status=404)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

