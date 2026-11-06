from nexus.graph.link_graph import build_graph, page_key


def make_document(document_id, kind, text, number=None, url=""):
    return {"id": document_id, "kind": kind, "source_id": "s", "number": number, "url": url, "text": text}


def test_pull_request_that_fixes_an_issue_is_linked():
    graph = build_graph([
        make_document("issue-123", "issue", "It crashes", number=123),
        make_document("pr-200", "pr", "Fixes #123", number=200),
    ])
    assert graph.edges["pr-200", "issue-123"]["relation"] == "fixes"


def test_fixes_stays_when_the_issue_is_also_mentioned():
    graph = build_graph([
        make_document("issue-123", "issue", "It crashes", number=123),
        make_document("pr-200", "pr", "Fixes #123. See #123 for details.", number=200),
    ])
    assert graph.edges["pr-200", "issue-123"]["relation"] == "fixes"


def test_unknown_issue_numbers_and_self_links_are_ignored():
    graph = build_graph([make_document("issue-123", "issue", "Same as #123, and see #999", number=123)])
    assert graph.number_of_edges() == 0


def test_page_links_match_in_different_forms():
    assert page_key("https://example.com/handbook/people/leave/#scope") == "people/leave"
    assert page_key("/docs/people/leave.md") == "people/leave"


def test_link_between_pages():
    graph = build_graph([
        make_document("leave", "docs", "Leave policy", url="https://example.com/people/leave"),
        make_document("home", "docs", "See [leave](/people/leave)", url="https://example.com/people/home"),
    ])
    assert graph.edges["home", "leave"]["relation"] == "links to"
