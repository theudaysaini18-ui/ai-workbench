from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import sys, os, shutil, uuid

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from schemas import ChatRequest, ChatResponse, RunTaskRequest, RunTaskResponse
from model_router import classify_task, route_model, call_ollama
from agents import coder_agent

app = FastAPI(title="Sovereign AI Workbench")

DELIVERABLES = {}


@app.get("/health")
def health():
    return {"status": "ok", "external_calls": False}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    task_type = classify_task(req.message, has_image=bool(req.image_path))
    model = route_model(task_type)
    reply = call_ollama(model, req.message, image_path=req.image_path)
    return ChatResponse(session_id=req.session_id, reply=reply, model_used=model)


@app.post("/run_task", response_model=RunTaskResponse)
def run_task(req: RunTaskRequest):
    if req.task_type == "code_task":
        result = coder_agent.run(req.instructions)
        task_id = str(uuid.uuid4())
        return RunTaskResponse(
            task_id=task_id,
            status=result["status"],
            steps=[result],
            deliverable_paths=result.get("deliverable_paths", []),
            models_used=[result["model_used"]],
            tools_used=result["tools_used"],
        )
    return RunTaskResponse(
        task_id="not-implemented", status="failed", steps=[],
        deliverable_paths=[], models_used=[], tools_used=[],
    )


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    os.makedirs("data/uploads", exist_ok=True)
    path = f"data/uploads/{file_id}_{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"file_id": file_id, "path": path}


@app.get("/download/{file_id}")
def download(file_id: str):
    return FileResponse(path=DELIVERABLES.get(file_id, ""))