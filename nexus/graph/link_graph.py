import json
import os
import re

import networkx as nx

from nexus import config

# "fixes #123", "Closes #45", "resolved #6789"
FIXES_PATTERN = re.compile(r"\b(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#(\d+)", re.IGNORECASE)

# "#123" or a full link to an issue or pull request
MENTION_PATTERN = re.compile(r"(?:^|[\s(])#(\d{2,6})\b")
ISSUE_LINK_PATTERN = re.compile(r"github\.com/[\w.-]+/[\w.-]+/(?:issues|pull)/(\d+)")

# Links to other pages: markdown links and plain URLs
MARKDOWN_LINK_PATTERN = re.compile(r"\]\(([^)\s]+)\)")
URL_PATTERN = re.compile(r"https?://[^\s)\]>\"']+")

# The more useful kind of link wins when two documents are linked more than once
RELATION_PRIORITY = {"fixes": 3, "mentions": 2, "links to": 1}

_graphs = {}


def graph_file(workspace_id):
    return os.path.join(config.index_dir(workspace_id), "graph.json")


def page_key(link):
    """Reduce a link to its last two path parts, so different forms of the same link match.

    https://handbook.gitlab.com/handbook/people-group/anti-harassment/#scope -> people-group/anti-harassment
    /oss/langgraph/persistence                                             -> langgraph/persistence
    """
    # Drop the #anchor and ?query parts
    link = link.split("#")[0]
    link = link.split("?")[0]

    # Drop https://domain.com
    if "://" in link:
        without_scheme = link.split("://", 1)[1]
        if "/" in without_scheme:
            link = without_scheme.split("/", 1)[1]
        else:
            link = ""

    link = link.strip("/").lower()
    for extension in (".mdx", ".md", ".html"):
        if link.endswith(extension):
            link = link[:-len(extension)]

    parts = []
    for part in link.split("/"):
        if part and part not in (".", ".."):
            parts.append(part)

    if len(parts) == 0:
        return ""
    return "/".join(parts[-2:])


def find_links(document, issue_ids, page_ids):
    """Return a list of (target_id, relation) for everything this document points to."""
    text = document["text"]
    links = []

    # Issue numbers only make sense inside the same GitHub source
    numbers = issue_ids.get(document["source_id"], {})

    for match in FIXES_PATTERN.finditer(text):
        target_id = numbers.get(int(match.group(1)))
        if target_id:
            links.append((target_id, "fixes"))

    mentioned = MENTION_PATTERN.findall(text) + ISSUE_LINK_PATTERN.findall(text)
    for number in mentioned:
        target_id = numbers.get(int(number))
        if target_id:
            links.append((target_id, "mentions"))

    page_links = MARKDOWN_LINK_PATTERN.findall(text) + URL_PATTERN.findall(text)
    for link in page_links:
        key = page_key(link)
        target_id = page_ids.get(key)

        # Relative links like ../persistence.md only have one part, match on the page name
        if target_id is None and "/" not in key:
            target_id = page_ids.get("name:" + key)

        if target_id:
            links.append((target_id, "links to"))

    return links


def add_edge(graph, source_id, target_id, relation):
    if source_id == target_id:
        return

    if graph.has_edge(source_id, target_id):
        old_relation = graph.edges[source_id, target_id]["relation"]
        if RELATION_PRIORITY[old_relation] >= RELATION_PRIORITY[relation]:
            return

    graph.add_edge(source_id, target_id, relation=relation)


def build_graph(documents):
    issue_ids = {}
    page_ids = {}
    name_counts = {}

    for document in documents:
        if document["kind"] in ("issue", "pr"):
            if document["source_id"] not in issue_ids:
                issue_ids[document["source_id"]] = {}
            numbers = issue_ids[document["source_id"]]
            numbers[document["number"]] = document["id"]
        elif document["url"]:
            key = page_key(document["url"])
            page_ids[key] = document["id"]

            # Also index by the last part of the path, but only names that are unique
            name = key.split("/")[-1]
            name_counts[name] = name_counts.get(name, 0) + 1
            page_ids["name:" + name] = document["id"]

    for name, count in name_counts.items():
        if count > 1:
            del page_ids["name:" + name]

    graph = nx.DiGraph()
    for document in documents:
        graph.add_node(document["id"])

    for document in documents:
        for target_id, relation in find_links(document, issue_ids, page_ids):
            add_edge(graph, document["id"], target_id, relation)

    return graph


def save_graph(workspace_id, graph):
    os.makedirs(config.index_dir(workspace_id), exist_ok=True)

    edges = []
    for source_id, target_id, data in graph.edges(data=True):
        edges.append([source_id, target_id, data["relation"]])

    with open(graph_file(workspace_id), "w", encoding="utf-8") as file:
        json.dump({"nodes": list(graph.nodes), "edges": edges}, file)

    _graphs[workspace_id] = graph


def forget_graph(workspace_id):
    if workspace_id in _graphs:
        del _graphs[workspace_id]


def load_graph(workspace_id):
    if workspace_id in _graphs:
        return _graphs[workspace_id]

    graph = nx.DiGraph()
    path = graph_file(workspace_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            saved = json.load(file)
        graph.add_nodes_from(saved["nodes"])
        for source_id, target_id, relation in saved["edges"]:
            graph.add_edge(source_id, target_id, relation=relation)

    _graphs[workspace_id] = graph
    return graph


def get_neighbors(workspace_id, document_id):
    """Documents linked to this one in either direction, most useful links first."""
    graph = load_graph(workspace_id)
    if document_id not in graph:
        return []

    neighbors = []

    for target_id in graph.successors(document_id):
        relation = graph.edges[document_id, target_id]["relation"]
        neighbors.append({"document_id": target_id, "relation": relation})

    for source_id in graph.predecessors(document_id):
        relation = graph.edges[source_id, document_id]["relation"]
        neighbors.append({"document_id": source_id, "relation": relation})

    neighbors.sort(key=relation_rank, reverse=True)
    return neighbors


def relation_rank(neighbor):
    return RELATION_PRIORITY[neighbor["relation"]]
