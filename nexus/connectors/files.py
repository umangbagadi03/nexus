import os

from nexus import config
from nexus.connectors.base import Connector, make_document
from nexus.connectors.file_parsers import is_supported, read_file


class FilesConnector(Connector):
    """Files uploaded in the web app: PDF, Word, Markdown and plain text.

    The files are stored in data/workspaces/<workspace>/uploads/<source>/.
    """

    type = "files"
    label = "Uploaded files"

    def fetch(self, report_progress):
        folder = config.uploads_dir(self.workspace_id, self.source_id)
        if not os.path.exists(folder):
            return []

        file_names = sorted(os.listdir(folder))
        documents = []

        for file_name in file_names:
            if not is_supported(file_name):
                continue

            report_progress("Reading " + file_name)
            path = os.path.join(folder, file_name)
            title, text = read_file(path)

            if not text.strip():
                report_progress("No text found in " + file_name + ", it may be a scanned PDF")
                continue

            if not title:
                title = os.path.splitext(file_name)[0]

            documents.append(make_document(
                document_id=file_name,
                kind="file",
                title=title,
                text="Title: " + title + "\n\n" + text,
                url="/files/" + self.workspace_id + "/" + self.source_id + "/" + file_name,
            ))

        return documents
