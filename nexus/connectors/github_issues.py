from nexus.connectors.base import Connector, make_document
from nexus.connectors.github_client import github_get

# Long comment threads are mostly noise after a point
MAX_COMMENTS_PER_ISSUE = 30


class GitHubIssuesConnector(Connector):
    """Issues and pull requests of a GitHub repository, with their comments.

    Settings:
      repo       for example "langchain-ai/langgraph"
      max_items  how many of the most recently updated issues and PRs to fetch
    """

    type = "github_issues"
    label = "GitHub issues and pull requests"

    def fetch(self, report_progress):
        repo = self.settings["repo"]
        max_items = int(self.settings.get("max_items", 300))

        documents = []
        page = 1

        while len(documents) < max_items:
            params = {
                "state": "all",
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            }
            items = github_get("/repos/" + repo + "/issues", params)
            if len(items) == 0:
                break

            for item in items:
                if len(documents) >= max_items:
                    break
                documents.append(self.build_document(repo, item))

                if len(documents) % 25 == 0:
                    report_progress("Fetched " + str(len(documents)) + " issues and pull requests")

            page += 1

        return documents

    def build_document(self, repo, item):
        number = item["number"]

        if "pull_request" in item:
            kind = "pr"
            kind_text = "Pull request"
        else:
            kind = "issue"
            kind_text = "Issue"

        state = get_state(item)

        labels = []
        for label in item.get("labels", []):
            labels.append(label["name"])

        lines = []
        lines.append("Title: " + item["title"])
        lines.append(kind_text + " #" + str(number) + " (" + state + ")")
        if labels:
            lines.append("Labels: " + ", ".join(labels))
        lines.append("")
        lines.append(item.get("body") or "")

        if item["comments"] > 0:
            for comment in fetch_comments(repo, number):
                lines.append("")
                lines.append("Comment by " + comment["author"] + ":")
                lines.append(comment["body"])

        return make_document(
            document_id=kind + "-" + str(number),
            kind=kind,
            title=item["title"],
            text="\n".join(lines),
            url=item["html_url"],
            number=number,
            state=state,
        )


def get_state(item):
    pull_request = item.get("pull_request")
    if pull_request and pull_request.get("merged_at"):
        return "merged"
    return item["state"]


def fetch_comments(repo, number):
    path = "/repos/" + repo + "/issues/" + str(number) + "/comments"
    raw_comments = github_get(path, {"per_page": MAX_COMMENTS_PER_ISSUE})

    comments = []
    for raw in raw_comments:
        user = raw.get("user") or {}

        # Skip bots like CI and changeset bots, they add no knowledge
        if user.get("type") == "Bot":
            continue

        comments.append({
            "author": user.get("login", "unknown"),
            "body": raw.get("body") or "",
        })
    return comments
