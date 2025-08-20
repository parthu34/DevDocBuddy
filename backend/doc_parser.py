# backend/doc_parser.py
import fitz  # PyMuPDF
import markdown
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
from typing import List, Optional, Tuple

def _clean_text(text: str) -> str:
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    lines = [ln.strip() for ln in text.splitlines()]
    filtered = [ln for ln in lines if not (len(ln) <= 3 and ln.isdigit())]
    return "\n".join(filtered).strip()

def parse_pdf_bytes(pdf_bytes: bytes, max_pages: Optional[int] = None) -> Tuple[str, int, int]:
    """Parse PDF bytes and return (clean_text, total_pages, pages_used)."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        total = len(doc)
        use = total if not max_pages else min(max_pages, total)
        pages = []
        for i in range(use):
            pages.append(doc[i].get_text())
    text = _clean_text("\n\n".join(pages))
    return text, total, use

def parse_pdf_file(file_path: str, max_pages: Optional[int] = None) -> Tuple[str, int, int]:
    with fitz.open(file_path) as doc:
        total = len(doc)
        use = total if not max_pages else min(max_pages, total)
        text = "\n".join(doc[i].get_text() for i in range(use))
    return _clean_text(text), total, use

def parse_markdown_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    return parse_markdown_text(md_content)

def parse_markdown_text(md_content: str) -> str:
    html = markdown.markdown(md_content, extensions=["fenced_code", "codehilite"])
    soup = BeautifulSoup(html, 'html.parser')
    return _clean_text(soup.get_text())

def fetch_github_readme(url: str) -> str:
    if "raw.githubusercontent.com" in url:
        raw_url = url
    else:
        if "github.com" in url and "/blob/" in url:
            parts = url.split("github.com/")[-1]
            owner_repo, _, branch_and_path = parts.partition("/blob/")
            raw_url = f"https://raw.githubusercontent.com/{owner_repo}/{branch_and_path}"
        else:
            if url.endswith("/"):
                url = url[:-1]
            raw_url = url + "/raw/HEAD/README.md"

    try:
        r = requests.get(raw_url, timeout=15)
        r.raise_for_status()
        md_text = r.text
        return parse_markdown_text(md_text)
    except Exception:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        return _clean_text(soup.get_text())

def split_text_to_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
