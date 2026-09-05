import os
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from agents.document_understanding_agent import (
    run as run_document_understanding,
)
from agents.general_assistant_agent import (
    run as run_general_assistant,
)
from agents.general_vision_agent import (
    run as run_general_vision,
)
from agents.coder_agent import run as run_coding_agent
from tools.request_classifier import is_coding_request

from backend.logging_audit import log_task_result
from backend.schemas import (
    AssistantResponse,
    ChatRequest,
    Citation,
    TechnicalTrace,
)
from backend.session_store import SessionStore

from agents.sovereignty_guard_agent import (
    looks_like_external_request,
    run as run_sovereignty_guard,
)




DOCUMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".csv",
    ".xlsx",
    ".xls",
}

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}


class AssistantService:
    """
    Universal local assistant service.

    Current routing:
    - Text-only request -> General Assistant Agent
    - Supported document attachment -> Document Understanding Agent
    - Supported image attachment -> General Vision Agent

    More routes can be added later without changing the frontend
    request format.
    """

    def __init__(self, session_store: SessionStore):
        self.session_store = session_store

    def _find_first_attachment_by_extension(
        self,
        attachment_paths: list[str],
        supported_extensions: set[str],
    ) -> str | None:
        """
        Return the first local attachment whose extension is supported.

        The order of `attachment_paths` determines which supported file
        is selected. This is intentional for the current single-file MVP.
        """
        for file_path in attachment_paths:
            extension = Path(file_path).suffix.lower()

            if extension in supported_extensions:
                return file_path

        return None

    def _build_audit_input(
        self,
        task_id: str,
        agent_name: str,
        agent_result: dict,
    ) -> dict:
        """Build the standard input expected by the local audit logger."""
        model_used = agent_result.get("model_used")

        return {
            "task_id": task_id,
            "status": agent_result.get("status", "failed"),
            "models_used": [model_used] if model_used else [],
            "tools_used": agent_result.get("tools_used", []),
            "deliverable_paths": agent_result.get(
                "deliverable_paths",
                [],
            ),
            "steps": [
                {
                    "step": 1,
                    "agent": agent_name,
                    "status": agent_result.get("status", "failed"),
                    "model_used": model_used,
                    "tools_used": agent_result.get("tools_used", []),
                }
            ],
        }

    def chat(self, request: ChatRequest) -> AssistantResponse:
        """
        Process a natural-language request with optional local attachments.

        Returned response design:
        - `answer`: clean user-facing response
        - `citations`: local-file source references
        - `warnings`: transparent MVP limitations or extraction issues
        - `technical_trace`: optional evaluator/debug information
        """
        task_id = str(uuid.uuid4())
        history = self.session_store.get_history(request.session_id)

        selected_image = self._find_first_attachment_by_extension(
            request.attachment_paths,
            IMAGE_EXTENSIONS,
        )

        selected_document = self._find_first_attachment_by_extension(
            request.attachment_paths,
            DOCUMENT_EXTENSIONS,
        )

        warnings = []

        if len(request.attachment_paths) > 1:
            warnings.append(
                "Multiple attachments were provided. This MVP processed "
                "one supported attachment only."
            )

        # Image is checked first because a user may attach images alongside
        # documents, and the image route is the best current single-file path.
        if looks_like_external_request(request.message):
            agent_name = "sovereignty_guard_agent"

            agent_result = run_sovereignty_guard(
                user_message=request.message,
            )

        elif selected_image:
            agent_name = "general_vision_agent"

            agent_result = run_general_vision(
                user_message=request.message,
                image_path=selected_image,
                conversation_history=history,
            )

        elif selected_document:
            agent_name = "document_understanding_agent"

            agent_result = run_document_understanding(
                user_message=request.message,
                file_path=selected_document,
                conversation_history=history,
            )

        elif is_coding_request(request.message):
            agent_name = "coding_agent"

            agent_result = run_coding_agent(
                user_message=request.message,
                conversation_history=history,
            )

        else:
            agent_name = "general_assistant_agent"

            agent_result = run_general_assistant(
                user_message=request.message,
                conversation_history=history,
            )


        self.session_store.add_message(
            session_id=request.session_id,
            role="user",
            content=request.message,
        )

        if agent_result.get("answer"):
            self.session_store.add_message(
                session_id=request.session_id,
                role="assistant",
                content=agent_result["answer"],
            )

        audit_input = self._build_audit_input(
            task_id=task_id,
            agent_name=agent_name,
            agent_result=agent_result,
        )

        audit_entry = log_task_result(audit_input)

        citations = [
            Citation(**citation)
            for citation in agent_result.get("citations", [])
        ]

        model_used = agent_result.get("model_used")

        technical_trace = TechnicalTrace(
            task_id=task_id,
            agents=[agent_name],
            models=[model_used] if model_used else [],
            tools=agent_result.get("tools_used", []),
            safety_status=audit_entry["sovereignty_status"],
            external_call_count=audit_entry["external_call_count"],
        )

        return AssistantResponse(
            session_id=request.session_id,
            response_type=agent_result.get("response_type", "error"),
            answer=agent_result.get(
                "answer",
                "The request could not be completed.",
            ),
            artifacts=[],
            structured_data=agent_result.get("structured_data"),
            citations=citations,
            warnings=warnings + agent_result.get("warnings", []),
            technical_trace=technical_trace,
        )


if __name__ == "__main__":
    store = SessionStore()
    service = AssistantService(session_store=store)

    text_response = service.chat(
        ChatRequest(
            session_id="text-demo",
            message="Explain the benefit of local AI for confidential files.",
        )
    )

    print("\n--- TEXT-ONLY RESPONSE ---\n")
    print(text_response.answer)
    print("\nAgent:", text_response.technical_trace.agents[0])
    print("Models:", text_response.technical_trace.models)

    document_response = service.chat(
        ChatRequest(
            session_id="document-demo",
            message=(
                "Summarize the attached document in exactly three concise "
                "bullet points. Do not add facts."
            ),
            attachment_paths=["data/uploads/test_report.txt"],
        )
    )

    print("\n--- DOCUMENT RESPONSE ---\n")
    print(document_response.answer)
    print("\nAgent:", document_response.technical_trace.agents[0])
    print("Models:", document_response.technical_trace.models)
    print("Tools:", document_response.technical_trace.tools)
    print("Citations:", document_response.citations)

    image_response = service.chat(
        ChatRequest(
            session_id="image-demo",
            message=(
                "Summarize this screenshot in 3–5 concise bullet points. "
                "Include the main heading and the key topic. "
                "Do not invent facts not visible in the image."
            ),
            attachment_paths=["data/uploads/test_image.png"],
        )
    )

    print("\n--- IMAGE RESPONSE ---\n")
    print(image_response.answer)
    print("\nAgent:", image_response.technical_trace.agents[0])
    print("Models:", image_response.technical_trace.models)
    print("Tools:", image_response.technical_trace.tools)
    print("Citations:", image_response.citations)
    print("Warnings:", image_response.warnings)