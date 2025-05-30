from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os

from doc_parser import parse_pdf, parse_markdown, fetch_github_readme

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/summarize")
async def summarize(
    query: Optional[str] = Form(None),
    github_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    content = ""

    if query:
        content = query
    elif github_url:
        content = fetch_github_readme(github_url)
    elif file:
        ext = os.path.splitext(file.filename)[-1].lower()
        os.makedirs("temp", exist_ok=True)
        temp_path = os.path.join("temp", file.filename)

        with open(temp_path, "wb") as f:
            f.write(await file.read())

        if ext == ".pdf":
            content = parse_pdf(temp_path)
        elif ext == ".md":
            content = parse_markdown(temp_path)
        else:
            content = f"Unsupported file type: {ext}"

        os.remove(temp_path)
    else:
        content = "⚠️ No input provided"

    return {
        "summary": f"<h2>Parsed Summary</h2><pre>{content[:1000]}</pre>"
    }
