import json
import os
import re
import threading
from datetime import datetime, timezone

from nexus import config

# Workspaces and their sources live in one small JSON file.
# Syncs run in background threads, so every read and write goes through this lock.
_lock = threading.Lock()


def now_text():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_id(name):
    """'GitLab Handbook' -> 'gitlab-handbook'"""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "item"


def _load():
    if not os.path.exists(config.WORKSPACES_FILE):
        return {"workspaces": []}
    with open(config.WORKSPACES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def _save(data):
    os.makedirs(os.path.dirname(config.WORKSPACES_FILE), exist_ok=True)
    with open(config.WORKSPACES_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def list_workspaces():
    with _lock:
        return _load()["workspaces"]


def get_workspace(workspace_id):
    for workspace in list_workspaces():
        if workspace["id"] == workspace_id:
            return workspace
    return None


def create_workspace(name, description, example_questions):
    with _lock:
        data = _load()
        workspace = {
            "id": make_id(name),
            "name": name,
            "description": description,
            "example_questions": example_questions,
            "sources": [],
        }
        data["workspaces"].append(workspace)
        _save(data)
        return workspace


def remove_workspace(workspace_id):
    with _lock:
        data = _load()
        kept = []
        for workspace in data["workspaces"]:
            if workspace["id"] != workspace_id:
                kept.append(workspace)
        data["workspaces"] = kept
        _save(data)


def add_source(workspace_id, source_type, name, settings):
    with _lock:
        data = _load()
        workspace = _find(data, workspace_id)

        source_id = make_id(name)
        existing_ids = []
        for source in workspace["sources"]:
            existing_ids.append(source["id"])

        # Two sources with the same name get different ids
        unique_id = source_id
        counter = 2
        while unique_id in existing_ids:
            unique_id = source_id + "-" + str(counter)
            counter += 1

        source = {
            "id": unique_id,
            "type": source_type,
            "name": name,
            "settings": settings,
            "status": "new",
            "message": "",
            "documents": 0,
            "last_synced": None,
        }
        workspace["sources"].append(source)
        _save(data)
        return source


def get_source(workspace_id, source_id):
    workspace = get_workspace(workspace_id)
    if workspace is None:
        return None
    for source in workspace["sources"]:
        if source["id"] == source_id:
            return source
    return None


def update_source(workspace_id, source_id, changes):
    with _lock:
        data = _load()
        workspace = _find(data, workspace_id)
        for source in workspace["sources"]:
            if source["id"] == source_id:
                source.update(changes)
        _save(data)


def remove_source(workspace_id, source_id):
    with _lock:
        data = _load()
        workspace = _find(data, workspace_id)

        kept = []
        for source in workspace["sources"]:
            if source["id"] != source_id:
                kept.append(source)
        workspace["sources"] = kept
        _save(data)


def _find(data, workspace_id):
    for workspace in data["workspaces"]:
        if workspace["id"] == workspace_id:
            return workspace
    raise ValueError("No workspace called '" + workspace_id + "'")
