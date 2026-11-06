class Connector:
    """Every data source is a connector.

    A connector has one job: return the source's content as a list of documents
    in the format made by make_document(). Chunking, embedding, the link graph
    and search are the same for every source, so a new connector (Confluence,
    Notion, Slack, Google Drive...) only needs to:

      1. subclass Connector
      2. implement fetch()
      3. add it to CONNECTORS in registry.py

    Systems that would rather push data than be pulled from can use the
    POST /api/workspaces/{id}/documents endpoint instead.
    """

    type = ""
    label = ""

    def __init__(self, workspace_id, source_id, settings):
        self.workspace_id = workspace_id
        self.source_id = source_id
        self.settings = settings

    def fetch(self, report_progress):
        """Return a list of documents. Call report_progress("some text") to update the UI."""
        raise NotImplementedError


def make_document(document_id, kind, title, text, url="", number=None, state=""):
    """The one document format every connector returns.

    kind is one of: docs, issue, pr, file, note. It decides the label and color in the UI.
    """
    return {
        "id": document_id,
        "kind": kind,
        "title": title,
        "url": url,
        "number": number,
        "state": state,
        "text": text,
    }
