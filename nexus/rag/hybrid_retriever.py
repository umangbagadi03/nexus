from nexus.indexing import dense_embedder, hybrid_store, sparse_embedder, vector_store
from nexus.rag.reranker import rerank

# Children that go into the reranker, and parent sections that come out
CHILD_CANDIDATES = 30
MAX_SECTIONS = 6

# A long page or issue thread can match many times. Capping it leaves room for other sources.
MAX_SECTIONS_PER_DOCUMENT = 2


def limit_per_document(sections, max_sections):
    picked = []
    count_by_document = {}

    for section in sections:
        document_id = section["document_id"]
        used = count_by_document.get(document_id, 0)
        if used >= MAX_SECTIONS_PER_DOCUMENT:
            continue

        picked.append(section)
        count_by_document[document_id] = used + 1

        if len(picked) == max_sections:
            break

    return picked


def search_children(workspace_id, query):
    dense_vector = dense_embedder.embed_query(query)
    sparse_vector = sparse_embedder.embed_query(query)
    collection = vector_store.chunks_collection(workspace_id)
    return vector_store.hybrid_search(collection, dense_vector, sparse_vector, CHILD_CANDIDATES)


def lift_to_parents(workspace_id, ranked_children, max_sections):
    """Children are ranked best first. Return their parent sections in the same order, without repeats."""
    sections = []
    seen_parent_ids = set()

    for child in ranked_children:
        parent_id = child["parent_id"]
        if parent_id in seen_parent_ids:
            continue
        seen_parent_ids.add(parent_id)

        parent = hybrid_store.get_parent(workspace_id, parent_id)
        if parent is None:
            continue

        parent = dict(parent)
        parent["score"] = child["rerank_score"]
        sections.append(parent)

    return limit_per_document(sections, max_sections)


def retrieve_sections(workspace_id, query, max_sections=MAX_SECTIONS):
    children = search_children(workspace_id, query)
    ranked_children = rerank(query, children)
    return lift_to_parents(workspace_id, ranked_children, max_sections)
