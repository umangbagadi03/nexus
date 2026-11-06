import hashlib
import json
import os

from qdrant_client.models import PointStruct

from nexus import config
from nexus.indexing import dense_embedder, hybrid_store, sparse_embedder, vector_store
from nexus.indexing.section_chunker import chunk_into_parents_and_children

BATCH_SIZE = 64


# The index state remembers a fingerprint of every indexed document,
# so a sync only re-indexes documents that are new or changed.

def state_file(workspace_id):
    return os.path.join(config.index_dir(workspace_id), "indexed.json")


def load_state(workspace_id):
    path = state_file(workspace_id)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_state(workspace_id, state):
    os.makedirs(config.index_dir(workspace_id), exist_ok=True)
    with open(state_file(workspace_id), "w", encoding="utf-8") as file:
        json.dump(state, file)


def fingerprint(document):
    content = document["title"] + "\n" + document.get("state", "") + "\n" + document["text"]
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def index_source(workspace_id, source_id, documents, report_progress):
    """Bring the index in line with the current documents of one source.

    New documents are added, changed ones are replaced, and documents that
    disappeared from the source are removed. Unchanged ones are skipped.
    """
    state = load_state(workspace_id)

    previous_ids = set()
    for document_id, entry in state.items():
        if entry["source_id"] == source_id:
            previous_ids.add(document_id)

    current_ids = set()
    to_index = []
    for document in documents:
        current_ids.add(document["id"])
        old_entry = state.get(document["id"])
        if old_entry is None or old_entry["hash"] != fingerprint(document):
            to_index.append(document)

    removed_ids = previous_ids - current_ids

    # Changed documents are deleted first, then added again
    to_delete = list(removed_ids)
    for document in to_index:
        if document["id"] in previous_ids:
            to_delete.append(document["id"])

    remove_documents(workspace_id, to_delete)
    add_documents(workspace_id, to_index, report_progress)

    for document_id in removed_ids:
        del state[document_id]
    for document in to_index:
        state[document["id"]] = {"source_id": source_id, "hash": fingerprint(document)}
    save_state(workspace_id, state)

    return {
        "indexed": len(to_index),
        "removed": len(removed_ids),
        "unchanged": len(documents) - len(to_index),
    }


def remove_source(workspace_id, source_id):
    state = load_state(workspace_id)

    document_ids = []
    for document_id, entry in state.items():
        if entry["source_id"] == source_id:
            document_ids.append(document_id)

    remove_documents(workspace_id, document_ids)

    for document_id in document_ids:
        del state[document_id]
    save_state(workspace_id, state)


def remove_documents(workspace_id, document_ids):
    if len(document_ids) == 0:
        return

    vector_store.delete_documents(vector_store.chunks_collection(workspace_id), document_ids)
    hybrid_store.remove_parents_of_documents(workspace_id, document_ids)
    hybrid_store.save_parents(workspace_id)


def add_documents(workspace_id, documents, report_progress):
    """Section-aware parents and small children, with a dense and a BM25 vector for each child.

    All pipelines search this one collection. The baseline only uses the dense vectors,
    the hybrid and agentic pipelines use both vectors plus the parent sections.
    """
    if len(documents) == 0:
        return

    collection = vector_store.chunks_collection(workspace_id)
    parents, children = chunk_into_parents_and_children(documents)

    for start in range(0, len(children), BATCH_SIZE):
        batch = children[start:start + BATCH_SIZE]

        # The title goes into the searched text so a child still knows what it belongs to
        texts = []
        for child in batch:
            texts.append(child["title"] + "\n" + child["text"])

        dense_vectors = dense_embedder.embed_texts(texts)
        sparse_vectors = sparse_embedder.embed_texts(texts)
        vector_store.ensure_collection(collection, len(dense_vectors[0]))

        points = []
        for index, child in enumerate(batch):
            vectors = {"dense": dense_vectors[index], "bm25": sparse_vectors[index]}
            points.append(PointStruct(id=vector_store.point_id(child["child_id"]), vector=vectors, payload=child))
        vector_store.upsert(collection, points)

        done = min(start + BATCH_SIZE, len(children))
        report_progress("Indexed " + str(done) + " of " + str(len(children)) + " chunks")

    hybrid_store.add_parents(workspace_id, parents)
    hybrid_store.save_parents(workspace_id)
