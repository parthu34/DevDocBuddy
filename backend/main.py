import os
import re
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
from transformers import pipeline

# local imports
from doc_parser import (
    parse_pdf_bytes_to_pages,    # ensure your doc_parser has this (we added earlier)
    parse_markdown_text,
    fetch_github_readme,
)
from embeddings_store import EmbeddingsStore  # your updated store with metas/search_with_meta

# ---------------- Env / Config ----------------
load_dotenv()
HF_SUMMARIZER = os.getenv("HF_SUMMARIZER", "sshleifer/distilbart-cnn-12-6")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))           # a little smaller for speed
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
MAX_SUMMARY_CHUNKS = int(os.getenv("MAX_SUMMARY_CHUNKS", "8"))  # ↓ from 20 to 8 for responsiveness
QA_MODEL = os.getenv("QA_MODEL", "deepset/roberta-base-squad2")
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.35"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("devdocbuddy")

embed_store = EmbeddingsStore(model_name=EMBEDDING_MODEL)

# Bind tokenizer explicitly; safer on some HF/torch combos
summarizer = pipeline(
    "summarization",
    model=HF_SUMMARIZER,
    tokenizer=HF_SUMMARIZER,
    device=-1
)
qa_pipeline = pipeline("question-answering", model=QA_MODEL)

app = FastAPI(title="DevDocBuddy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with your Vercel domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Models ----------------
class SummarizeRequest(BaseModel):
    query: Optional[str] = None
    index: bool = True             # summarize & index by default
    mode: Optional[str] = "replace"
    title: Optional[str] = "Manual Text"

# ---------------- Utils ----------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

def split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    words = text.split()
    if not words:
        return []
    chunks, i, n = [], 0, len(words)
    step = max(1, chunk_size - overlap)
    while i < n:
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += step
    return chunks

def split_pages_into_chunks(
    page_texts: List[str],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    source_title: str = "Document",
) -> Tuple[List[str], List[Dict[str, Any]]]:
    all_chunks: List[str] = []
    all_metas: List[Dict[str, Any]] = []
    step = max(1, chunk_size - overlap)
    for page_num, page_text in enumerate(page_texts, start=1):
        words = page_text.split()
        if not words:
            continue
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunk = " ".join(chunk_words)
            all_chunks.append(chunk)
            all_metas.append({"source_title": source_title, "page": page_num})
            i += step
    return all_chunks, all_metas

# ---- summarizer sanitization & stable lengths ----
_LONG_TOKEN = re.compile(r"(\S{120,})")
_CTRL = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")

def _sanitize_for_summarizer(text: str) -> str:
    text = _LONG_TOKEN.sub(lambda m: " ".join([m.group(1)[i:i+100] for i in range(0, len(m.group(1)), 100)]), text)
    text = _CTRL.sub(" ", text)
    return text

def _summarize_snippet(snippet: str, max_new=110, min_new=30) -> str:
    clean = _sanitize_for_summarizer(snippet)
    # Very short inputs: just return as-is (prevents warnings & saves time)
    if len(clean) < 220:
        return clean
    out = summarizer(
        clean,
        max_new_tokens=max_new,        # avoids max_length warnings
        min_new_tokens=min_new,
        do_sample=False,
        truncation=True,
        no_repeat_ngram_size=3,
    )
    return (out[0]["summary_text"] or "").strip()

def generate_summary(text: str) -> str:
    if not text or len(text.strip()) == 0:
        return ""
    chunks = split_text_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if len(chunks) > MAX_SUMMARY_CHUNKS:
        logger.info(f"Trimming chunks from {len(chunks)} -> {MAX_SUMMARY_CHUNKS} for summarization speed.")
        chunks = chunks[:MAX_SUMMARY_CHUNKS]

    chunk_summaries = []
    for i, ch in enumerate(chunks):
        try:
            chunk_summaries.append(_summarize_snippet(ch, max_new=90, min_new=25))
        except Exception as e:
            logger.warning(f"Chunk summarization failed at #{i}: {e}")

    if not chunk_summaries:
        return ""

    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    meta_input = " ".join(chunk_summaries)
    try:
        return _summarize_snippet(meta_input, max_new=150, min_new=40)
    except Exception as e:
        logger.warning(f"Meta summarization failed: {e}")
        return " ".join(chunk_summaries)

def _format_sources(used: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    out, seen = [], set()
    for item in used:
        meta = item.get("meta", {})
        key = (meta.get("source_title", "Document"), meta.get("page", None))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "title": meta.get("source_title", "Document"),
            "page": meta.get("page", None),
            "similarity": float(item.get("similarity", 0.0))
        })
        if len(out) >= top_k:
            break
    return out

def _maybe_enumeration_answer(question: str, used: List[Dict[str, Any]]) -> Optional[str]:
    q = question.lower()
    if not (("type" in q or "types" in q) and ("which" in q or "what are" in q or "list" in q)):
        return None
    combined = "\n".join(item["text"] for item in used)
    bullets: List[str] = []
    defs: Dict[str, str] = {}
    pattern = re.compile(
        r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]+\)\s*Data Type is\s+(.*?)(?:\.\s|$)',
        flags=re.IGNORECASE | re.MULTILINE
    )
    for m in pattern.finditer(combined):
        name = m.group(1).strip()
        desc = m.group(2).strip()
        defs[name.lower()] = desc
    known = ["str", "int", "float", "list", "tuple", "range", "dict", "bool", "set"]
    found: List[str] = []
    for t in known:
        if re.search(rf'\b{re.escape(t)}\b', combined):
            found.append(t)
    if not found:
        return None
    for t in found:
        desc = defs.get(t.lower(), "")
        bullets.append(f"- `{t}` — {desc}" if desc else f"- `{t}`")
    return "\n".join(bullets) if bullets else None

# ---------------- Routes ----------------
@app.post("/api/summarize")
def summarize(req: SummarizeRequest):
    content = (req.query or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="No content provided for summarization.")

    if req.index:
        chunks = split_text_into_chunks(content)
        metas = [{"source_title": req.title or "Manual Text", "page": i + 1} for i in range(len(chunks))]
        mode = (req.mode or "replace").lower()
        if mode in ("append", "add"):
            embed_store.add_texts(chunks, metas)
        else:
            embed_store.build_index(chunks, metas)

    summary = generate_summary(content)
    return {
        "summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>",
        "indexed": bool(req.index),
        "mode": (req.mode or "replace"),
        "title": req.title or "Manual Text",
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    source_title = file.filename
    try:
        if file.filename.lower().endswith(".pdf"):
            page_texts = parse_pdf_bytes_to_pages(contents)
            chunk_texts, metas = split_pages_into_chunks(page_texts, CHUNK_SIZE, CHUNK_OVERLAP, source_title)
            full_text = "\n\n".join(page_texts)
        else:
            text = contents.decode("utf-8", errors="ignore")
            text = parse_markdown_text(text)
            chunk_texts = split_text_into_chunks(text)
            metas = [{"source_title": source_title, "page": i + 1} for i in range(len(chunk_texts))]
            full_text = text
    except Exception:
        logger.exception("Failed to parse uploaded file.")
        raise HTTPException(status_code=500, detail="Failed to parse uploaded file.")

    if len(full_text) > 2_000_000:
        raise HTTPException(status_code=413, detail="File too large to process on this instance.")

    embed_store.build_index(chunk_texts, metas)
    summary = generate_summary(full_text)
    return {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>"}

@app.post("/api/upload-url")
async def upload_url(url: str = Form(...)):
    try:
        content = fetch_github_readme(url)
    except Exception as e:
        logger.exception("Failed to fetch or parse URL.")
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    chunk_texts = split_text_into_chunks(content)
    metas = [{"source_title": url, "page": i + 1} for i in range(len(chunk_texts))]
    embed_store.build_index(chunk_texts, metas)

    summary = generate_summary(content)
    return {"summary": f"<h2>GitHub URL Summary</h2><p>{summary}</p>"}

@app.post("/api/add-doc")
async def add_document(file: UploadFile = File(...)):
    contents = await file.read()
    source_title = file.filename
    try:
        if file.filename.lower().endswith(".pdf"):
            page_texts = parse_pdf_bytes_to_pages(contents)
            chunk_texts, metas = split_pages_into_chunks(page_texts, CHUNK_SIZE, CHUNK_OVERLAP, source_title)
            full_text = "\n\n".join(page_texts)
        else:
            text = contents.decode("utf-8", errors="ignore")
            text = parse_markdown_text(text)
            chunk_texts = split_text_into_chunks(text)
            metas = [{"source_title": source_title, "page": i + 1} for i in range(len(chunk_texts))]
            full_text = text
    except Exception:
        logger.exception("Failed to parse added document.")
        raise HTTPException(status_code=500, detail="Failed to parse uploaded file.")

    embed_store.add_texts(chunk_texts, metas)
    summary = generate_summary(full_text)
    return {"summary": f"<h2>Added Content Summary</h2><p>{summary}</p>"}

@app.post("/api/reset")
def reset_embeddings():
    embed_store.reset()
    return JSONResponse(content={"message": "Embeddings store reset successfully."})

@app.get("/api/reset")
def reset_embeddings_get():
    return reset_embeddings()


@app.post("/api/ask")
def ask_question(question: str = Form(...), top_k: int = Form(8)):
    if not embed_store.index or not embed_store.texts:
        raise HTTPException(status_code=400, detail="No document embeddings found. Upload a document first.")

    results = embed_store.search_with_meta(question, top_k=12)
    if not results:
        return {"answer": "I couldn't find relevant content in the uploaded documents.", "sources": []}

    filtered = [r for r in results if r["similarity"] >= MIN_SIMILARITY]
    if not filtered:
        return {"answer": "The document does not appear to contain the answer to that question.", "sources": []}

    filtered.sort(key=lambda x: x["similarity"], reverse=True)
    used: List[Dict[str, Any]] = []
    context_parts: List[str] = []
    total = 0
    for item in filtered:
        c = item["text"]
        if total + len(c) > MAX_CONTEXT_CHARS:
            break
        context_parts.append(c)
        used.append(item)
        total += len(c)
    context = "\n\n".join(context_parts)

    enum_ans = _maybe_enumeration_answer(question, used)
    if enum_ans:
        return {"answer": enum_ans, "sources": _format_sources(used)}

    try:
        qa_out = qa_pipeline(question=question, context=context)
        span = qa_out.get("answer", "").strip()
        score = float(qa_out.get("score", 0.0))
    except Exception as e:
        logger.warning(f"QA pipeline failed: {e}")
        span, score = "", 0.0

    if not span or score < 0.25:
        return {"answer": "The document does not contain a clear answer to that question.", "sources": _format_sources(used)}

    return {"answer": span, "sources": _format_sources(used), "confidence": score}
