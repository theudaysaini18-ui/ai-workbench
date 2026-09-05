from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for a single routed local-chat interaction."""

    session_id: str
    message: str
    image_path: Optional[str] = None


class ChatResponse(BaseModel):
    """Response body for a single routed local-chat interaction."""

    session_id: str
    reply: str
    model_used: str


class RunTaskRequest(BaseModel):
    """
    Request body for a full agentic workflow.

    `task_type` is intentionally restricted so unsupported tasks are
    rejected at the FastAPI boundary instead of failing inside an agent.
    """

    task_type: Literal[
        "approval_note",
        "code_task",
        "vision_task",
        "custom",
    ]

    input_files: list[str] = Field(default_factory=list)
    instructions: str = Field(min_length=1)


class Deliverable(BaseModel):
    """
    A locally generated file made available through a controlled API route.

    `download_url` is a relative URL such as:
    /download/fc841b7a-...
    """

    file_id: str
    filename: str
    download_url: str
    file_type: str


class RunTaskResponse(BaseModel):
    """Unified response returned after the Controller executes a workflow."""

    task_id: str
    status: Literal["success", "failed"]
    steps: list[dict] = Field(default_factory=list)