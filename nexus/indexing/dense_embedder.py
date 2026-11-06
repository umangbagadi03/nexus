from fastembed import TextEmbedding

from nexus import config

# Embeddings run locally on CPU, so indexing costs nothing.
# The model is loaded once, the first time it is needed.
_model = None


def get_model():
    global _model
    if _model is None:
        print("  loading embedding model", config.EMBEDDING_MODEL)
        _model = TextEmbedding(config.EMBEDDING_MODEL)
    return _model


def embed_texts(texts):
    model = get_model()
    vectors = []
    for vector in model.embed(texts, batch_size=16):
        vectors.append(vector.tolist())
    return vectors


def embed_query(question):
    model = get_model()
    vectors = list(model.query_embed(question))
    return vectors[0].tolist()
