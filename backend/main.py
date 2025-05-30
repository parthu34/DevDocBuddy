from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# CORS setup (keep as-is)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in prod
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
    # Mocked logic — will add real parser later
    content = ""

    if query:
        content = query
    elif github_url:
        content = f"Mocked content fetched from GitHub URL: {github_url}"
    elif file:
        contents = await file.read()
        content = contents.decode("utf-8", errors="ignore")

    return {
        "summary": f"<h2>Summary</h2><p>This is a mock summary for input:</p><pre>{content[:500]}</pre>"
    }
