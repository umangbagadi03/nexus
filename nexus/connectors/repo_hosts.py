import requests

from nexus import config
from nexus.connectors.github_client import github_get

# Listing and downloading files from a Git repository on GitHub or GitLab.
# Only public repositories, or private ones the token in .env can read.

GITLAB_API = "https://gitlab.com/api/v4"


def list_files(provider, repo, branch, folder):
    if provider == "github":
        return list_github_files(repo, branch, folder)
    if provider == "gitlab":
        return list_gitlab_files(repo, branch, folder)
    raise ValueError("Unknown provider '" + provider + "'. Use github or gitlab.")


def download_file(provider, repo, branch, path):
    if provider == "github":
        url = "https://raw.githubusercontent.com/" + repo + "/" + branch + "/" + path
    else:
        url = "https://gitlab.com/" + repo + "/-/raw/" + branch + "/" + path

    response = requests.get(url, headers=gitlab_headers(), timeout=30)
    response.raise_for_status()
    return response.text


def list_github_files(repo, branch, folder):
    tree = github_get("/repos/" + repo + "/git/trees/" + branch, {"recursive": "1"})

    paths = []
    for entry in tree["tree"]:
        if entry["type"] == "blob" and entry["path"].startswith(folder + "/"):
            paths.append(entry["path"])
    return paths


def gitlab_headers():
    if config.GITLAB_TOKEN:
        return {"PRIVATE-TOKEN": config.GITLAB_TOKEN}
    return {}


def list_gitlab_files(repo, branch, folder):
    # GitLab wants the project path URL-encoded: group/project -> group%2Fproject
    project = requests.utils.quote(repo, safe="")
    url = GITLAB_API + "/projects/" + project + "/repository/tree"

    paths = []
    page = 1
    while True:
        params = {"path": folder, "ref": branch, "recursive": "true", "per_page": 100, "page": page}
        response = requests.get(url, params=params, headers=gitlab_headers(), timeout=30)
        response.raise_for_status()

        entries = response.json()
        for entry in entries:
            if entry["type"] == "blob":
                paths.append(entry["path"])

        next_page = response.headers.get("X-Next-Page")
        if not next_page:
            break
        page = int(next_page)

    return paths
