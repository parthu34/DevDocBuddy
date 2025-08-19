import fitz  # PyMuPDF
import markdown
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
from typing import List


def _clean_text(text: str) -> str:
    # Basic cleanups: remove repeated blank lines, trim long whitespace
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)  # collapse multiple blank lines
    # Remove leading/trailing spaces on each line
    lines = [ln.strip() for ln in text.splitlines()]
    # Remove any lines that are just short noise (e.g., page numbers like "1", "-", etc.)
    filtered = [ln for ln in lines if not (len(ln) <= 3 and ln.isdigit())]
    return "\n".join(filtered).strip()


def parse_pdf_bytes(pdf_bytes: bytes) -> str:
    """(Legacy) Parse PDF bytes and return cleaned plain text."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        pages = []
        for page in doc:
            text = page.get_text()
            pages.append(text)
    text = "\n\n".join(pages)
    return _clean_text(text)


def parse_pdf_bytes_to_pages(pdf_bytes: bytes) -> List[str]:
    """Parse PDF bytes and return a CLEANED list of page texts (1-based pages)."""
    pages_clean = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            txt = page.get_text()
            pages_clean.append(_clean_text(txt))
    return pages_clean


def parse_pdf_file(file_path: str) -> str:
    doc = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    return _clean_text(text)


def parse_markdown_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    return parse_markdown_text(md_content)


def parse_markdown_text(md_content: str) -> str:
    html = markdown.markdown(md_content, extensions=["fenced_code", "codehilite"])
    soup = BeautifulSoup(html, 'html.parser')
    return _clean_text(soup.get_text())


def fetch_github_readme(url: str) -> str:
    """
    Accepts github.com URLs to README or repo root; convert to raw.githubusercontent URL if possible.
    If the URL already points to raw content, fetch directly.
    """
    if "raw.githubusercontent.com" in url:
        raw_url = url
    else:
        # try to convert common GitHub patterns to raw
        # example: https://github.com/owner/repo/blob/branch/README.md
        if "github.com" in url and "/blob/" in url:
            parts = url.split("github.com/")[-1]
            owner_repo, _, branch_and_path = parts.partition("/blob/")
            raw_url = f"https://raw.githubusercontent.com/{owner_repo}/{branch_and_path}"
        else:
            # If user passed repo root, try to fetch README from main/master
            if url.endswith("/"):
                url = url[:-1]
            raw_url = url + "/raw/HEAD/README.md"

    try:
        r = requests.get(raw_url, timeout=15)
        r.raise_for_status()
        md_text = r.text
        return parse_markdown_text(md_text)
    except Exception:
        # fallback: try GET the URL and extract visible text
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        return _clean_text(soup.get_text())


def split_text_to_sentences(text: str) -> List[str]:
    # quick sentence splitter fallback
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
