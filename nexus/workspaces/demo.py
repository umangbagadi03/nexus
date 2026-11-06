import os
import shutil

from nexus import config
from nexus.workspaces import store

# Sample workspaces, since a portfolio project has no company data of its own.
# GitLab publishes its internal handbook openly, and LangGraph has public docs,
# issues and pull requests. Together they look like a real company's knowledge:
# policies and runbooks on one side, engineering docs and tickets on the other.
# Acme is fictional: one small PDF to show file uploads, tables and scanned pages.

GITLAB_HANDBOOK = {
    "name": "GitLab Handbook",
    "description": "GitLab's company handbook: people policies, benefits, communication and incident management.",
    "example_questions": [
        "How should I report harassment, and who handles it?",
        "What should an incident manager do in the first minutes of an incident?",
        "When should I use Slack and when should I use an issue?",
        "What does GitLab's 360 feedback process look like?",
    ],
    "sources": [
        {
            "type": "markdown_repo",
            "name": "GitLab Handbook pages",
            "settings": {
                "provider": "gitlab",
                "repo": "gitlab-com/content-sites/handbook",
                "branch": "main",
                "folders": [
                    "content/handbook/people-group",
                    "content/handbook/communication",
                    "content/handbook/engineering/infrastructure-platforms/incident-management",
                    "content/handbook/total-rewards",
                ],
                "strip_prefix": "content/",
                "site_url": "https://handbook.gitlab.com",
                "max_pages": 130,
            },
        },
    ],
}

LANGGRAPH = {
    "name": "LangGraph",
    "description": "An engineering team's docs, issues and pull requests, from the open source LangGraph project.",
    "example_questions": [
        "My graph fails with GRAPH_RECURSION_LIMIT. How do I fix it?",
        "Is there a known memory leak with InMemorySaver?",
        "How do I pause a graph to ask a human for approval?",
        "What is the difference between a checkpointer and a store?",
    ],
    "sources": [
        {
            "type": "markdown_repo",
            "name": "LangGraph docs",
            "settings": {
                "provider": "github",
                "repo": "langchain-ai/docs",
                "branch": "main",
                "folders": ["src/oss/langgraph"],
                "strip_prefix": "src/oss/langgraph/",
                "site_url": "https://docs.langchain.com/oss/python/langgraph",
                "max_pages": 100,
            },
        },
        {
            "type": "github_issues",
            "name": "LangGraph issues and PRs",
            "settings": {
                "repo": "langchain-ai/langgraph",
                "max_items": 300,
            },
        },
    ],
}


ACME_BENEFITS = {
    "name": "Acme Benefits",
    "description": "A sample PDF for a fictional company, with tables and a scanned page.",
    "example_questions": [
        "How much does Acme pay per month for the Silver plan with family coverage?",
        "How many annual leave days does a Senior with 4 years of service get?",
        "What relocation allowance does an L5 employee get for an international move?",
    ],
    "sources": [
        {
            "type": "files",
            "name": "Benefits guide PDF",
            "settings": {},
            "sample_files": ["demo_data/acme-benefits-guide.pdf"],
        },
    ],
}


def copy_sample_files(workspace_id, source_id, paths):
    folder = config.uploads_dir(workspace_id, source_id)
    os.makedirs(folder, exist_ok=True)
    for path in paths:
        shutil.copy(path, folder)


def create_demo_workspaces():
    """Create the sample workspaces if they do not exist yet. Returns the ids of the new sources."""
    existing_ids = []
    for workspace in store.list_workspaces():
        existing_ids.append(workspace["id"])

    new_sources = []
    for template in [GITLAB_HANDBOOK, LANGGRAPH, ACME_BENEFITS]:
        workspace_id = store.make_id(template["name"])
        if workspace_id in existing_ids:
            continue

        store.create_workspace(template["name"], template["description"], template["example_questions"])
        for source in template["sources"]:
            created = store.add_source(workspace_id, source["type"], source["name"], source["settings"])
            copy_sample_files(workspace_id, created["id"], source.get("sample_files", []))
            new_sources.append((workspace_id, created["id"]))

    return new_sources
