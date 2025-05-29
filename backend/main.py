from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SummarizeRequest(BaseModel):
    query: str

@app.post("/api/summarize")
async def summarize(req: SummarizeRequest):
    return {
        "summary": f"<h2>Mocked Summary</h2><p>This is a mock for query: <strong>{req.query}</strong></p>"
    }
