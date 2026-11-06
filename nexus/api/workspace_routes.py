import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from nexus.api.schemas import AskRequest, CreateWorkspaceRequest
from nexus.ingestion import document_store, pipeline
from nexus.pipelines import get_pipeline, get_streaming_pipeline
from nexus.workspaces import store

router = APIRouter()


def find_workspace(workspace_id):
    workspace = store.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="No workspace called '" + workspace_id + "'")
    return workspace


def with_counts(workspace):
    """The workspace as the UI needs it: its sources plus how many documents of each kind it has."""
    result = dict(workspace)
    result["counts"] = document_store.count_by_kind(workspace["id"])

    total = 0
    for source in workspace["sources"]:
        total += source["documents"]
    result["total_documents"] = total
    return result


@router.get("/api/workspaces")
def list_workspaces():
    workspaces = []
    for workspace in store.list_workspaces():
        workspaces.append(with_counts(workspace))
    return workspaces


@router.post("/api/workspaces")
def create_workspace(request: CreateWorkspaceRequest):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Give the workspace a name.")

    if store.get_workspace(store.make_id(name)) is not None:
        raise HTTPException(status_code=409, detail="A workspace called " + name + " already exists.")

    workspace = store.create_workspace(name, request.description.strip(), [])
    return with_counts(workspace)


@router.delete("/api/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str):
    workspace = find_workspace(workspace_id)
    for source in workspace["sources"]:
        if source["status"] in ("syncing", "queued"):
            raise HTTPException(status_code=409, detail="Wait for the sync to finish before deleting this workspace.")

    pipeline.delete_workspace(workspace_id)
    return {"removed": workspace_id}


@router.get("/api/workspaces/{workspace_id}")
def get_workspace(workspace_id: str):
    return with_counts(find_workspace(workspace_id))


def read_question(workspace_id, request):
    find_workspace(workspace_id)

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Type a question first.")
    return question


@router.post("/api/workspaces/{workspace_id}/ask")
def ask(workspace_id: str, request: AskRequest):
    question = read_question(workspace_id, request)

    try:
        answer_question = get_pipeline(request.pipeline)
        return answer_question(workspace_id, question)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=502, detail="The model call failed: " + str(error))


def events_as_lines(events):
    """One JSON object per line. The response has already started, so an error has to be an event too."""
    try:
        for event in events:
            yield json.dumps(event) + "\n"
    except Exception as error:
        message = {"type": "error", "message": "The model call failed: " + str(error)}
        yield json.dumps(message) + "\n"


@router.post("/api/workspaces/{workspace_id}/ask/stream")
def ask_stream(workspace_id: str, request: AskRequest):
    question = read_question(workspace_id, request)

    try:
        stream_answer = get_streaming_pipeline(request.pipeline)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    events = stream_answer(workspace_id, question)
    return StreamingResponse(events_as_lines(events), media_type="application/x-ndjson")
