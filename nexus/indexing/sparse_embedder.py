from fastembed import SparseTextEmbedding
from qdrant_client.models import SparseVector

# BM25 keyword vectors. They catch exact terms that dense vectors miss,
# like class names (InMemorySaver), error codes and issue numbers.
MODEL_NAME = "Qdrant/bm25"

_model = None


def get_model():
    global _model
    if _model is None:
        print("  loading keyword model", MODEL_NAME)
        _model = SparseTextEmbedding(MODEL_NAME)
    return _model


def to_qdrant_vector(embedding):
    return SparseVector(
        indices=embedding.indices.tolist(),
        values=embedding.values.tolist(),
    )


def embed_texts(texts):
    vectors = []
    for embedding in get_model().embed(texts, batch_size=16):
        vectors.append(to_qdrant_vector(embedding))
    return vectors


def embed_query(question):
    embeddings = list(get_model().query_embed(question))
    return to_qdrant_vector(embeddings[0])
