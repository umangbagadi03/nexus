import re

# JSX tags used by MDX docs sites, like <Info>, </Tip>, <a id="x" />
JSX_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*[^>]*>")

# MDX comments like {/* some note */}
MDX_COMMENT = re.compile(r"\{/\*.*?\*/\}", re.DOTALL)

# Hugo shortcodes used by the GitLab handbook, like {{% panel %}} or {{< note >}}
SHORTCODE = re.compile(r"\{\{[<%].*?[%>]\}\}", re.DOTALL)


def split_front_matter(text):
    """Return (title, body). The front matter is the block between the first two '---' lines."""
    title = ""
    if not text.startswith("---"):
        return title, text

    end = text.find("\n---", 3)
    if end == -1:
        return title, text

    front_matter = text[3:end]
    body = text[end + 4:]

    for line in front_matter.splitlines():
        if line.startswith("title:"):
            title = line.replace("title:", "", 1).strip().strip('"').strip("'")

    return title, body


def clean_markdown(text):
    """Turn MDX or Hugo markdown into plain markdown.

    Removes components, comments and shortcodes. In docs that show the same example
    in Python and JavaScript, only the Python version is kept.
    """
    text = MDX_COMMENT.sub("", text)
    text = SHORTCODE.sub("", text)

    kept_lines = []
    inside_js_block = False
    inside_code = False

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            inside_code = not inside_code

        if stripped == ":::js":
            inside_js_block = True
            continue

        if stripped == ":::python":
            continue

        if stripped == ":::":
            inside_js_block = False
            continue

        if inside_js_block:
            continue

        # Only remove tags outside code, so code samples stay untouched
        if not inside_code and not stripped.startswith("```"):
            line = JSX_TAG.sub("", line)

        kept_lines.append(line)

    cleaned = "\n".join(kept_lines)

    # Collapse the empty lines left behind by removed tags
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
