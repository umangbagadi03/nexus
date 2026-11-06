from nexus.indexing.chunker import document_fields, split_text

# Parents are what the LLM reads, children are what we search.
# Small children match precisely, big parents keep the full context.
PARENT_MIN_SIZE = 600
PARENT_MAX_SIZE = 4000
CHILD_SIZE = 700
CHILD_OVERLAP = 100


def is_section_start(line):
    # Markdown headings in docs and files, and each comment in an issue thread
    if line.startswith("## ") or line.startswith("### "):
        return True
    if line.startswith("Comment by ") and line.endswith(":"):
        return True
    return False


def split_into_sections(text):
    sections = []
    current_lines = []
    inside_code = False

    for line in text.splitlines():
        if line.strip().startswith("```"):
            inside_code = not inside_code

        # A '## ' inside a code block is a comment, not a heading
        if not inside_code and is_section_start(line) and current_lines:
            sections.append("\n".join(current_lines).strip())
            current_lines = []

        current_lines.append(line)

    if current_lines:
        sections.append("\n".join(current_lines).strip())

    return sections


def merge_small_sections(sections):
    """Tiny sections (a heading with two lines under it) are merged into the next one."""
    merged = []
    buffer = ""

    for section in sections:
        if buffer:
            buffer = buffer + "\n\n" + section
        else:
            buffer = section

        if len(buffer) >= PARENT_MIN_SIZE:
            merged.append(buffer)
            buffer = ""

    if buffer:
        if merged:
            merged[-1] = merged[-1] + "\n\n" + buffer
        else:
            merged.append(buffer)

    return merged


def build_parents(document):
    sections = split_into_sections(document["text"])
    sections = merge_small_sections(sections)

    # Very long sections are still split, so one parent never floods the prompt
    parent_texts = []
    for section in sections:
        if len(section) <= PARENT_MAX_SIZE:
            parent_texts.append(section)
        else:
            parent_texts.extend(split_text(section, PARENT_MAX_SIZE, 200))

    parents = []
    for index, parent_text in enumerate(parent_texts):
        parent = document_fields(document)
        parent["parent_id"] = document["id"] + "#p" + str(index)
        parent["text"] = parent_text
        parents.append(parent)
    return parents


def build_children(parent):
    children = []
    pieces = split_text(parent["text"], CHILD_SIZE, CHILD_OVERLAP)

    for index, piece in enumerate(pieces):
        child = {
            "child_id": parent["parent_id"] + "c" + str(index),
            "parent_id": parent["parent_id"],
            "document_id": parent["document_id"],
            "source_id": parent["source_id"],
            "source_name": parent["source_name"],
            "kind": parent["kind"],
            "title": parent["title"],
            "url": parent["url"],
            "number": parent["number"],
            "state": parent["state"],
            "text": piece,
        }
        children.append(child)
    return children


def chunk_into_parents_and_children(documents):
    all_parents = []
    all_children = []

    for document in documents:
        parents = build_parents(document)
        for parent in parents:
            all_parents.append(parent)
            all_children.extend(build_children(parent))

    return all_parents, all_children
