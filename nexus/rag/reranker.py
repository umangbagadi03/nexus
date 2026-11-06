from fastembed.rerank.cross_encoder import TextCrossEncoder

# A cross-encoder reads the question and a passage together, so it judges relevance
# much better than vector similarity. It is slower, so it only runs on the top candidates.
MODEL_NAME = "Xenova/ms-marco-MiniLM-L-12-v2"

_model = None


def get_model():
    global _model
    if _model is None:
        print("  loading reranker", MODEL_NAME)
        _model = TextCrossEncoder(MODEL_NAME)
    return _model


def rerank(question, candidates):
    """Score each candidate against the question and return them best first."""
    if len(candidates) == 0:
        return []

    passages = []
    for candidate in candidates:
        passages.append(candidate["title"] + "\n" + candidate["text"])

    scores = list(get_model().rerank(question, passages))

    for index, candidate in enumerate(candidates):
        candidate["rerank_score"] = round(float(scores[index]), 4)

    candidates.sort(key=rerank_score, reverse=True)
    return candidates


def rerank_score(candidate):
    return candidate["rerank_score"]
