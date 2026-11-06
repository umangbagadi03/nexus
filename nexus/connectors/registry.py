from nexus.connectors.files import FilesConnector
from nexus.connectors.github_issues import GitHubIssuesConnector
from nexus.connectors.markdown_repo import MarkdownRepoConnector
from nexus.connectors.pushed import PushedConnector

# Add new connectors here
CONNECTORS = {
    FilesConnector.type: FilesConnector,
    MarkdownRepoConnector.type: MarkdownRepoConnector,
    GitHubIssuesConnector.type: GitHubIssuesConnector,
    PushedConnector.type: PushedConnector,
}


def make_connector(workspace_id, source):
    connector_class = CONNECTORS.get(source["type"])
    if connector_class is None:
        raise ValueError("Unknown source type '" + source["type"] + "'")
    return connector_class(workspace_id, source["id"], source["settings"])
