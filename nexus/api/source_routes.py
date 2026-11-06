import os
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from nexus import config
from nexus.api.schemas import GitHubIssuesSourceRequest, MarkdownRepoSourceRequest, PushRequest
from nexus.api.workspace_routes import find_workspace
from nexus.connectors.file_parsers import SUPPORTED_EXTENSIONS, is_supported
from nexus.connectors.pushed import add_to_inbox
from nexus.ingestion import pipeline
from nexus.workspaces import store

router = APIRouter()


def find_source(workspace_id, source_id):
    source = store.get_source(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="No source called '" + source_id + "'")
    return source


def find_or_create_source(workspace_id, source_type, name, settings):
    workspace = find_workspace(workspace_id)
    for source in workspace["sources"]:
        if source["type"] == source_type and source["name"] == name:
            return source
    return store.add_source(workspace_id, source_type, name, settings)


@router.post("/api/workspaces/{workspace_id}/sources/upload")
async def upload_files(workspace_id: str, files: List[UploadFile] = File(...), source_name: str = Form("Uploaded files")):
    """Save uploaded files into a files source, then index them in the background."""
    for upload in files:
        if not is_supported(upload.filename):
            allowed = ", ".join(SUPPORTED_EXTENSIONS)
            raise HTTPException(status_code=400, detail=upload.filename + " is not supported. Use " + allowed)

    source = find_or_create_source(workspace_id, "files", source_name, {})
    folder = config.uploads_dir(workspace_id, source["id"])
    os.makedirs(folder, exist_ok=True)

    for upload in files:
        # Only keep the file name, never a path someone typed into it
        file_name = os.path.basename(upload.filename)
        content = await upload.read()
        with open(os.path.join(folder, file_name), "wb") as file:
            file.write(content)

    pipeline.start_sync(workspace_id, source["id"])
    return store.get_source(workspace_id, source["id"])


@router.post("/api/workspaces/{workspace_id}/sources/github-issues")
def add_github_issues(workspace_id: str, request: GitHubIssuesSourceRequest):
    find_workspace(workspace_id)
    settings = {"repo": request.repo.strip(), "max_items": request.max_items}
    source = store.add_source(workspace_id, "github_issues", request.repo + " issues", settings)
    pipeline.start_sync(workspace_id, source["id"])
    return source


@router.post("/api/workspaces/{workspace_id}/sources/markdown-repo")
def add_markdown_repo(workspace_id: str, request: MarkdownRepoSourceRequest):
    find_workspace(workspace_id)
    folder = request.folder.strip().strip("/")
    settings = {
        "provider": request.provider,
        "repo": request.repo.strip(),
        "branch": request.branch.strip() or "main",
        "folders": [folder],
        "strip_prefix": folder + "/",
        "site_url": request.site_url.strip(),
        "max_pages": request.max_pages,
    }
    source = store.add_source(workspace_id, "markdown_repo", request.repo + " docs", settings)
    pipeline.start_sync(workspace_id, source["id"])
    return source


@router.post("/api/workspaces/{workspace_id}/documents")
def push_documents(workspace_id: str, request: PushRequest):
    """Push API: any system can send documents here. Sending the same id again updates it."""
    if len(request.documents) == 0:
        raise HTTPException(status_code=400, detail="Send at least one document.")

    source = find_or_create_source(workspace_id, "pushed", request.source_name, {})

    documents = []
    for document in request.documents:
        documents.append(document.model_dump())
    total = add_to_inbox(workspace_id, source["id"], documents)

    pipeline.start_sync(workspace_id, source["id"])
    return {"source_id": source["id"], "received": len(documents), "total_in_source": total}


@router.post("/api/workspaces/{workspace_id}/sources/{source_id}/sync")
def sync_source(workspace_id: str, source_id: str):
    find_source(workspace_id, source_id)
    pipeline.start_sync(workspace_id, source_id)
    return {"status": "queued"}


@router.delete("/api/workspaces/{workspace_id}/sources/{source_id}")
def delete_source(workspace_id: str, source_id: str):
    source = find_source(workspace_id, source_id)
    if source["status"] in ("syncing", "queued"):
        raise HTTPException(status_code=409, detail="Wait for the sync to finish before removing this source.")
    pipeline.delete_source(workspace_id, source_id)
    return {"removed": source_id}
