# assistant/llm.py
import os
from groq import Groq
import textwrap
from dotenv import load_dotenv

load_dotenv()

# client = Groq(api_key=)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "openai/gpt-oss-20b"


def build_prompt(restaurant_name: str, menu_context: str, user_query: str) -> str:
    """
    Construct a clean, instruction-style prompt for Groq LLM.

    Args:
        restaurant_name: Name of restaurant
        menu_context: Retrieved dishes (string)
        user_query: Customer's query

    Returns:
        A formatted text prompt.
    """
    prompt = textwrap.dedent(f"""
        You are a friendly and knowledgeable virtual waiter for the restaurant "{restaurant_name}".

        Use the following menu context to answer the customer's question accurately and politely.

        Menu Context:
        {menu_context}

        Customer Query:
        "{user_query}"

        Guidelines:
        - Recommend dishes that match the customer's preferences.
        - Mention dish name, price, and calories (if available).
        - Keep responses short, conversational, and natural.
        - Never invent menu items not in the context.
        - Offer at most 2–3 recommendations.

        Respond as if you're chatting with a customer.
    """).strip()
    return prompt


def generate_response(restaurant_name: str, menu_context: str, user_query: str) -> str:
    """
    Generate the waiter response using Groq-hosted LLM.

    Args:
        restaurant_name: Name of restaurant.
        menu_context: Retrieved menu text.
        user_query: Customer question.

    Returns:
        str: Natural waiter-style reply.
    """
    prompt = build_prompt(restaurant_name, menu_context, user_query)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful AI waiter."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=500,
    )

    reply = response.choices[0].message.content.strip()
    return reply


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
