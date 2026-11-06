from nexus.indexing import vector_store
from nexus.indexing.dense_embedder import embed_query


def retrieve(workspace_id, question, top_k):
    """Baseline retrieval: the closest small chunks by dense vector only. No keywords, reranker or parent sections."""
    query_vector = embed_query(question)
    collection = vector_store.chunks_collection(workspace_id)
    return vector_store.dense_search(collection, query_vector, top_k)


def group_by_document(chunks):
    """Several chunks can come from the same page or issue. Show each document once."""
    documents = []
    documents_by_id = {}

    for chunk in chunks:
        document_id = chunk["document_id"]

        if document_id not in documents_by_id:
            document = {
                "document_id": document_id,
                "title": chunk["title"],
                "url": chunk["url"],
                "kind": chunk["kind"],
                "source_name": chunk.get("source_name", ""),
                "state": chunk.get("state", ""),
                "number": chunk.get("number"),
                "score": chunk["score"],
                "via": chunk.get("via", ""),
                "passages": [],
            }
            documents_by_id[document_id] = document
            documents.append(document)

        documents_by_id[document_id]["passages"].append(chunk["text"])

    for index, document in enumerate(documents):
        document["citation"] = index + 1

    return documents
