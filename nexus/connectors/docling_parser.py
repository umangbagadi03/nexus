from docling.document_converter import DocumentConverter

# Docling understands page layout: it keeps tables as tables and can read scanned
# pages with OCR. It needs PyTorch and AI models, so it is an optional install:
# pip install -r requirements-docling.txt

# The models take a lot of memory, so they are not kept loaded after a file is read.
# That leaves room for the embedding step that comes next.


def read_pdf_with_docling(path):
    """Each page becomes a '## Page N' section, the same as with pypdf, so citations still work."""
    document = DocumentConverter().convert(path).document
    parts = []

    for page_number in sorted(document.pages):
        page_text = document.export_to_markdown(page_no=page_number, image_placeholder="").strip()
        if page_text:
            parts.append("## Page " + str(page_number))
            parts.append(page_text)

    return "", "\n\n".join(parts)
