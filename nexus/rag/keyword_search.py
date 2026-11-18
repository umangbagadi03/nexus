import re
import threading

from rank_bm25 import BM25Okapi

from nexus.indexing import hybrid_store

# Light search for small servers, turned on with LIGHT_SEARCH=true.
# Plain BM25 keyword search over the parent sections, with no embedding model,
# reranker or vector store, so it fits in a few hundred MB of memory.
# The full hybrid search is better: the evals were run with it.

_index_by_workspace = {}
_lock = threading.Lock()

# Common words that say nothing about the topic. Without this, "when should I use"
# matches every page that happens to use those words a lot.
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do", "does", "for", "from",
    "how", "i", "if", "in", "into", "is", "it", "its", "me", "my", "of", "on", "or", "our",
    "should", "so", "that", "the", "their", "there", "this", "to", "use", "was", "we", "what",
    "when", "where", "which", "who", "why", "will", "with", "you", "your",
}


def words(text):
    kept = []
    for word in re.findall(r"[a-z0-9_]+", text.lower()):
        if word not in STOP_WORDS:
            kept.append(word)
    return kept


def get_index(workspace_id):
    """The BM25 index and its sections, built once per workspace."""
    with _lock:
        if workspace_id not in _index_by_workspace:
            sections = list(hybrid_store.get_parents(workspace_id).values())
            index = None
            if len(sections) > 0:
                tokenized = []
                for section in sections:
                    tokenized.append(words(section["title"] + " " + section["text"]))
                index = BM25Okapi(tokenized)
            _index_by_workspace[workspace_id] = (index, sections)
        return _index_by_workspace[workspace_id]


def forget_workspace(workspace_id):
    with _lock:
        if workspace_id in _index_by_workspace:
            del _index_by_workspace[workspace_id]


def search_sections(workspace_id, query, limit):
    """The best matching sections, best first, each with its BM25 score."""
    index, sections = get_index(workspace_id)
    if index is None:
        return []

    scores = index.get_scores(words(query))

    scored = []
    for position in range(len(sections)):
        if scores[position] > 0:
            scored.append((scores[position], position))
    scored.sort(reverse=True)

    results = []
    for score, position in scored[:limit]:
        section = dict(sections[position])
        section["score"] = round(float(score), 4)
        results.append(section)
    return results
