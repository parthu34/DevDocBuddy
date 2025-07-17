import os
import fitz  # PyMuPDF
import requests

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from transformers import pipeline
from embeddings_store import EmbeddingsStore

# Initialize embeddings store globally
embed_store = EmbeddingsStore()

# Initialize Hugging Face summarization model (sync)
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for summarize endpoint
class SummarizeRequest(BaseModel):
    query: Optional[str] = None

# Text input summarization
@app.post("/api/summarize")
def summarize(req: SummarizeRequest):
    content = req.query or ""
    summary = generate_summary(content)
    return {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>"}

# File upload summarization and embeddings build
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(contents)
    else:
        text = contents.decode("utf-8", errors="ignore")

    # Build embeddings store with chunks for Q&A
    chunks = split_text_into_chunks(text, chunk_size=500)
    embed_store.build_index(chunks)

    summary = generate_summary(text)
    return {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>"}

# GitHub doc URL summarization and embeddings build
@app.post("/api/upload-url")
async def upload_url(url: str = Form(...)):
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        return {"summary": f"<h2>Error</h2><p>Failed to fetch URL: {url}<br>{str(e)}</p>"}

    chunks = split_text_into_chunks(content, chunk_size=500)
    embed_store.build_index(chunks)

    summary = generate_summary(content)
    return {"summary": f"<h2>GitHub URL Summary</h2><p>{summary}</p>"}

# Ask question endpoint using embeddings + summarization
@app.post("/api/ask")
def ask_question(question: str = Form(...)):
    if not embed_store.index or not embed_store.texts:
        raise HTTPException(status_code=400, detail="No document embeddings found. Upload a document first.")

    relevant_chunks = embed_store.search(question, top_k=3)
    context = "\n\n".join(relevant_chunks)

    prompt = f"Given the following documentation excerpts:\n{context}\n\nAnswer the question: {question}"
    answer = generate_summary(prompt)

    return {
        "answer": answer,
        "sources": relevant_chunks  # NEW: Send chunks back to frontend
    }

# Utility to extract text from PDF bytes
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return "\n".join([page.get_text() for page in doc])

# Simple text chunking utility
def split_text_into_chunks(text, chunk_size=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
    return chunks

# Generate summary using Hugging Face pipeline (sync)
def generate_summary(text: str) -> str:
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    summaries = [
        summarizer(chunk, max_length=100, min_length=30, do_sample=False)[0]["summary_text"]
        for chunk in chunks[:3]  # Limit chunks for speed
    ]
    return " ".join(summaries)
