import os
import tarfile

from nexus import config
from nexus.ingestion import document_store
from nexus.workspaces import store

# A snapshot of the demo workspaces, so a server can start with them without fetching anything.
# It holds the documents, the parent sections and the link graph, not the vectors:
# the light search needs no vectors, and the full search builds them again from the documents.

SNAPSHOT_FILE = os.path.join("demo_data", "demo-workspaces.tar.gz")

# Per workspace, these files and folders go into the snapshot
KEPT_PARTS = [
    "raw",
    "uploads",
    os.path.join("index", "parents.json"),
    os.path.join("index", "graph.json"),
]


def save_snapshot():
    with tarfile.open(SNAPSHOT_FILE, "w:gz") as archive:
        archive.add(config.WORKSPACES_FILE)
        for workspace in store.list_workspaces():
            for part in KEPT_PARTS:
                path = os.path.join(config.workspace_dir(workspace["id"]), part)
                if os.path.exists(path):
                    archive.add(path)
    return SNAPSHOT_FILE


def load_snapshot(report=print):
    if os.path.exists(config.WORKSPACES_FILE):
        report("Workspaces already exist in " + config.DATA_DIR + ", so the snapshot was not loaded.")
        return

    with tarfile.open(SNAPSHOT_FILE, "r:gz") as archive:
        # "data" only lets plain files and folders out, nothing outside the target folder
        archive.extractall(".", filter="data")
    report("Loaded the demo workspaces from " + SNAPSHOT_FILE)

    if config.LIGHT_SEARCH:
        report("Light search needs no vector index, so nothing more to do.")
        return

    # Imported here, so the light search runs without the indexing libraries installed
    from nexus.indexing import indexer

    for workspace in store.list_workspaces():
        for source in workspace["sources"]:
            documents = []
            for document in document_store.load_all_documents(workspace["id"]):
                if document["source_id"] == source["id"]:
                    documents.append(document)

            report("Indexing " + workspace["id"] + " / " + source["id"] + ": " + str(len(documents)) + " documents")
            indexer.index_source(workspace["id"], source["id"], documents, report)
