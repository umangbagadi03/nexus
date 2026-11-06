ANSWER_SYSTEM_PROMPT = """You answer questions for people at a company, using the company's own knowledge:
documents, pages, files, issues and pull requests. The workspace is called "{workspace_name}".
You get numbered sources found for the question.

Rules:
- Use only the sources. Do not add facts from memory.
- Cite every claim with the source number in square brackets, like [1] or [2][3].
- If the sources do not contain the answer, say so plainly and mention what is missing.
- When an issue or pull request is relevant, say whether it is open, closed or merged.
- A pull request marked closed was not merged, so its change did not land. Only merged means the change landed.
- Keep it short and practical. Use lists or a code block when it helps."""


def describe_source(document):
    """A short label for a source, shown to the model and in the UI."""
    kind = document["kind"]
    number = str(document.get("number"))
    state = document.get("state", "")

    if kind == "issue":
        return "Issue #" + number + ", " + state
    if kind == "pr":
        return "Pull request #" + number + ", " + state
    if kind == "file":
        return "Uploaded file"
    if kind == "note":
        return "Pushed document"

    source_name = document.get("source_name", "")
    if source_name:
        return "Page in " + source_name
    return "Page"


def build_system_prompt(workspace_name):
    return ANSWER_SYSTEM_PROMPT.replace("{workspace_name}", workspace_name)


def build_answer_prompt(question, documents):
    parts = []

    for document in documents:
        header = "[" + str(document["citation"]) + "] " + document["title"]
        header += " (" + describe_source(document) + ")"

        parts.append(header)
        parts.append("\n\n".join(document["passages"]))
        parts.append("")

    sources_text = "\n".join(parts)
    return "Sources:\n\n" + sources_text + "\nQuestion: " + question
