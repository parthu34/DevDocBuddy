import fitz  # PyMuPDF
import markdown
import requests
from bs4 import BeautifulSoup
from pathlib import Path

def parse_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    return text

def parse_markdown(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    html = markdown.markdown(md_content)
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()

def fetch_github_readme(url: str) -> str:
    if not url.endswith("README.md"):
        raise ValueError("Only README.md fetching is supported for now.")
    response = requests.get(url)
    response.raise_for_status()
    html = markdown.markdown(response.text)
    return BeautifulSoup(html, 'html.parser').get_text()
