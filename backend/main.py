import os
import logging
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from doc_parser import parse_pdf_bytes, parse_markdown_text, fetch_github_readme
from embeddings_store import EmbeddingsStore

from transformers import pipeline

load_dotenv()

# ---------------- Runtime & model pins ----------------
HF_SUMMARIZER = os.getenv("HF_SUMMARIZER", "sshleifer/distilbart-cnn-12-6")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
QA_MODEL_ID = os.getenv("QA_MODEL", "deepset/roberta-base-squad2")
GEN_MODEL_ID = os.getenv("GEN_MODEL", "google/flan-t5-small")  # lightweight, CPU-friendly

# Chunking / QA
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
MAX_SUMMARY_CHUNKS = int(os.getenv("MAX_SUMMARY_CHUNKS", "18"))
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.25"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "7000"))

# Upload limits (neutral wording)
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(10 * 1024 * 1024)))  # 10 MB
MAX_PAGES = int(os.getenv("MAX_PAGES", "12"))
TRUNCATE_ON_OVERSIZE = os.getenv("TRUNCATE_ON_OVERSIZE", "false").lower() == "true"

# Concurrency guard
CONCURRENCY = int(os.getenv("CONCURRENCY", "2"))
_sem = asyncio.Semaphore(CONCURRENCY)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("devdocbuddy")

# Instantiate models
embed_store = EmbeddingsStore(model_name=EMBEDDING_MODEL)
summarizer = pipeline("summarization", model=HF_SUMMARIZER, device=-1)
qa_pipeline = pipeline("question-answering", model=QA_MODEL_ID, device=-1)

# Lazy-loaded generative fallback
_gen_pipeline = None
def _get_gen():
    global _gen_pipeline
    if _gen_pipeline is None:
        _gen_pipeline = pipeline("text2text-generation", model=GEN_MODEL_ID, device=-1)
    return _gen_pipeline

app = FastAPI(title="DevDocBuddy")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Pydantic ----------------
class SummarizeRequest(BaseModel):
    query: str
    index: Optional[bool] = False
    mode: Optional[str] = "replace"  # replace|append
    title: Optional[str] = "Manual Text"

# ---------------- Helpers ----------------
def split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
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

def generate_summary(text: str) -> str:
    """
    Per-chunk summaries + meta-summary for quality.
    Length-guarded to avoid 'max_length > input_length' warnings.
    """
    t = text.strip()
    if not t:
        return ""

    chunks = split_text_into_chunks(t, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if len(chunks) > MAX_SUMMARY_CHUNKS:
        chunks = chunks[:MAX_SUMMARY_CHUNKS]

    chunk_summaries = []
    for ch in chunks if chunks else [t]:
        try:
            out = summarizer(ch, max_length=140, min_length=60, do_sample=False)
            chunk_summaries.append(out[0]["summary_text"].strip())
        except Exception as e:
            logger.warning(f"summarize chunk fallback: {e}")
            chunk_summaries.append((ch[:500] + "...") if len(ch) > 520 else ch)

    if not chunk_summaries:
        return ""
    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    meta_input = "\n\n".join(chunk_summaries)
    try:
        meta = summarizer(meta_input, max_length=200, min_length=80, do_sample=False)
        return meta[0]["summary_text"].strip()
    except Exception as e:
        logger.warning(f"meta summarize fallback: {e}")
        return " ".join(chunk_summaries)

def _trim_context(s: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    s = s.strip()
    if len(s) <= max_chars:
        return s
    # Keep head and tail parts to preserve variety
    head = s[: max_chars // 2]
    tail = s[- max_chars // 2 :]
    return head + "\n...\n" + tail

async def _try_acquire() -> None:
    try:
        await asyncio.wait_for(_sem.acquire(), timeout=10)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=429, detail="Service is busy. Please retry in a few seconds.")

def _release() -> None:
    try:
        _sem.release()
    except ValueError:
        pass

# ---------------- Error handling ----------------
@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=503,
        content={"detail": "The service encountered an error. Please try again with a smaller input or a bit later."}
    )

# ---------------- Health & index ----------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/api/index-status")
def index_status():
    ready = bool(embed_store.index) and bool(embed_store.texts)
    return {"ready": ready, "count": len(embed_store.texts)}

# ---------------- Summarize ----------------
@app.post("/api/summarize")
async def summarize(req: SummarizeRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(400, "No content provided.")
    text = req.query.strip()
    summary = generate_summary(text)

    if req.index:
        chunks = split_text_into_chunks(text)
        metas = [{"title": req.title or "Manual Text"}] * len(chunks)
        if req.mode == "append" and embed_store.index:
            embed_store.add_texts(chunks, metas)
        else:
            embed_store.build_index(chunks, metas)

    return {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>", "title": req.title}

# ---------------- Upload file ----------------
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    await _try_acquire()
    try:
        contents = await file.read()
        if len(contents) > MAX_FILE_BYTES:
            raise HTTPException(413, f"File too large for current limits ({len(contents)} bytes).")

        truncated = False
        if file.filename.lower().endswith(".pdf"):
            text, total_pages, used_pages = parse_pdf_bytes(contents, max_pages=(MAX_PAGES if TRUNCATE_ON_OVERSIZE else None))
            if not TRUNCATE_ON_OVERSIZE and total_pages > MAX_PAGES:
                raise HTTPException(413, f"PDF has {total_pages} pages; the current limit is {MAX_PAGES} pages.")
            truncated = used_pages < total_pages
            title = file.filename or "Uploaded PDF"
        else:
            text = contents.decode("utf-8", errors="ignore")
            text = parse_markdown_text(text)
            title = file.filename or "Uploaded Text"

        if len(text) > 2_000_000:
            raise HTTPException(413, "Document text is too large for this service.")

        chunks = split_text_into_chunks(text)
        metas = [{"title": title}] * len(chunks)
        embed_store.build_index(chunks, metas)

        summary = generate_summary(text)
        payload = {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>", "title": title}
        if file.filename.lower().endswith(".pdf"):
            payload.update({
                "pages_total": total_pages,
                "pages_used": used_pages,
                "truncated": truncated
            })
            if truncated:
                payload["warning"] = f"Indexed the first {used_pages} of {total_pages} pages (limit applied)."
        return payload
    finally:
        _release()

# ---------------- Upload URL ----------------
@app.post("/api/upload-url")
async def upload_url(url: str = Form(...)):
    await _try_acquire()
    try:
        content = fetch_github_readme(url)
        chunks = split_text_into_chunks(content)
        metas = [{"title": url}] * len(chunks)
        embed_store.build_index(chunks, metas)
        summary = generate_summary(content)
        return {"summary": f"<h2>GitHub URL Summary</h2><p>{summary}</p>", "title": url}
    finally:
        _release()

# ---------------- Add (append) ----------------
@app.post("/api/add-doc")
async def add_document(file: UploadFile = File(...)):
    await _try_acquire()
    try:
        contents = await file.read()
        if file.filename.lower().endswith(".pdf"):
            text, _, _ = parse_pdf_bytes(contents, max_pages=(MAX_PAGES if TRUNCATE_ON_OVERSIZE else None))
        else:
            text = contents.decode("utf-8", errors="ignore")
            text = parse_markdown_text(text)

        chunks = split_text_into_chunks(text)
        metas = [{"title": file.filename or "Added Doc"}] * len(chunks)
        embed_store.add_texts(chunks, metas)
        summary = generate_summary(text)
        return {"summary": f"<h2>Added Content Summary</h2><p>{summary}</p>", "title": file.filename}
    finally:
        _release()

# ---------------- Reset ----------------
@app.post("/api/reset")
def reset_embeddings():
    embed_store.reset()
    return {"message": "Embeddings store reset successfully."}

@app.get("/api/reset")
def reset_embeddings_get():
    return reset_embeddings()

# ---------------- Ask ----------------
@app.post("/api/ask")
def ask_question(
    question: str = Form(...),
    top_k: int = Form(10)
):
    if not embed_store.index or not embed_store.texts:
        raise HTTPException(status_code=400, detail="No document indexed yet. Upload a PDF/URL or paste text first.")

    # Retrieve
    chunks, sims = embed_store.search(question, top_k=top_k)
    if not chunks:
        return {"answer": "I couldn't find relevant content in the uploaded documents.", "sources": []}

    pairs = list(zip(chunks, sims))
    filtered = [(c, s) for (c, s) in pairs if s >= MIN_SIMILARITY]
    if not filtered:
        filtered = pairs[:3]

    # Build compact context
    filtered.sort(key=lambda x: x[1], reverse=True)
    context_parts, used = [], []
    total = 0
    for c, s in filtered:
        if total + len(c) > MAX_CONTEXT_CHARS:
            break
        context_parts.append(c)
        used.append((c, s))
        total += len(c)
    context = "\n\n".join(context_parts)
    context = _trim_context(context, MAX_CONTEXT_CHARS)

    # 1) Extractive QA
    span, score = "", 0.0
    try:
        qa_out = qa_pipeline(question=question, context=context)
        span = (qa_out.get("answer") or "").strip()
        score = float(qa_out.get("score") or 0.0)
    except Exception:
        pass

    # If extractive fails, 2) Generative fallback constrained by context
    if not span or score < 0.25:
        try:
            gen = _get_gen()
            prompt = (
                "You are a helpful assistant. Answer the question ONLY using the provided context. "
                "If the answer is not in the context, reply: I don't know.\n\n"
                f"Context:\n{context}\n\n"
                f"Question: {question}\nAnswer:"
            )
            g = gen(
                prompt,
                max_new_tokens=80,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )
            cand = (g[0]["generated_text"] or "").strip()
            # Basic guard: if model declines, propagate 'no answer'
            bad = ["i don't know", "i do not know", "not in the context", "cannot be determined"]
            if not cand or any(b in cand.lower() for b in bad):
                return {
                    "answer": "The document does not contain a clear answer to that question.",
                    "sources": [{"text": c, "similarity": s} for (c, s) in used]
                }
            final_answer = cand
            return {
                "answer": final_answer,
                "sources": [{"text": c, "similarity": s} for (c, s) in used],
                "confidence": None,
                "note": "generative-from-context"
            }
        except Exception:
            return {
                "answer": "The document does not contain a clear answer to that question.",
                "sources": [{"text": c, "similarity": s} for (c, s) in used]
            }

    # Optional light polish of extractive span
    try:
        top_support = used[0][0] if used else ""
        polish_input = (
            "Answer succinctly based only on the extracted span and supporting excerpt.\n\n"
            f"Span:\n{span}\n\nExcerpt:\n{top_support}\n\nFinal answer:"
        )
        polished = summarizer(polish_input, max_length=120, min_length=20, do_sample=False)[0]["summary_text"].strip()
        final_answer = polished if polished else span
    except Exception:
        final_answer = span

    return {
        "answer": final_answer,
        "sources": [{"text": c, "similarity": s} for (c, s) in used],
        "confidence": score,
        "note": "extractive"
    }
