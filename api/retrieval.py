# menu/retrieval.py
"""
Retrieval module for the Virtual Waiter system.
Uses local embeddings (SentenceTransformers) + Chroma for semantic search.
"""

import chromadb
from sentence_transformers import SentenceTransformer

# --- Load embedding model and Chroma persistent client ---
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_db")

try:
    collection = chroma_client.get_collection("menu_items")
except Exception:
    raise RuntimeError(
        "❌ Chroma collection 'menu_items' not found. "
        "Run `python manage.py index_to_chroma` first to create it."
    )


def retrieve_menu_items(restaurant_id: str, user_query: str, k: int = 5):
    """
    Retrieves top-k most relevant menu items for a given restaurant and user query.

    Args:
        restaurant_id (str): Restaurant UUID.
        user_query (str): Natural language query from user.
        k (int): Number of items to retrieve.

    Returns:
        list[dict]: List of dicts containing "text" and "meta".
    """
    if not user_query.strip():
        return []

    # Compute embedding for query
    query_emb = embedding_model.encode(user_query, show_progress_bar=False).tolist()

    # Query Chroma with restaurant filter
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=k,
        where={"restaurant_id": str(restaurant_id)}
    )

    docs = []
    if not results or not results.get("documents"):
        return docs

    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        # Ensure metadata keys exist safely
        meta = meta or {}
        docs.append({
            "text": doc,
            "meta": {
                "dish_id": meta.get("dish_id", ""),
                "dish_name": meta.get("dish_name", ""),
                "restaurant_name": meta.get("restaurant_name", ""),
                "price": meta.get("price", 0.0),
                "calories": meta.get("calories", 0),
                "category": meta.get("category", ""),
                "tags": meta.get("tags", ""),
                "ingredients": meta.get("ingredients", ""),
                "chef_special": meta.get("chef_special", ""),
                "image_url": meta.get("image_url", ""),
                "video_url": meta.get("video_url", ""),
                "model_3d_url": meta.get("model_3d_url", "")
            }
        })

    return docs


def build_menu_context(docs: list[dict]) -> str:
    """
    Converts retrieved dish documents into a readable context string
    for feeding into LLM prompt (llm.py).

    Args:
        docs: List of dish dictionaries from retrieve_menu_items().

    Returns:
        str: Clean formatted text summary of dishes.
    """
    if not docs:
        return "No matching dishes found for this restaurant."

    context_lines = []
    for d in docs:
        m = d["meta"]
        context_lines.append(
            f"Name: {m['dish_name']} | "
            f"Category: {m['category']} | "
            f"Price: ₹{m['price']} | "
            f"Calories: {m['calories']} kcal | "
            f"Tags: {m['tags']} | "
            f"Ingredients: {m['ingredients']} | "
            f"Chef Special: {m['chef_special']}"
        )

    return "\n".join(context_lines)


def debug_retrieval(restaurant_id: str, query: str, k: int = 5):
    """
    Simple CLI test helper for debugging retrieval behavior.
    """
    results = retrieve_menu_items(restaurant_id, query, k)
    if not results:
        print("⚠️ No matching items found.")
        return

    print(f"\n🔍 Query: {query}\n")
    for i, r in enumerate(results, 1):
        m = r["meta"]
        print(f"{i}. {m['dish_name']} — ₹{m['price']} ({m['calories']} kcal)")
        print(f"Tags: {m['tags']}")
        print(f"Category: {m['category']}")
        print(f"Chef Special: {m['chef_special']}\n")

    print("📋 Context for LLM:")
    print("---------------------")
    print(build_menu_context(results))


# Example standalone test
if __name__ == "__main__":
    debug_retrieval(
        restaurant_id="5dd31c71-8a0e-4928-8810-a2d2f5336341",
        query="spicy chicken under 400 calories",
        k=3
    )
