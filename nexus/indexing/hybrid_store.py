import json
import os
import threading

from nexus import config

# Parent sections are stored in a JSON file per workspace, not in Qdrant.
# Qdrant holds the small children that are searched, this file holds the
# bigger parent sections that the LLM reads.

_parents_by_workspace = {}
_lock = threading.Lock()


def parents_file(workspace_id):
    return os.path.join(config.index_dir(workspace_id), "parents.json")


def get_parents(workspace_id):
    with _lock:
        if workspace_id not in _parents_by_workspace:
            path = parents_file(workspace_id)
            parents = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    parents = json.load(file)
            _parents_by_workspace[workspace_id] = parents
        return _parents_by_workspace[workspace_id]


def save_parents(workspace_id):
    parents = get_parents(workspace_id)
    with _lock:
        os.makedirs(config.index_dir(workspace_id), exist_ok=True)
        with open(parents_file(workspace_id), "w", encoding="utf-8") as file:
            json.dump(parents, file, ensure_ascii=False)


def forget_workspace(workspace_id):
    with _lock:
        if workspace_id in _parents_by_workspace:
            del _parents_by_workspace[workspace_id]


def add_parents(workspace_id, new_parents):
    parents = get_parents(workspace_id)
    for parent in new_parents:
        parents[parent["parent_id"]] = parent


def remove_parents_of_documents(workspace_id, document_ids):
    parents = get_parents(workspace_id)
    document_id_set = set(document_ids)

    to_remove = []
    for parent_id, parent in parents.items():
        if parent["document_id"] in document_id_set:
            to_remove.append(parent_id)

    for parent_id in to_remove:
        del parents[parent_id]


def get_parent(workspace_id, parent_id):
    return get_parents(workspace_id).get(parent_id)


def get_first_parent_of_document(workspace_id, document_id):
    return get_parent(workspace_id, document_id + "#p0")
