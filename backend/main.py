import os
import shutil
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from schemas import (
    ChatRequest,
    ChatResponse,
    Deliverable,
    RunTaskRequest,
    RunTaskResponse,
)
from model_router import call_ollama, classify_task, route_model
from orchestrator import Controller
from logging_audit import get_recent_logs, inspect_network_connections


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

app = FastAPI(
    title="Sovereign AI Workbench",
    description="Local-only agentic AI workbench for confidential industrial tasks.",
)

# Mount custom HTML/CSS/JS at /static.
# All files are served from this local project folder only.
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)

controller = Controller()

# Temporary in-memory mapping for this server session:
# random file ID -> approved generated local file path.
DELIVERABLES: dict[str, Path] = {}


def get_file_type(file_path: Path) -> str:
    """Returns the file extension without the leading dot."""
    suffix = file_path.suffix.lower().lstrip(".")
    return suffix or "file"


@app.get("/", include_in_schema=False)
def root():
    """
    Serve the custom local frontend dashboard.

    Browser URL:
    http://127.0.0.1:8000/
    """
    index_file = FRONTEND_DIR / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="frontend/index.html was not found.",
        )

    return FileResponse(index_file)


@app.get("/health")
def health():
    """Returns local endpoint and visible network-monitor status."""
    network_status = inspect_network_connections()
    external_connections = network_status["external_connections"]

    return {
        "status": "ok",
        "fastapi_endpoint": "http://127.0.0.1:8000",
        "ollama_endpoint": "http://127.0.0.1:11434",
        "external_call_count": len(external_connections),
        "external_connections_detected": external_connections,
        "monitor_permission_limited": network_status["permission_limited"],
        "sandbox_network": "disabled (--network none)",
    }


@app.get("/logs")
def logs(limit: int = 20):
    """
    Returns recent audit records for the Sovereignty Monitor.

    Limit is capped to prevent unnecessarily large local responses.
    """
    safe_limit = max(1, min(limit, 100))
    entries = get_recent_logs(limit=safe_limit)

    return {
        "count": len(entries),
        "entries": entries,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Handles one local chat turn through the local model router."""
    task_type = classify_task(
        user_input=req.message,
        has_image=bool(req.image_path),
    )

    model = route_model(task_type)

    reply = call_ollama(
        model=model,
        prompt=req.message,
        image_path=req.image_path,
    )

    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        model_used=model,
    )


@app.post("/run_task", response_model=RunTaskResponse)
def run_task(req: RunTaskRequest):
    """
    Executes a task through the Controller.

    The Controller handles agent delegation:
    - code_task: Coder Agent -> Docker sandbox
    - vision_task: Vision Agent -> structured findings
    - approval_note: Vision Agent -> RAG -> Document Agent -> DOCX
    """
    result = controller.run_task(
        task_type=req.task_type,
        input_files=req.input_files,
        instructions=req.instructions,
    )

    if result["status"] == "failed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": result.get("error", "Task execution failed."),
                "task_result": result,
            },
        )

    registered_deliverables: list[Deliverable] = []

    for file_path_string in result.get("deliverable_paths", []):
        file_path = Path(file_path_string).resolve()

        # Only expose real files under the local uploads directory.
        # This prevents a generated/incorrect agent response from exposing
        # arbitrary files elsewhere on the host machine.
        try:
            file_path.relative_to(UPLOAD_DIR.resolve())
        except ValueError:
            continue

        if not file_path.exists() or not file_path.is_file():
            continue

        file_id = str(uuid.uuid4())
        DELIVERABLES[file_id] = file_path

        registered_deliverables.append(
            Deliverable(
                file_id=file_id,
                filename=file_path.name,
                download_url=f"/download/{file_id}",
                file_type=get_file_type(file_path),
            )
        )

    return RunTaskResponse(
        task_id=result["task_id"],
        status=result["status"],
        steps=result.get("steps", []),
        deliverable_paths=result.get("deliverable_paths", []),
        deliverables=registered_deliverables,
        models_used=result.get("models_used", []),
        tools_used=result.get("tools_used", []),
    )


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    """
    Saves an uploaded input file to the local workspace only.

    UUID prefixes avoid filename collisions. os.path.basename removes
    unwanted directory components from a client-supplied filename.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_filename = os.path.basename(file.filename or "uploaded_file")
    local_path = UPLOAD_DIR / f"{file_id}_{safe_filename}"

    with open(local_path, "wb") as destination:
        shutil.copyfileobj(file.file, destination)

    return {
        "file_id": file_id,
        "path": str(local_path.relative_to(PROJECT_ROOT)),
        "filename": safe_filename,
        "message": "File stored locally. No cloud upload was used.",
    }


@app.get("/download/{file_id}")
def download(file_id: str):
    """
    Downloads one known local deliverable from the current server session.

    The endpoint never accepts a raw server file path from the browser.
    """
    file_path = DELIVERABLES.get(file_id)

    if file_path is None or not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Deliverable not found. It may have expired after "
                "a server restart."
            ),
        )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )