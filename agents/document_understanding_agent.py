import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from agents.general_assistant_agent import run as run_general_assistant
from tools.document_reader import read_document


MAX_CONTEXT_CHARACTERS = 18000


def prepare_document_context(
    document_content: str,
    metadata: dict,
) -> tuple[str, list[str]]:
    """
    Build safe local context for the general assistant.

    We limit length because a large PDF or DOCX can exceed the local
    model context window. This MVP reads the beginning of long documents
    and explicitly warns the user that the result is partial.
    """
    warnings = []

    if len(document_content) > MAX_CONTEXT_CHARACTERS:
        document_content = document_content[:MAX_CONTEXT_CHARACTERS]
        warnings.append(
            "The document is long, so this response is based on the first "
            f"{MAX_CONTEXT_CHARACTERS:,} extracted characters. "
            "A multi-part full-document summarization flow can be added later."
        )

    filename = metadata.get("filename", "uploaded document")
    file_format = metadata.get("format", "unknown")

    if metadata.get("is_likely_scanned"):
        warnings.append(
            "This PDF appears to be scanned or image-based. "
            "Text extraction may be incomplete; use Vision Analysis for "
            "better OCR on scanned pages."
        )

    context = f"""
Local document metadata:
- Filename: {filename}
- Format: {file_format}
- Extracted characters: {len(document_content)}

Local document content:
<document_content>
{document_content}
</document_content>
""".strip()

    return context, warnings


def run(
    user_message: str,
    file_path: str,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Read one local document and answer a normal natural-language request
    about it.

    Examples:
    - "Summarize this report in five bullets."
    - "Extract the key risks from this document."
    - "Rewrite this for senior management."
    - "What are the important deadlines in this file?"
    """
    try:
        document_result = read_document(file_path)

    except (FileNotFoundError, ValueError, OSError) as error:
        return {
            "status": "failed",
            "response_type": "error",
            "answer": f"I could not read the uploaded document: {error}",
            "model_used": None,
            "tools_used": ["read_document"],
            "deliverable_paths": [],
            "citations": [],
            "warnings": [],
        }

    content = document_result.get("content", "").strip()
    metadata = document_result.get("metadata", {})

    if not content:
        return {
            "status": "failed",
            "response_type": "error",
            "answer": (
                "I could not extract readable text from this document. "
                "If it is a scanned PDF, use the Vision/OCR processing path."
            ),
            "model_used": None,
            "tools_used": ["read_document"],
            "deliverable_paths": [],
            "citations": [],
            "warnings": [
                "No selectable text was extracted from the document."
            ],
        }

    context, warnings = prepare_document_context(
        document_content=content,
        metadata=metadata,
    )

    assistant_result = run_general_assistant(
        user_message=user_message,
        conversation_history=conversation_history,
        context=context,
    )

    return {
        "status": "success",
        "response_type": "summary",
        "answer": assistant_result["answer"],
        "model_used": assistant_result["model_used"],
        "tools_used": ["read_document"],
        "deliverable_paths": [],
        "structured_data": {
            "document_metadata": metadata,
        },
        "citations": [
            {
                "source": metadata.get("filename", os.path.basename(file_path)),
                "excerpt": (
                    "Local uploaded document processed on this workstation."
                ),
            }
        ],
        "warnings": warnings + assistant_result.get("warnings", []),
    }


if __name__ == "__main__":
    test_file = "data/uploads/test_report.txt"

    result = run(
        user_message=(
            "Summarize this document in exactly three concise bullet points. "
            "Do not add facts not found in the document."
        ),
        file_path=test_file,
    )

    print("\n--- STATUS ---")
    print(result["status"])

    print("\n--- CLEAN USER ANSWER ---")
    print(result["answer"])

    print("\n--- LOCAL SOURCE ---")
    print(result["citations"])

    print("\n--- WARNINGS ---")
    print(result["warnings"])