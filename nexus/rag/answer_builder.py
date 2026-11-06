from nexus.llm.provider import get_llm
from nexus.rag.prompts import build_answer_prompt, build_system_prompt, describe_source
from nexus.workspaces import store

# Pipelines send their progress as a series of events:
#   {"type": "status", "text": ...}   what is happening right now
#   {"type": "step", "step": ...}     a finished step of the agent
#   {"type": "token", "text": ...}    the next piece of the answer
#   {"type": "result", "result": ...} the finished answer, always the last event


def stream_answer_text(workspace_id, question, documents):
    workspace = store.get_workspace(workspace_id)
    system_prompt = build_system_prompt(workspace["name"])
    prompt = build_answer_prompt(question, documents)
    return get_llm().stream(system_prompt, prompt)


def final_result(events):
    """Run a pipeline's events to the end and return only the finished answer."""
    result = None
    for event in events:
        if event["type"] == "result":
            result = event["result"]
    return result


def build_sources(documents):
    """The source list that the API and the UI show next to the answer."""
    sources = []
    for document in documents:
        sources.append({
            "citation": document["citation"],
            "title": document["title"],
            "url": document["url"],
            "kind": document["kind"],
            "label": describe_source(document),
            "score": document["score"],
            "snippet": document["passages"][0][:320],
            "via": document.get("via", ""),
        })
    return sources


def make_result(question, answer, documents, steps, pipeline_name, seconds, check=None):
    return {
        "question": question,
        "answer": answer,
        "sources": build_sources(documents),
        "steps": steps,
        "check": check,
        "model": get_llm().name,
        "pipeline": pipeline_name,
        "seconds": round(seconds, 2),
    }
