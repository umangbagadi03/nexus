import time

from nexus.rag.answer_builder import final_result, make_result
from nexus.rag.hybrid_retriever import retrieve_sections
from nexus.rag.retriever import group_by_document

PIPELINE_NAME = "search"


def stream_answer(workspace_id, question):
    """Search without a model: the best matching sections and where they come from, no written answer.

    The server uses this when it has no model of its own and the visitor brought no API key.
    Search runs locally, so it is free.
    """
    started = time.time()

    yield {"type": "status", "text": "Searching"}
    sections = retrieve_sections(workspace_id, question)
    documents = group_by_document(sections)

    result = make_result(question, "", documents, [], PIPELINE_NAME, time.time() - started, "")
    result["search_only"] = True
    yield {"type": "result", "result": result}
