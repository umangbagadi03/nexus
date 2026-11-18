import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from nexus import config
from nexus.api import eval_routes, source_routes, workspace_routes
from nexus.ingestion.pipeline import mark_interrupted_syncs
from nexus.llm.provider import PROVIDER_LABELS, VISITOR_PROVIDERS, default_model, get_llm
from nexus.pipelines import DEFAULT_PIPELINE, PIPELINES

app = FastAPI(title="Nexus")

app.include_router(workspace_routes.router)
app.include_router(source_routes.router)
app.include_router(eval_routes.router)


@app.on_event("startup")
def on_startup():
    mark_interrupted_syncs()


@app.middleware("http")
async def always_revalidate(request, call_next):
    # Make the browser check for a newer version of the web files on every load
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache"
    return response


def is_question(path):
    return path.endswith("/ask") or path.endswith("/ask/stream")


@app.middleware("http")
async def block_changes_when_read_only(request, call_next):
    # A public demo only answers questions. Everything else that would change data is refused.
    if config.READ_ONLY and request.method != "GET" and not is_question(request.url.path):
        detail = "This is a read-only demo. Run Nexus on your own machine to add workspaces and sources."
        return JSONResponse(status_code=403, content={"detail": detail})
    return await call_next(request)


@app.get("/api/status")
def status():
    llm = get_llm()
    model = ""
    if llm is not None:
        model = llm.name

    # What the web app offers when a visitor brings their own key
    providers = []
    for provider_name in VISITOR_PROVIDERS:
        providers.append({
            "id": provider_name,
            "label": PROVIDER_LABELS[provider_name],
            "default_model": default_model(provider_name),
        })

    return {
        "model": model,
        "search_only": llm is None,
        "read_only": config.READ_ONLY,
        "light_search": config.LIGHT_SEARCH,
        "providers": providers,
        "pipelines": list(PIPELINES.keys()),
        "default_pipeline": DEFAULT_PIPELINE,
    }


@app.get("/files/{workspace_id}/{source_id}/{file_name}")
def uploaded_file(workspace_id: str, source_id: str, file_name: str):
    """Uploaded files, so a citation of a PDF can open the PDF."""
    folder = config.uploads_dir(os.path.basename(workspace_id), os.path.basename(source_id))
    path = os.path.join(folder, os.path.basename(file_name))
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


# The web app is plain HTML, CSS and JS, served from the web folder
app.mount("/", StaticFiles(directory="web", html=True), name="web")
