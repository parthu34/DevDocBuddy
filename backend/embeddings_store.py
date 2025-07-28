from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class EmbeddingsStore:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        # Load the embedding model
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.texts = []  # List of texts corresponding to vectors
        self.dimension = self.model.get_sentence_embedding_dimension()

    def build_index(self, texts):
        # Completely rebuild the index with new texts
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings)
        self.texts = texts

    def add_texts(self, new_texts):
        # Add new texts incrementally to existing index
        embeddings = self.model.encode(new_texts, convert_to_numpy=True)
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.texts = []
        self.index.add(embeddings)
        self.texts.extend(new_texts)

    def reset(self):
        # Clear index and texts
        self.index = None
        self.texts = []

    def search(self, query, top_k=5):
        if self.index is None:
            return []
        query_vec = self.model.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_vec, top_k)
        results = []
        for idx in indices[0]:
            if idx < len(self.texts):
                results.append(self.texts[idx])
        return results
