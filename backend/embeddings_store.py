from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
import pickle
from typing import List, Dict, Any, Optional, Tuple


class EmbeddingsStore:
    """
    Cosine-similarity retrieval using FAISS IndexFlatIP
    (we L2-normalize vectors so inner-product == cosine similarity).

    Now stores metadata per chunk (e.g., page number, source title).
    """
    def __init__(self, model_name="all-MiniLM-L6-v2", persist_dir="data"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.texts: List[str] = []
        self.metas: List[Dict[str, Any]] = []
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self._load_if_exists()

    def _encode(self, texts: List[str]) -> np.ndarray:
        embs = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        # normalize_embeddings=True already L2-normalizes to unit vectors (sbert>=2.2).
        return embs.astype("float32")

    # ----------------------
    # Build / Add
    # ----------------------
    def build_index(self, texts: List[str], metas: Optional[List[Dict[str, Any]]] = None):
        if not texts:
            self.index = None
            self.texts = []
            self.metas = []
            return
        if metas is None:
            metas = [{} for _ in texts]
        if len(metas) != len(texts):
            raise ValueError("metas length must match texts length")
        embeddings = self._encode(texts)
        self.index = faiss.IndexFlatIP(self.dimension)  # cosine when vectors are unit-normalized
        self.index.add(embeddings)
        self.texts = list(texts)
        self.metas = list(metas)
        self._persist()

    def add_texts(self, new_texts: List[str], new_metas: Optional[List[Dict[str, Any]]] = None):
        if not new_texts:
            return
        if new_metas is None:
            new_metas = [{} for _ in new_texts]
        if len(new_metas) != len(new_texts):
            raise ValueError("new_metas length must match new_texts length")
        embeddings = self._encode(new_texts)
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.texts = []
            self.metas = []
        self.index.add(embeddings)
        self.texts.extend(new_texts)
        self.metas.extend(new_metas)
        self._persist()

    def reset(self):
        self.index = None
        self.texts = []
        self.metas = []
        for fname in ["index.faiss", "texts.pkl", "metas.pkl"]:
            try:
                os.remove(os.path.join(self.persist_dir, fname))
            except FileNotFoundError:
                pass

    # ----------------------
    # Search
    # ----------------------
    def search(self, query: str, top_k: int = 5):
        """Legacy: returns (results, scores)."""
        if self.index is None:
            return [], []
        q = self._encode([query])
        sims, idxs = self.index.search(q, top_k)
        results, scores = [], []
        for score, idx in zip(sims[0], idxs[0]):
            if 0 <= idx < len(self.texts):
                results.append(self.texts[idx])
                scores.append(float(score))
        return results, scores

    def search_with_meta(self, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """Preferred: returns list of {index, text, meta, similarity}."""
        out: List[Dict[str, Any]] = []
        if self.index is None:
            return out
        q = self._encode([query])
        sims, idxs = self.index.search(q, top_k)
        for score, idx in zip(sims[0], idxs[0]):
            if 0 <= idx < len(self.texts):
                out.append({
                    "index": int(idx),
                    "text": self.texts[idx],
                    "meta": self.metas[idx] if self.metas and idx < len(self.metas) else {},
                    "similarity": float(score),
                })
        return out

    # ----------------------
    # Persistence
    # ----------------------
    def _persist(self):
        idx_path = os.path.join(self.persist_dir, "index.faiss")
        txt_path = os.path.join(self.persist_dir, "texts.pkl")
        meta_path = os.path.join(self.persist_dir, "metas.pkl")
        try:
            if self.index is not None:
                faiss.write_index(self.index, idx_path)
            with open(txt_path, "wb") as f:
                pickle.dump(self.texts, f)
            with open(meta_path, "wb") as f:
                pickle.dump(self.metas, f)
        except Exception as e:
            print(f"Warning: failed to persist index: {e}")

    def _load_if_exists(self):
        idx_path = os.path.join(self.persist_dir, "index.faiss")
        txt_path = os.path.join(self.persist_dir, "texts.pkl")
        meta_path = os.path.join(self.persist_dir, "metas.pkl")
        try:
            if os.path.exists(idx_path) and os.path.exists(txt_path):
                self.index = faiss.read_index(idx_path)
                with open(txt_path, "rb") as f:
                    self.texts = pickle.load(f)
                if os.path.exists(meta_path):
                    with open(meta_path, "rb") as f:
                        self.metas = pickle.load(f)
                else:
                    self.metas = [{} for _ in self.texts]
        except Exception:
            self.index = None
            self.texts = []
            self.metas = []
