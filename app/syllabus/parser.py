from pathlib import Path

import fitz
from docx import Document


def extract_text(file_path: str) -> str:
    """Extract text from PDF, DOCX or TXT files."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Syllabus not found: {path}")

    extension = path.suffix.lower()

    if extension == ".pdf":
        return extract_pdf(path)

    elif extension == ".docx":
        return extract_docx(path)

    elif extension == ".txt":
        return path.read_text(encoding="utf-8-sig")

    raise ValueError(f"Unsupported syllabus format: {extension}")


def extract_pdf(path: Path) -> str:
    text_parts = []

    with fitz.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append(
                    f"\n--- Page {page_number} ---\n{page_text}"
                )

    return "\n".join(text_parts)


def extract_docx(path: Path) -> str:
    document = Document(path)
    text_parts = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            text_parts.append(text)

    # Also extract content from tables.
    for table in document.tables:
        for row in table.rows:
            cells = [
                cell.text.strip().replace("\n", " ")
                for cell in row.cells
            ]
            text_parts.append(" | ".join(cells))

    return "\n".join(text_parts)