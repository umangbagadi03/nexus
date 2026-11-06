import time

from nexus.rag.answer_builder import final_result, make_result, stream_answer_text
from nexus.rag.hybrid_retriever import retrieve_sections
from nexus.rag.retriever import group_by_document

PIPELINE_NAME = "hybrid"


def stream_answer(workspace_id, question):
    """Hybrid search (dense + BM25 + RRF), reranker and parent sections, then one LLM call.

    No grading or retries. This shows how much better retrieval alone helps.
    """
    started = time.time()

    yield {"type": "status", "text": "Searching"}
    sections = retrieve_sections(workspace_id, question)
    documents = group_by_document(sections)

    yield {"type": "status", "text": "Writing the answer"}
    answer = ""
    for text in stream_answer_text(workspace_id, question, documents):
        answer += text
        yield {"type": "token", "text": text}

    result = make_result(question, answer, documents, [], PIPELINE_NAME, time.time() - started)
    yield {"type": "result", "result": result}


def answer_question(workspace_id, question):
    return final_result(stream_answer(workspace_id, question))
