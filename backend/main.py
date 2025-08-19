import os
import re
import logging
from dotenv import load_dotenv
import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple

# local imports
from doc_parser import (
    parse_pdf_bytes,
    parse_pdf_bytes_to_pages,
    parse_markdown_text,
    fetch_github_readme,
)
from embeddings_store import EmbeddingsStore

# transformers summarizer + extractive QA
from transformers import pipeline

# Load environment variables
load_dotenv()
HF_SUMMARIZER = os.getenv("HF_SUMMARIZER", "sshleifer/distilbart-cnn-12-6")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))  # words per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
MAX_SUMMARY_CHUNKS = int(os.getenv("MAX_SUMMARY_CHUNKS", "20"))  # limit for speed
qa_model_id = os.getenv("QA_MODEL", "deepset/roberta-base-squad2")
qa_pipeline = pipeline("question-answering", model=qa_model_id)  # CPU-friendly, extractive QA
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.35"))  # reject chunks weaker than this
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))  # cap context size

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Logging setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("devdocbuddy")

# Instantiate embedding store (will load persisted index if exists)
embed_store = EmbeddingsStore(model_name=EMBEDDING_MODEL)

# Instantiate summarizer (Hugging Face pipeline) - used for /summarize endpoints only
summarizer = pipeline("summarization", model=HF_SUMMARIZER, device=-1)

# FastAPI app
app = FastAPI(title="DevDocBuddy")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Models
# ----------------------
class SummarizeRequest(BaseModel):
    query: Optional[str] = None


# ----------------------
# Utilities
# ----------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


def split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Word-based chunker with overlap (used for non-PDF content)."""
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    n = len(words)
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
    """
    Chunk each page separately so we can retain page metadata.
    Returns (chunk_texts, metas) where meta contains source_title and page.
    """
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
            all_metas.append({
                "source_title": source_title,
                "page": page_num
            })
            i += step
    return all_chunks, all_metas


def generate_summary(text: str) -> str:
    if not text or len(text.strip()) == 0:
        return ""
    # chunk text
    chunks = split_text_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    # limit for speed
    if len(chunks) > MAX_SUMMARY_CHUNKS:
        logger.info(f"Trimming chunks from {len(chunks)} -> {MAX_SUMMARY_CHUNKS} for summarization speed.")
        chunks = chunks[:MAX_SUMMARY_CHUNKS]

    # Summarize each chunk individually
    chunk_summaries = []
    for i, ch in enumerate(chunks):
        try:
            out = summarizer(ch, max_length=120, min_length=30, do_sample=False)
            text_out = out[0]["summary_text"].strip()
            chunk_summaries.append(text_out)
            logger.debug(f"Chunk {i} summary length {len(text_out)}")
        except Exception:
            logger.exception("Chunk summarization failed, continuing.")
            continue

    if not chunk_summaries:
        return ""
    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    # Meta-summary
    meta_input = "\n\n".join(chunk_summaries)
    try:
        meta_out = summarizer(meta_input, max_length=200, min_length=60, do_sample=False)
        final_summary = meta_out[0]["summary_text"].strip()
        return final_summary
    except Exception:
        logger.exception("Meta summarization failed, returning concatenated chunk summaries.")
        return " ".join(chunk_summaries)


def _format_sources(used: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """Compact sources summary for UI."""
    out = []
    seen = set()
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
    """
    If the user asks for a list of 'types/kinds', try to enumerate from context.
    Works very well for the "Python data types" PDF you tested.
    """
    q = question.lower()
    if not (("type" in q or "types" in q) and ("which" in q or "what are" in q or "list" in q)):
        return None

    combined = "\n".join(item["text"] for item in used)
    bullets: List[str] = []

    # 1) Look for pattern: "<name> (String) Data Type is ..." (captures definition sentences)
    defs: Dict[str, str] = {}
    pattern = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]+\)\s*Data Type is\s+(.*?)(?:\.\s|$)',
                         flags=re.IGNORECASE | re.MULTILINE)
    for m in pattern.finditer(combined):
        name = m.group(1).strip()
        desc = m.group(2).strip()
        defs[name.lower()] = desc

    # 2) Collect known common Python scalar/collection types if present in context
    known = ["str", "int", "float", "list", "tuple", "range", "dict", "bool", "set"]
    found: List[str] = []
    for t in known:
        if re.search(rf'\b{re.escape(t)}\b', combined):
            found.append(t)

    # Prefer order of appearance in `known`
    if not found:
        return None

    for t in found:
        desc = defs.get(t.lower(), "")
        if desc:
            bullets.append(f"- `{t}` — {desc}")
        else:
            bullets.append(f"- `{t}`")

    if bullets:
        return "\n".join(bullets)
    return None


# ----------------------
# Routes
# ----------------------
@app.post("/api/summarize")
def summarize(req: SummarizeRequest):
    content = req.query or ""
    if not content:
        raise HTTPException(status_code=400, detail="No content provided for summarization.")
    summary = generate_summary(content)
    return {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    logger.info(f"Received upload: {file.filename}, size={len(contents)} bytes")
    source_title = file.filename

    try:
        if file.filename.lower().endswith(".pdf"):
            page_texts = parse_pdf_bytes_to_pages(contents)
            # Build chunks per page to retain page metadata
            chunk_texts, metas = split_pages_into_chunks(page_texts, CHUNK_SIZE, CHUNK_OVERLAP, source_title)
            full_text = "\n\n".join(page_texts)
        else:
            # assume markdown or txt
            text = contents.decode("utf-8", errors="ignore")
            text = parse_markdown_text(text)
            chunk_texts = split_text_into_chunks(text)
            # use synthetic "page" numbering (1..N) for consistency
            metas = [{"source_title": source_title, "page": i + 1} for i in range(len(chunk_texts))]
            full_text = text
    except Exception:
        logger.exception("Failed to parse uploaded file.")
        raise HTTPException(status_code=500, detail="Failed to parse uploaded file.")

    # Basic guard for huge files
    if len(full_text) > 2_000_000:
        raise HTTPException(status_code=413, detail="File too large to process on this instance.")

    embed_store.build_index(chunk_texts, metas)

    summary = generate_summary(full_text)
    return {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>"}


@app.post("/api/upload-url")
async def upload_url(url: str = Form(...)):
    logger.info(f"Fetching URL: {url}")
    try:
        # try GitHub specialized fetch
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
    logger.info(f"Adding doc: {file.filename}, size={len(contents)} bytes")
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


@app.post("/api/ask")
def ask_question(question: str = Form(...)):
    """
    Strict RAG flow:
    1) Retrieve top chunks with cosine similarity.
    2) Filter out low-similarity chunks.
    3) Build a compact context (up to MAX_CONTEXT_CHARS).
    4) Try an enumeration-style answer (for "types/list/which" questions) from context only.
    5) Otherwise, run extractive QA (SQuAD2) strictly on the context.
       - If low confidence OR empty -> say it's not in the doc.
    """
    if not embed_store.index or not embed_store.texts:
        raise HTTPException(status_code=400, detail="No document embeddings found. Upload a document first.")

    logger.info(f"Q: {question}")
    results = embed_store.search_with_meta(question, top_k=12)
    if not results:
        return {"answer": "I couldn't find relevant content in the uploaded documents.", "sources": []}

    # Keep only chunks above similarity threshold
    filtered = [r for r in results if r["similarity"] >= MIN_SIMILARITY]
    if not filtered:
        return {"answer": "The document does not appear to contain the answer to that question.", "sources": []}

    # Sort by similarity desc and build a compact context up to char cap
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

    # 1) Enumeration intent (e.g., "Which are python data types?")
    enum_ans = _maybe_enumeration_answer(question, used)
    if enum_ans:
        return {
            "answer": enum_ans,
            "sources": _format_sources(used)
        }

    # 2) Extractive QA (strict, no generative polishing to avoid instruction leakage)
    try:
        qa_out = qa_pipeline(question=question, context=context)
        span = qa_out.get("answer", "").strip()
        score = float(qa_out.get("score", 0.0))
    except Exception:
        logger.exception("QA pipeline failed")
        span, score = "", 0.0

    if not span or score < 0.25:
        return {
            "answer": "The document does not contain a clear answer to that question.",
            "sources": _format_sources(used)
        }

    return {
        "answer": span,
        "sources": _format_sources(used),
        "confidence": score
    }
