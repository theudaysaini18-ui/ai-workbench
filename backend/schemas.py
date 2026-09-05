from pydantic import BaseModel
from typing import Optional, Literal


class ChatRequest(BaseModel):
    session_id: str
    message: str
    image_path: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model_used: str


class RunTaskRequest(BaseModel):
    task_type: Literal["approval_note", "code_task", "vision_task", "custom"]
    input_files: list[str] = []
    instructions: str


class RunTaskResponse(BaseModel):
    task_id: str
    status: str
    steps: list[dict]
    deliverable_paths: list[str]
    models_used: list[str]
    tools_used: list[str]