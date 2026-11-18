from nexus.indexing import hybrid_store
from nexus.rag import keyword_search


def section(parent_id, title, text):
    document_id = parent_id.split("#")[0]
    return {"parent_id": parent_id, "document_id": document_id, "title": title, "text": text}


SECTIONS = {
    "a#p0": section("a#p0", "Memory leak", "InMemorySaver keeps every checkpoint, so memory grows."),
    "b#p0": section("b#p0", "Interrupts", "Pause a graph with interrupt to ask a human for approval."),
    "c#p0": section("c#p0", "Stores", "A store keeps data across threads."),
}


def use_sections(monkeypatch):
    def get_parents(workspace_id):
        return SECTIONS

    monkeypatch.setattr(hybrid_store, "get_parents", get_parents)
    keyword_search.forget_workspace("test")


def test_best_match_comes_first(monkeypatch):
    use_sections(monkeypatch)
    results = keyword_search.search_sections("test", "memory leak with InMemorySaver", 5)
    assert results[0]["parent_id"] == "a#p0"
    assert results[0]["score"] > 0


def test_sections_without_the_words_are_left_out(monkeypatch):
    use_sections(monkeypatch)
    results = keyword_search.search_sections("test", "human approval", 5)
    ids = []
    for result in results:
        ids.append(result["parent_id"])
    assert ids == ["b#p0"]


def test_words_ignore_case_and_punctuation():
    assert keyword_search.words("GRAPH_RECURSION_LIMIT, Fix it!") == ["graph_recursion_limit", "fix", "it"]
