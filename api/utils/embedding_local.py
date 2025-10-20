# utils/embeddings_local.py
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")  # small and fast

def embed_texts(texts):
    return model.encode(texts, show_progress_bar=False).tolist()
