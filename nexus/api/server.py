import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from nexus import config
from nexus.api import eval_routes, source_routes, workspace_routes
from nexus.ingestion.pipeline import mark_interrupted_syncs
from nexus.llm.provider import get_llm, pick_provider_name
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


@app.get("/api/status")
def status():
    return {
        "provider": pick_provider_name(),
        "model": get_llm().name,
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
