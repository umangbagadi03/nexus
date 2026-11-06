def split_text(text, chunk_size, overlap):
    """Split text into pieces of about chunk_size characters, with some overlap between them.

    It tries to end each piece at a line break so sentences are not cut in the middle too often.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        if end < text_length:
            last_line_break = text.rfind("\n", start, end)
            if last_line_break > start + chunk_size // 2:
                end = last_line_break

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= text_length:
            break

        start = end - overlap

    return chunks


def document_fields(document):
    """The fields every chunk and section carries, so search results can be shown without another lookup."""
    return {
        "document_id": document["id"],
        "source_id": document["source_id"],
        "source_name": document.get("source_name", ""),
        "kind": document["kind"],
        "title": document["title"],
        "url": document["url"],
        "number": document.get("number"),
        "state": document.get("state", ""),
    }

