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
        Use the menu and conversation to assist the customer.

        Conversation so far:
        {chat_log}

        Items currently in cart:
        {cart_summary}

        Menu Context:
        {menu_context}

        Customer says: "{user_query}"

        You must respond in JSON only with this exact structure:
        {{
        "intent": "chat" | "add_to_cart" | "describe_dish" | "confirm_order",
        "reply": "your natural language response to the customer",
        "items": ["list of dishes the user mentioned or referred to, if any"]
        }}

        Rules:
        - If user asks to add something → intent = add_to_cart.
        - If user asks about a dish → intent = describe_dish.
        - If user confirms or finalizes → intent = confirm_order.
        - Otherwise → intent = chat.
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
        max_tokens=500,
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
