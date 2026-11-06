from typing import List, Optional

from pydantic import BaseModel

from nexus.pipelines import DEFAULT_PIPELINE


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str = ""


class AskRequest(BaseModel):
    question: str
    pipeline: str = DEFAULT_PIPELINE


class GitHubIssuesSourceRequest(BaseModel):
    repo: str
    max_items: int = 200


class MarkdownRepoSourceRequest(BaseModel):
    provider: str = "github"
    repo: str
    branch: str = "main"
    folder: str
    site_url: str = ""
    max_pages: int = 200


class PushedDocument(BaseModel):
    id: str
    title: str
    text: str
    url: str = ""


class PushRequest(BaseModel):
    source_name: str = "API"
    documents: List[PushedDocument]


class EvalRequest(BaseModel):
    pipeline: str = "hybrid"
    retrieval_only: bool = True
    limit: Optional[int] = None
