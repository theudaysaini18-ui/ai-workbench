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

from backend.assistant_service import AssistantService
from backend.logging_audit import get_recent_logs, inspect_network_connections
from backend.orchestrator import Controller
from backend.schemas import (
    AssistantResponse,
    ChatRequest,
    Deliverable,
    RunTaskRequest,
    RunTaskResponse,
)
from backend.session_store import SessionStore

from datetime import datetime
from textwrap import wrap

from fastapi import Body
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
EXPORT_DIR = PROJECT_ROOT / "data" / "exports"

app = FastAPI(
    title="Sovereign AI Workbench",
    description="Local-only agentic AI workbench for confidential work.",
)

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)

controller = Controller()

# Chat memory is intentionally in-memory for the MVP.
session_store = SessionStore()
assistant_service = AssistantService(session_store=session_store)

# Current-session mapping from secure random ID -> locally generated file.
DELIVERABLES: dict[str, Path] = {}


def get_file_type(file_path: Path) -> str:
    """Return the extension without its leading dot."""
    return file_path.suffix.lower().lstrip(".") or "file"


@app.get("/", include_in_schema=False)
def root():
    """Serve the local HTML/CSS/JavaScript frontend."""
    index_file = FRONTEND_DIR / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="frontend/index.html was not found.",
        )

    return FileResponse(index_file)


@app.get("/health")
def health():
    """Return local endpoints and visible network-monitor information."""
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
        "active_chat_sessions": session_store.session_count(),
    }


@app.get("/logs")
def logs(limit: int = 20):
    """Return recent local audit records for the Sovereignty Monitor."""
    safe_limit = max(1, min(limit, 100))
    entries = get_recent_logs(limit=safe_limit)

    return {
        "count": len(entries),
        "entries": entries,
    }


@app.post("/chat", response_model=AssistantResponse)
def chat(request: ChatRequest):
    """
    Normal local ChatGPT/Claude-style chat endpoint.

    Current version supports natural text conversation with session memory.
    Attachment processing and automatic agent routing are added next.
    """
    return assistant_service.chat(request)


@app.post("/chat/clear")
def clear_chat(session_id: str):
    """Clear in-memory conversation history for one local chat session."""
    session_store.clear_session(session_id)

    return {
        "status": "success",
        "message": "Local conversation history cleared.",
        "session_id": session_id,
    }


@app.post("/run_task", response_model=RunTaskResponse)
def run_task(request: RunTaskRequest):
    """
    Explicit transparent workflow endpoint retained for testing/demo use.

    Supported:
    - code_task
    - vision_task
    - approval_note
    """
    result = controller.run_task(
        task_type=request.task_type,
        input_files=request.input_files,
        instructions=request.instructions,
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
    """Store an uploaded file only under the local data/uploads folder."""
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


@app.post("/export/pdf")
def export_pdf(payload: dict = Body(...)):
    """
    Create a PDF locally from an assistant response.

    The browser sends only the response text. The PDF is generated and stored
    locally under data/exports, then returned through FileResponse.
    """
    answer = str(payload.get("answer", "")).strip()
    title = str(payload.get("title", "Sovereign AI Workbench Response")).strip()

    if not answer:
        raise HTTPException(
            status_code=400,
            detail="No response text was provided for PDF export.",
        )

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"sovereign_ai_response_{timestamp}.pdf"
    export_path = EXPORT_DIR / export_filename

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    body_style = styles["BodyText"]

    body_style.leading = 16
    body_style.spaceAfter = 7

    document = SimpleDocTemplate(
        str(export_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    story = [
        Paragraph(title, title_style),
        Spacer(1, 8 * mm),
    ]

    for line in answer.splitlines():
        cleaned_line = line.strip()

        if not cleaned_line:
            story.append(Spacer(1, 3 * mm))
            continue

        # Lightweight Markdown cleanup for a readable PDF.
        if cleaned_line.startswith("#"):
            cleaned_line = cleaned_line.lstrip("#").strip()

        if cleaned_line.startswith("- "):
            cleaned_line = "• " + cleaned_line[2:]

        safe_line = cleaned_line.replace("&", "&amp;")
        safe_line = safe_line.replace("<", "&lt;")
        safe_line = safe_line.replace(">", "&gt;")

        story.append(Paragraph(safe_line, body_style))

    document.build(story)

    return FileResponse(
        path=str(export_path),
        filename=export_filename,
        media_type="application/pdf",
    )


@app.get("/download/{file_id}")
def download(file_id: str):
    """
    Download a known generated local artifact from the current server session.

    Browser clients never provide raw file paths.
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