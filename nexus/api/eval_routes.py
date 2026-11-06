import threading

from fastapi import APIRouter, HTTPException

from nexus.api.schemas import EvalRequest
from nexus.api.workspace_routes import find_workspace
from nexus.evaluation.compare import comparison_rows
from nexus.evaluation.runner import load_questions, run_eval
from nexus.pipelines import PIPELINES

router = APIRouter()

# The eval that is running right now, per workspace. Evals are short enough
# that keeping this in memory is fine.
running_evals = {}


@router.get("/api/workspaces/{workspace_id}/evals")
def get_evals(workspace_id: str):
    find_workspace(workspace_id)

    questions = load_questions(workspace_id)
    single_hop = 0
    multi_hop = 0
    for question in questions:
        if question.get("type") == "multi_hop":
            multi_hop += 1
        else:
            single_hop += 1

    return {
        "questions": len(questions),
        "single_hop": single_hop,
        "multi_hop": multi_hop,
        "full": comparison_rows(workspace_id, "full"),
        "retrieval": comparison_rows(workspace_id, "retrieval"),
        "running": running_evals.get(workspace_id),
    }


@router.post("/api/workspaces/{workspace_id}/evals/run")
def start_eval(workspace_id: str, request: EvalRequest):
    find_workspace(workspace_id)

    if request.pipeline not in PIPELINES:
        raise HTTPException(status_code=400, detail="Unknown pipeline " + request.pipeline)
    if request.retrieval_only and request.pipeline == "agentic":
        raise HTTPException(status_code=400, detail="The agentic pipeline needs the LLM, so it has no retrieval-only run.")
    if running_evals.get(workspace_id):
        raise HTTPException(status_code=409, detail="An evaluation is already running for this workspace.")

    running_evals[workspace_id] = {"pipeline": request.pipeline, "message": "Starting"}

    def report_progress(message):
        running_evals[workspace_id] = {"pipeline": request.pipeline, "message": message}

    def run():
        try:
            run_eval(workspace_id, request.pipeline, request.limit, request.retrieval_only, report_progress)
        finally:
            running_evals[workspace_id] = None

    threading.Thread(target=run, daemon=True).start()
    return running_evals[workspace_id]
