import os
import fitz  # PyMuPDF
import requests

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from transformers import pipeline

# Initialize Hugging Face summarization model (loaded once)
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

# Pydantic model
class SummarizeRequest(BaseModel):
    query: Optional[str] = None

# Text input summarization
@app.post("/api/summarize")
async def summarize(req: SummarizeRequest):
    content = req.query or ""
    summary = generate_summary(content)
    return {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>"}

# File upload summarization
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(contents)
    else:
        text = contents.decode("utf-8", errors="ignore")
    summary = generate_summary(text)
    return {"summary": f"<h2>Parsed Content Summary</h2><p>{summary}</p>"}

# GitHub doc URL summarization
@app.post("/api/upload-url")
async def upload_url(url: str = Form(...)):
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        return {"summary": f"<h2>Error</h2><p>Failed to fetch URL: {url}<br>{str(e)}</p>"}
    
    summary = generate_summary(content)
    return {"summary": f"<h2>GitHub URL Summary</h2><p>{summary}</p>"}

# Extract text from PDF
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return "\n".join([page.get_text() for page in doc])

# Generate summary using Hugging Face
def generate_summary(text: str) -> str:
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    summaries = [
        summarizer(chunk, max_length=100, min_length=30, do_sample=False)[0]["summary_text"]
        for chunk in chunks[:3]  # Limit for speed
    ]
    return " ".join(summaries)
