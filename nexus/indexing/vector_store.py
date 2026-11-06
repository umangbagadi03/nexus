import atexit
import threading
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    Fusion,
    FusionQuery,
    MatchAny,
    Modifier,
    Prefetch,
    SparseVectorParams,
    VectorParams,
)

from nexus import config

# Qdrant runs in local mode: it stores everything in a folder, no server needed.
# Local mode allows only one process to open the folder, and syncs run in
# background threads, so every call goes through this lock.
_client = None
_lock = threading.Lock()

# How many candidates each search brings before fusion
CANDIDATES_PER_SEARCH = 30


def get_client():
    global _client
    if _client is None:
        _client = QdrantClient(path=config.QDRANT_DIR)
        # Close it ourselves before Python shuts down, otherwise Qdrant prints an error on exit
        atexit.register(_client.close)
    return _client


def chunks_collection(workspace_id):
    return workspace_id + "__chunks"


def point_id(text_id):
    """Qdrant ids must be numbers or UUIDs. The same chunk id always gives the same UUID."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, text_id))


def ensure_collection(name, vector_size):
    with _lock:
        client = get_client()
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config={"dense": VectorParams(size=vector_size, distance=Distance.COSINE)},
                sparse_vectors_config={"bm25": SparseVectorParams(modifier=Modifier.IDF)},
            )


def upsert(name, points):
    with _lock:
        get_client().upsert(collection_name=name, points=points)


def delete_documents(name, document_ids):
    if len(document_ids) == 0:
        return

    with _lock:
        client = get_client()
        if not client.collection_exists(name):
            return

        condition = FieldCondition(key="document_id", match=MatchAny(any=list(document_ids)))
        client.delete(
            collection_name=name,
            points_selector=FilterSelector(filter=Filter(must=[condition])),
        )


def drop_collection(name):
    with _lock:
        client = get_client()
        if client.collection_exists(name):
            client.delete_collection(name)


def dense_search(name, query_vector, limit):
    """Vector search only. This is what the baseline pipeline uses."""
    with _lock:
        client = get_client()
        if not client.collection_exists(name):
            return []
        response = client.query_points(collection_name=name, query=query_vector, using="dense", limit=limit)

    results = []
    for point in response.points:
        result = dict(point.payload)
        result["score"] = round(point.score, 4)
        results.append(result)
    return results


def hybrid_search(name, dense_vector, sparse_vector, limit):
    """Run dense and keyword search, then merge both lists with Reciprocal Rank Fusion."""
    with _lock:
        client = get_client()
        if not client.collection_exists(name):
            return []
        response = client.query_points(
            collection_name=name,
            prefetch=[
                Prefetch(query=dense_vector, using="dense", limit=CANDIDATES_PER_SEARCH),
                Prefetch(query=sparse_vector, using="bm25", limit=CANDIDATES_PER_SEARCH),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=limit,
        )

    results = []
    for point in response.points:
        result = dict(point.payload)
        result["fusion_score"] = round(point.score, 4)
        results.append(result)
    return results
