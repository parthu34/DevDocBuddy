# DevDocBuddy

Turn dense developer docs into answers. Upload a PDF/Markdown or paste a GitHub URL, get a plain-English summary, then **ask questions with sources**.

- **Live app:** https://dev-doc-buddy.vercel.app  
- **Backend (API):** Hugging Face Space (containerized FastAPI)  
- **Self-host bundle:** see Releases for zip

> ⚠️ Demo is public. Don’t upload confidential material.

---

## ✨ Features

- **Multi-ingest:** PDF, Markdown, GitHub README/URL
- **Summarize & Index:** quick, readable overview + retrieval index
- **Q&A over your docs:** answers **grounded** in the indexed chunks
- **Citations:** expandable sources with similarity scores
- **Lightweight stack:** FastAPI + SentenceTransformers + FAISS + Vue 3 (Vite)
- **Deployable:** Vercel (frontend) + Hugging Face Spaces (backend)

---

## 🧱 Architecture (MVP)

- **Frontend:** Vue 3 + Vite + Pinia + Axios  
- **Backend:** FastAPI (Python), extractive QA (`deepset/roberta-base-squad2`)  
- **Embeddings:** `all-MiniLM-L6-v2` via SentenceTransformers  
- **Vector store:** FAISS (cosine similarity, on CPU)  
- **Parsing:** PyMuPDF (PDF), Markdown/BeautifulSoup, GitHub raw fetcher  
- **Hosting:** Vercel (static site) + Hugging Face Space (Docker)  

---

## 🚀 Quick Start (Local)

### 1) Backend (FastAPI)

Requires Python **3.10**.

```bash
# from repo root
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

# optional: set env (or rely on defaults)
# echo "HF_SUMMARIZER=sshleifer/distilbart-cnn-12-6" >> .env

uvicorn main:app --reload --port 8000
```

Health check: http://localhost:8000/docs

### 2) Frontend (Vite)
```
# new terminal
cd frontend
npm i
# dev uses Vite proxy to :8000 by default
npm run dev
```

### 🌐 Production Deploy

**Backend → Hugging Face Spaces (Docker)**
- Push backend/Dockerfile and backend code.
 -Space type: Docker.
- Exposed port: 7860 (already configured in Dockerfile as PORT).
- The app serves FastAPI at / (e.g., https://<space>.hf.space).

**Important env (already handled in Dockerfile):**
- HF_HOME=/data/.huggingface
 -TRANSFORMERS_CACHE=/data/.cache/huggingface
- SENTENCE_TRANSFORMERS_HOME=/data/.cache/sentence-transformers**
- A writable /data volume will be created automatically.

**Frontend → Vercel**
- Import repo → framework Vite (auto).
- Env Vars → VITE_API_BASE = your Space base URL, e.g.:

### 🧪How to Use (Flow)
1. Upload a PDF/Markdown or paste a GitHub URL, then click Summarize & Index.
- The summary renders in “Results”.
- The index is built for Q&A.

2. Ask AI (Q&A): type a question (e.g., “What is a variable?”).
- See an answer; click Show Sources to expand citations.

3. Reset Index clears the current index and input fields.

4. “Get the self-host bundle” opens your one-time purchase / bundle link.

Index status: the app prevents Q&A until an index exists.
The frontend calls /api/index-status and gates the “Ask” input.

###🔌API (for reference)
All routes are under the backend base URL.
- GET /healthz – simple health check
- POST /api/summarize – body { query, index, mode, title }
- Returns { summary: "<html>", ... } and rebuilds index if index=true
- POST /api/upload – multipart PDF/Markdown
- POST /api/add-doc – add another file to current index
- POST /api/upload-url – form url=<github-url>
 -POST /api/ask – form: question, optional top_k
- POST /api/reset – clears FAISS + cached texts
- GET /api/index-status – { ready: boolean }

### 🧯Troubleshooting

**“Request failed with status code 404” (frontend):**
Check VITE_API_BASE points to your backend root (not /api).
Example: https://<space>.hf.space ✅

**No Hugging Face logs for requests:**
Likely your frontend is calling a different base URL. Open devtools → Network tab. Confirm request host.

413/429/503 or large PDFs failing:
Free CPU tiers are constrained. Keep PDFs small (≤ ~5–10 pages) or split. Use Add Document to build up gradually.

**Q&A disabled:**
You must Summarize & Index first. The app checks /api/index-status.

**Windows zip too large:**
Remove transient folders before zipping: backend/data/, __pycache__/, node_modules/, dist/.

### 🔐License & Terms
- See LICENSE (project license).
- See EULA-SELFHOST.txt (end-user terms for the self-hosted bundle).
- See NOTICE.md for acknowledgements.

### 🙌 Contributing / Issues

Issues and PRs are welcome for bug fixes and small improvements.
For feature requests, please open an issue first.

### 📫 Contact
For support or bundle questions: open a GitHub issue or contact via your listing page.
