# backend/embeddings_store.py
import os
import pickle
import faiss
from sentence_transformers import SentenceTransformer


class EmbeddingsStore:
    """
    Cosine-similarity retrieval using FAISS IndexFlatIP.
    - Vectors are L2-normalized (SentenceTransformers normalize_embeddings=True),
      so inner product == cosine similarity.
    - Persists index, texts, and (new) metas under a writable dir.
      Defaults to /data/embeddings for HF Spaces.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", persist_dir: str | None = None):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.texts: list[str] = []
        self.metas: list[dict | None] = []  # aligned with self.texts

        # Use /data on HF Spaces; fallback to env var or default local if not set.
        self.persist_dir = persist_dir or os.getenv("EMBED_PERSIST_DIR", "/data/embeddings")
        os.makedirs(self.persist_dir, exist_ok=True)

        self.dimension = self.model.get_sentence_embedding_dimension()
        self._load_if_exists()

    # -------- encoding --------
    def _encode(self, texts: list[str]):
        embs = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,  # unit vectors
        )
        return embs.astype("float32")

    # -------- build / add --------
    def build_index(self, texts: list[str], metas: list[dict | None] | None = None):
        """
        (Re)build the index from scratch.
        Accepts optional metadata list (same length as texts). If None/short/long, we pad/trim.
        Backward-compatible: older callers can pass only `texts`.
        """
        self.index = None
        self.texts = []
        self.metas = []

        if not texts:
            self._persist()
            return

        embeddings = self._encode(texts)
        self.index = faiss.IndexFlatIP(self.dimension)  # cosine on unit vectors
        self.index.add(embeddings)
        self.texts = list(texts)

        if metas is None:
            self.metas = [None] * len(self.texts)
        else:
            m = list(metas)
            if len(m) < len(self.texts):
                m += [None] * (len(self.texts) - len(m))
            elif len(m) > len(self.texts):
                m = m[: len(self.texts)]
            self.metas = m

        self._persist()

    def add_texts(self, new_texts: list[str], new_metas: list[dict | None] | None = None):
        """
        Append new items to an existing index.
        Backward-compatible: older callers can pass only `new_texts`.
        """
        if not new_texts:
            return

        embs = self._encode(new_texts)
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.texts = []
            self.metas = []

        self.index.add(embs)
        self.texts.extend(list(new_texts))

        if new_metas is None:
            self.metas.extend([None] * len(new_texts))
        else:
            nm = list(new_metas)
            if len(nm) < len(new_texts):
                nm += [None] * (len(new_texts) - len(nm))
            elif len(nm) > len(new_texts):
                nm = nm[: len(new_texts)]
            self.metas.extend(nm)

        self._persist()

    def reset(self):
        """Clear index and remove persisted files."""
        self.index = None
        self.texts = []
        self.metas = []
        for fn in ("index.faiss", "texts.pkl", "metas.pkl"):
            try:
                os.remove(os.path.join(self.persist_dir, fn))
            except FileNotFoundError:
                pass

    # -------- search --------
    def search(self, query: str, top_k: int = 5):
        """
        Return (texts, scores) for backward compatibility with older code.
        """
        if self.index is None:
            return [], []
        q = self._encode([query])
        sims, idxs = self.index.search(q, top_k)
        results, scores = [], []
        for score, idx in zip(sims[0], idxs[0]):
            if 0 <= idx < len(self.texts):
                results.append(self.texts[idx])
                scores.append(float(score))  # cosine in [-1,1]
        return results, scores

    def search_with_meta(self, query: str, top_k: int = 5):
        """
        Return list of dicts: {"text": str, "meta": dict|None, "similarity": float}
        """
        if self.index is None:
            return []
        q = self._encode([query])
        sims, idxs = self.index.search(q, top_k)
        out = []
        for score, idx in zip(sims[0], idxs[0]):
            if 0 <= idx < len(self.texts):
                out.append(
                    {
                        "text": self.texts[idx],
                        "meta": self.metas[idx] if self.metas else None,
                        "similarity": float(score),
                    }
                )
        return out

    # -------- persistence --------
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
                    self.metas = [None] * len(self.texts)
        except Exception:
            self.index = None
            self.texts = []
            self.metas = []
