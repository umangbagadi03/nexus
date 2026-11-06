import json


def parse_json_reply(text):
    """LLMs often wrap JSON in ```json fences or add a sentence around it.
    Take the part between the first '{' and the last '}' and parse that."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
