import fitz  # PyMuPDF

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SummarizeRequest(BaseModel):
    query: Optional[str] = None

@app.post("/api/summarize")
async def summarize(req: SummarizeRequest):
    content = req.query if req.query else ""
    # TODO: Replace mock with real summary logic
    return {
        "summary": f"<h2>Summary</h2><p>This is a mock summary for input:</p><pre>{content[:500]}</pre>"
    }


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.filename.endswith(".pdf"):
        contents = await file.read()
        text = extract_text_from_pdf(contents)
    else:
        contents = await file.read()
        text = contents.decode("utf-8", errors="ignore")
    
    return {
        "summary": f"<h2>Parsed Content Summary</h2><pre>{text[:1000]}</pre>"
    }


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return "\n".join([page.get_text() for page in doc])


@app.post("/api/upload-url")
async def upload_url(url: str = Form(...)):
    # TODO: Fetch GitHub doc from URL and parse it
    content = f"Mocked content fetched from GitHub URL: {url}"
    return {
        "summary": f"<h2>GitHub URL Summary</h2><p>{content}</p>"
    }
