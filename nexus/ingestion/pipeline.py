import os
import shutil
import threading
import traceback

from nexus import config
from nexus.connectors.pushed import inbox_file
from nexus.connectors.registry import make_connector
from nexus.graph.link_graph import build_graph, forget_graph, save_graph
from nexus.indexing import hybrid_store, indexer, vector_store
from nexus.ingestion import document_store
from nexus.workspaces import store

# Syncing uses a lot of CPU and memory for embeddings, so only one runs at a time
_sync_lock = threading.Lock()


def prepare_documents(source, documents):
    """Make document ids unique in the workspace and remember which source they came from."""
    prepared = []
    for document in documents:
        document = dict(document)
        document["id"] = source["id"] + "/" + str(document["id"])
        document["source_id"] = source["id"]
        document["source_name"] = source["name"]
        prepared.append(document)
    return prepared


def rebuild_graph(workspace_id):
    graph = build_graph(document_store.load_all_documents(workspace_id))
    save_graph(workspace_id, graph)
    return graph


def sync_source(workspace_id, source_id):
    """Fetch a source, index what changed, and rebuild the link graph."""

    def report_progress(message):
        store.update_source(workspace_id, source_id, {"status": "syncing", "message": message})

    store.update_source(workspace_id, source_id, {"status": "queued", "message": "Waiting for another sync to finish"})

    with _sync_lock:
        source = store.get_source(workspace_id, source_id)
        if source is None:
            return

        store.update_source(workspace_id, source_id, {"status": "syncing", "message": "Fetching documents"})

        try:
            connector = make_connector(workspace_id, source)
            documents = connector.fetch(report_progress)
            documents = prepare_documents(source, documents)
            document_store.save_source_documents(workspace_id, source_id, documents)

            report_progress("Indexing " + str(len(documents)) + " documents")
            result = indexer.index_source(workspace_id, source_id, documents, report_progress)

            report_progress("Linking documents")
            rebuild_graph(workspace_id)

            message = (
                str(result["indexed"]) + " indexed, "
                + str(result["unchanged"]) + " unchanged, "
                + str(result["removed"]) + " removed"
            )
            store.update_source(workspace_id, source_id, {
                "status": "ready",
                "message": message,
                "documents": len(documents),
                "last_synced": store.now_text(),
            })
        except Exception as error:
            traceback.print_exc()
            store.update_source(workspace_id, source_id, {"status": "failed", "message": str(error)})


def delete_workspace(workspace_id):
    """Remove a workspace: its search index, documents, link graph and uploaded files.
    Its eval questions and results in evals/ are kept."""
    with _sync_lock:
        vector_store.drop_collection(vector_store.chunks_collection(workspace_id))
        hybrid_store.forget_workspace(workspace_id)
        forget_graph(workspace_id)

        folder = config.workspace_dir(workspace_id)
        if os.path.exists(folder):
            shutil.rmtree(folder)

        store.remove_workspace(workspace_id)


def mark_interrupted_syncs():
    """A sync that was running when the server stopped will never finish. Say so in the UI."""
    for workspace in store.list_workspaces():
        for source in workspace["sources"]:
            if source["status"] in ("syncing", "queued"):
                store.update_source(workspace["id"], source["id"], {
                    "status": "failed",
                    "message": "The sync was interrupted. Sync again to finish it.",
                })


def start_sync(workspace_id, source_id):
    """Run a sync in the background, so the web app stays responsive."""
    thread = threading.Thread(target=sync_source, args=(workspace_id, source_id), daemon=True)
    thread.start()


def delete_source(workspace_id, source_id):
    with _sync_lock:
        indexer.remove_source(workspace_id, source_id)
        document_store.delete_source_documents(workspace_id, source_id)

        uploads = config.uploads_dir(workspace_id, source_id)
        if os.path.exists(uploads):
            shutil.rmtree(uploads)

        inbox = inbox_file(workspace_id, source_id)
        if os.path.exists(inbox):
            os.remove(inbox)

        store.remove_source(workspace_id, source_id)
        rebuild_graph(workspace_id)
