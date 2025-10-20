# menu/management/commands/index_to_chroma.py
import os
import json
from django.core.management.base import BaseCommand
from api.models import Dish
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# --- Use Chroma persistent client ---
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("menu_items")

# --- Local embedding model ---
# small, fast, accurate enough for menus
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

class Command(BaseCommand):
    help = "Index all restaurant menu items into Chroma using local embeddings (no OpenAI needed)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🔄 Starting menu indexing (local embeddings)..."))

        items = Dish.objects.select_related("restaurant").all()
        if not items:
            self.stdout.write(self.style.ERROR("⚠️  No menu items found."))
            return

        documents, metadatas, ids = [], [], []

        for item in items:
            text = (
                f"Name: {item.name}\n"
                f"Description: {item.description}\n"
                f"Calories: {item.calories}\n"
                f"Price: {item.price}\n"
                f"Category: {item.category}\n"
                f"Tags: {', '.join(item.tags or [])}\n"
                f"Ingredients: {', '.join(item.ingredients or [])}"
            )

            metadata = {
                "item_id": str(item.id),
                "restaurant_id": str(item.restaurant.id),
                "name": item.name,
                "price": float(item.price) if item.price else 0.0,
                "calories": int(item.calories) if item.calories else 0,
                "tags": ", ".join(item.tags or []),
            }

            documents.append(text)
            metadatas.append(metadata)
            ids.append(str(item.id))

        self.stdout.write("🧠 Generating local embeddings...")

        embeddings = []
        for doc in tqdm(documents, desc="Embedding"):
            emb = embedding_model.encode(doc, show_progress_bar=False).tolist()
            embeddings.append(emb)

        try:
            collection.delete()
            self.stdout.write("🧹 Cleared existing collection.")
        except Exception:
            self.stdout.write("ℹ️  New collection, no previous data.")

        self.stdout.write(f"📦 Adding {len(documents)} menu items to Chroma...")
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        self.stdout.write(self.style.SUCCESS("✅ Menu indexing complete (local embeddings)!"))
        self.stdout.write(self.style.SUCCESS(f"📁 Data stored in ./chroma_db"))
