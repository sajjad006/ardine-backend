# menu/retrieval.py
"""
Retrieval module for your Virtual Waiter system.
Uses local embeddings (SentenceTransformers) + Chroma for semantic search.
"""

import chromadb
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_db")

try:
    collection = chroma_client.get_collection("menu_items")
except Exception:
    raise RuntimeError(
        "❌ Chroma collection 'menu_items' not found. "
        "Run `python manage.py index_to_chroma` first to create it."
    )


def retrieve_menu_items(restaurant_id: int | str, user_query: str, k: int = 5):
    """
    Retrieves top-k most relevant menu items for a given restaurant and user query.

    Args:
        restaurant_id (int | str): Restaurant ID (as string if UUID).
        user_query (str): Natural language query from user.
        k (int): Number of items to retrieve.

    Returns:
        List[dict]: List of dicts with "text" and "metadata" keys.
    """
    # Compute embedding for query
    query_emb = embedding_model.encode(user_query, show_progress_bar=False).tolist()

    # Query Chroma
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=k,
        where={"restaurant_id": str(restaurant_id)}  # Filter by restaurant
    )

    # Convert result format for easier usage
    docs = []
    if results and results["documents"]:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            docs.append({
                "text": doc,
                "meta": meta
            })

    return docs


def debug_retrieval(restaurant_id: str, query: str, k: int = 5):
    results = retrieve_menu_items(restaurant_id, query, k)
    if not results:
        print("⚠️ No matching items found.")
        return
    print(f"\n🔍 Query: {query}\n")
    for i, r in enumerate(results, 1):
        m = r["meta"]
        print(f"{i}. {m['name']} — ₹{m['price']} ({m['calories']} kcal)")
        print(f"Tags: {m['tags']}")
        print()


# Example standalone test
if __name__ == "__main__":
    debug_retrieval(restaurant_id="5dd31c71-8a0e-4928-8810-a2d2f5336341", query="spicy chicken under 400 calories", k=3)
