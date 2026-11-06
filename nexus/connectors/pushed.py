import os

from nexus import config
from nexus.connectors.base import Connector, make_document
from nexus.utils.jsonl import read_jsonl, write_jsonl


class PushedConnector(Connector):
    """Documents sent to the push API (POST /api/workspaces/{id}/documents).

    Instead of Nexus pulling from a system, the system sends its documents.
    They are kept in an inbox file, and syncing indexes what is in the inbox.
    """

    type = "pushed"
    label = "Pushed through the API"

    def fetch(self, report_progress):
        return read_jsonl(inbox_file(self.workspace_id, self.source_id))


def inbox_file(workspace_id, source_id):
    return os.path.join(config.workspace_dir(workspace_id), "inbox", source_id + ".jsonl")


def add_to_inbox(workspace_id, source_id, pushed_documents):
    """Pushed documents replace earlier ones with the same id, so pushing again updates them."""
    path = inbox_file(workspace_id, source_id)

    documents_by_id = {}
    for document in read_jsonl(path):
        documents_by_id[document["id"]] = document

    for pushed in pushed_documents:
        document = make_document(
            document_id=pushed["id"],
            kind="note",
            title=pushed["title"],
            text="Title: " + pushed["title"] + "\n\n" + pushed["text"],
            url=pushed.get("url", ""),
        )
        documents_by_id[document["id"]] = document

    write_jsonl(path, list(documents_by_id.values()))
    return len(documents_by_id)
