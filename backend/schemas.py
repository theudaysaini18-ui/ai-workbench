from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Universal request for the natural-language assistant.

    Future attachments will be local file IDs or local paths returned by /upload.
    The frontend will send the chat history/session ID automatically.
    """

    session_id: str
    message: str = Field(min_length=1)
    attachment_paths: list[str] = Field(default_factory=list)
    use_knowledge_base: bool = False


class Citation(BaseModel):
    """A local source used to ground an assistant answer."""

    source: str
    excerpt: Optional[str] = None


class Artifact(BaseModel):
    """A locally created output file exposed through a controlled download route."""

    file_id: str
    filename: str
    download_url: str
    file_type: str


class TechnicalTrace(BaseModel):
    """
    Internal execution details.

    The UI will keep this collapsed by default, while judges can expand it
    to see local models, agents, tools, audit ID, and safety proof.
    """

    task_id: str
    agents: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    safety_status: str
    external_call_count: int = 0


class AssistantResponse(BaseModel):
    """
    Standard clean response returned by the normal chat assistant.

    `answer` is the primary content shown to users.
    `technical_trace` is secondary evaluator/debug information.
    """

    session_id: str
    response_type: Literal[
        "chat",
        "summary",
        "extraction",
        "code",
        "document",
        "spreadsheet",
        "error",
    ]
    answer: str
    artifacts: list[Artifact] = Field(default_factory=list)
    structured_data: Optional[Any] = None
    citations: list[Citation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    technical_trace: TechnicalTrace


class RunTaskRequest(BaseModel):
    """Request body for the explicit transparent workflow runner."""

    task_type: Literal[
        "approval_note",
        "code_task",
        "vision_task",
        "custom",
    ]
    input_files: list[str] = Field(default_factory=list)
    instructions: str = Field(min_length=1)


class Deliverable(BaseModel):
    """Deliverable used by the existing explicit workflow endpoint."""

    file_id: str
    filename: str
    download_url: str
    file_type: str


class RunTaskResponse(BaseModel):
    """Response for the existing explicit agent-workflow endpoint."""

    task_id: str
    status: Literal["success", "failed"]
    steps: list[dict] = Field(default_factory=list)
    deliverable_paths: list[str] = Field(default_factory=list)
    deliverables: list[Deliverable] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)