import time

from nexus.agent.graph import build_agent
from nexus.rag.answer_builder import final_result, make_result

PIPELINE_NAME = "agentic"

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def stream_answer(workspace_id, question):
    """Corrective RAG: search, follow links, check relevance, search again if needed, answer, check the answer."""
    started = time.time()

    start_state = {
        "workspace_id": workspace_id,
        "question": question,
        "query": question,
        "attempt": 0,
        "candidates": [],
        "kept": [],
        "verdict": "",
        "better_query": "",
        "answer": "",
        "documents": [],
        "check": None,
        "steps": [],
    }

    # "custom" events come from inside the nodes, "values" is the full state after each node
    final_state = start_state
    steps_sent = 0
    for mode, data in get_agent().stream(start_state, stream_mode=["custom", "values"]):
        if mode == "custom":
            yield data
            continue

        final_state = data
        for step in data["steps"][steps_sent:]:
            yield {"type": "step", "step": step}
        steps_sent = len(data["steps"])

    result = make_result(
        question,
        final_state["answer"],
        final_state["documents"],
        final_state["steps"],
        PIPELINE_NAME,
        time.time() - started,
        final_state["check"],
    )
    yield {"type": "result", "result": result}


def answer_question(workspace_id, question):
    return final_result(stream_answer(workspace_id, question))
