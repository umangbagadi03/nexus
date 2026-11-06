import time

from nexus import config
from nexus.rag.answer_builder import final_result, make_result, stream_answer_text
from nexus.rag.retriever import group_by_document, retrieve

PIPELINE_NAME = "baseline"


def stream_answer(workspace_id, question):
    """Plain RAG: embed the question, take the closest chunks by vector search, ask the LLM once.

    This is the starting point that the other pipelines are measured against.
    """
    started = time.time()

    yield {"type": "status", "text": "Searching"}
    chunks = retrieve(workspace_id, question, config.TOP_K)
    documents = group_by_document(chunks)

    yield {"type": "status", "text": "Writing the answer"}
    answer = ""
    for text in stream_answer_text(workspace_id, question, documents):
        answer += text
        yield {"type": "token", "text": text}

    result = make_result(question, answer, documents, [], PIPELINE_NAME, time.time() - started)
    yield {"type": "result", "result": result}


def answer_question(workspace_id, question):
    return final_result(stream_answer(workspace_id, question))
