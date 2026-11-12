from docx import Document as WordDocument
from pypdf import PdfReader

from nexus import config
from nexus.connectors.markdown_cleaner import clean_markdown, split_front_matter

SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".md", ".mdx", ".txt"]


def read_pdf(path):
    if config.PDF_PARSER == "docling":
        # Imported here because Docling is an optional install
        from nexus.connectors.docling_parser import read_pdf_with_docling
        return read_pdf_with_docling(path)
    if config.PDF_PARSER == "pypdf":
        return read_pdf_with_pypdf(path)
    raise ValueError("Unknown PDF_PARSER '" + config.PDF_PARSER + "'. Use pypdf or docling.")


def read_pdf_with_pypdf(path):
    """Each page becomes a '## Page N' section, so answers can say which page they came from."""
    reader = PdfReader(path)
    parts = []

    for index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append("## Page " + str(index + 1))
            parts.append(page_text.strip())

    return "", "\n\n".join(parts)


def read_word(path):
    """Word headings become markdown headings, so long documents are split at the right places."""
    document = WordDocument(path)
    parts = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        style = ""
        if paragraph.style is not None:
            style = paragraph.style.name
        if style.startswith("Heading 1") or style == "Title":
            parts.append("## " + text)
        elif style.startswith("Heading"):
            parts.append("### " + text)
        else:
            parts.append(text)

    return "", "\n\n".join(parts)


def read_markdown(path):
    with open(path, "r", encoding="utf-8", errors="replace") as file:
        raw_text = file.read()
    title, body = split_front_matter(raw_text)
    return title, clean_markdown(body)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as file:
        return "", file.read()


def read_file(path):
    """Return (title, text). The title is empty when the file does not have one."""
    lower_path = path.lower()

    if lower_path.endswith(".pdf"):
        return read_pdf(path)
    if lower_path.endswith(".docx"):
        return read_word(path)
    if lower_path.endswith(".md") or lower_path.endswith(".mdx"):
        return read_markdown(path)
    if lower_path.endswith(".txt"):
        return read_text(path)

    raise ValueError("Unsupported file type: " + path)


def is_supported(file_name):
    lower_name = file_name.lower()
    for extension in SUPPORTED_EXTENSIONS:
        if lower_name.endswith(extension):
            return True
    return False
