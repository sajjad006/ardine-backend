# assistant/llm.py
import os
from groq import Groq
import textwrap
from dotenv import load_dotenv
import json

load_dotenv()

# client = Groq(api_key=)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "openai/gpt-oss-20b"


def build_prompt(restaurant_name: str, menu_context: str, user_query: str, chat_history=None, cart=None) -> str:
    """
    Construct a clean, instruction-style prompt for Groq LLM.

    Args:
        restaurant_name: Name of restaurant
        menu_context: Retrieved dishes (string)
        user_query: Customer's query

    Returns:
        A formatted text prompt.
    """
    chat_log = ""
    if chat_history:
        for turn in chat_history[-5:]:
            chat_log += f"{turn['role'].capitalize()}: {turn['content']}\n"

    cart_summary = ""
    if cart:
        items = [f"{c['name']} (x{c['qty']})" for c in cart]
        cart_summary = f"Current Cart: {', '.join(items)}\n"

    prompt = f"""
        You are a friendly virtual waiter for "{restaurant_name}".
        You help customers by answering questions, giving recommendations, and managing their orders.

        Below is the recent chat, cart, and menu information. Use these carefully.

        Conversation so far:
        {chat_log}

        Items currently in cart:
        {cart_summary}

        Menu Context (from the restaurant database):
        {menu_context}

        Customer says: "{user_query}"
        
        ---
        Your task:
        Respond **strictly in JSON** following this structure:
        {{
        "intent": "<one of: chat | describe_dish | add_to_cart | remove_from_cart | update_quantity | check_cart | confirm_order | recommend_dish | ask_calories | ask_ingredients | ask_price | ask_category | restaurant_info | greet | goodbye | unknown>",
        "reply": "<your natural and friendly waiter-style response>",
        "items": ["list of dishes or menu items mentioned by the user, if any"]
        }}

        ---

        Intent Definitions (read carefully):
        - "chat": Small talk, greetings, or general non-order messages.
        - "describe_dish": User asks about details, taste, or description of a specific dish.
        - "add_to_cart": User wants to add one or more dishes to their order/cart.
        - "remove_from_cart": User wants to remove something from the cart.
        - "update_quantity": User wants to change the quantity of an existing dish in the cart.  Example: “Change my chicken biryani to 2 portions”, “Make it 3 paneer butter masalas”.
        - "check_cart": User asks to review what’s in their cart.
        - "confirm_order": User confirms or finalizes their order.
        - "recommend_dish": User asks for suggestions (e.g., “What’s good?”, “Something spicy under ₹200”, “Low calorie meals”).
        - "ask_calories": User asks about calorie or nutrition information.
        - "ask_ingredients": User asks what ingredients are in a dish.
        - "ask_price": User asks the cost or price of something.
        - "ask_category": User asks for a specific food type (e.g., starters, desserts, drinks).
        - "restaurant_info": User asks about restaurant hours, address, or contact.
        - "greet": User greets you (e.g., “Hi”, “Hello”).
        - "goodbye": User says goodbye (e.g., “Thanks”, “See you”).
        - "unknown": If you can’t classify the intent confidently.

        ---

        🧠 Rules:
        - Be concise, natural, and warm — sound like a helpful human waiter.
        - When describing dishes, mention price, calories, and key ingredients if available.
        - Always ensure the JSON is valid and contains *no* extra text or comments outside it.
        - Use `items` array to list exact dish names if they appear or are inferred from context.
        - If user asks about a “healthy”, “spicy”, “vegan”, or “low-calorie” dish → use `recommend_dish`.
        - If multiple intents apply (e.g., “Can you add the chicken soup and tell me its calories?”), choose the **main action** (e.g., add_to_cart).

        ---

        Now produce the JSON output:
    """
    return prompt.strip()




def generate_response(restaurant_name: str, menu_context: str, user_query: str, chat_session=None, cart=None) -> str:
    """
    Generate the waiter response using Groq-hosted LLM.

    Args:
        restaurant_name: Name of restaurant.
        menu_context: Retrieved menu text.
        user_query: Customer question.

    Returns:
        str: Natural waiter-style reply.
    """
    prompt = build_prompt(restaurant_name, menu_context, user_query, chat_session, cart)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful AI waiter."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=600,
    )

    text = response.choices[0].message.content.strip()

    # Try parsing model output as JSON
    try:
        result = json.loads(text)
    except Exception:
        result = {"intent": "chat", "reply": text, "items": []}

    return result



# ✅ Optional CLI test
if __name__ == "__main__":
    restaurant_name = "Spice Villa"
    sample_context = """
    Name: Grilled Chicken Salad | Price: ₹220 | Calories: 350 | Tags: non-veg, healthy, low-fat
    Name: Paneer Butter Masala | Price: ₹260 | Calories: 580 | Tags: veg, rich, spicy
    Name: Chicken Soup | Price: ₹150 | Calories: 180 | Tags: non-veg, light
    """
    user_query = "Recommend something healthy and light with chicken under 400 calories"

    print("\n Generating Virtual Waiter Response via Groq...\n")
    reply = generate_response(restaurant_name, sample_context, user_query)
    print("Waiter:", reply)
