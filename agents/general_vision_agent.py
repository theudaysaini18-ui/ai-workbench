import os
import sys
from pathlib import Path

import ollama


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


VISION_MODEL = "qwen2.5vl:7b"
SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}


def prepare_vision_prompt(user_message: str) -> str:
    """
    Create instructions for a local multimodal model.

    The actual image is passed separately through the Ollama `images`
    message field. It is not merely described by its file path.
    """
    return f"""
You are a careful local image-understanding assistant.

Answer the user's request using only what is visibly present in the image.

User request:
<user_request>
{user_message}
</user_request>

Rules:
- Do not invent text, labels, numbers, objects, people, or events.
- For OCR/transcription requests, preserve visible wording, spelling,
  capitalization, and numbers as accurately as possible.
- If text is blurred, cut off, obstructed, or unreadable, say that clearly.
- For screenshots, identify visible applications, headings, labels,
  and major on-screen content when relevant.
- For photos, distinguish visible observations from uncertain guesses.
- If the request cannot be answered from the image, explain what is missing.
- Do not claim you opened a website, clicked anything, or accessed data
  outside the image.
- Be concise unless the user asks for a detailed extraction.
""".strip()


def _extract_response_content(response) -> str:
    """
    Support both common ollama-python response styles:
    response.message.content and response["message"]["content"].
    """
    if hasattr(response, "message") and hasattr(response.message, "content"):
        return response.message.content.strip()

    if isinstance(response, dict):
        return response.get("message", {}).get("content", "").strip()

    return ""


def run(
    user_message: str,
    image_path: str,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Answer a user request about one local image through Qwen2.5-VL.

    The image is explicitly passed to Ollama in:
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [absolute_image_path],
        }]
    """
    resolved_path = Path(image_path).expanduser().resolve()

    if not resolved_path.exists():
        return {
            "status": "failed",
            "response_type": "error",
            "answer": "I could not find the specified image file on disk.",
            "model_used": None,
            "tools_used": [],
            "deliverable_paths": [],
            "citations": [],
            "warnings": [f"Image path not found: {image_path}"],
        }

    if not resolved_path.is_file():
        return {
            "status": "failed",
            "response_type": "error",
            "answer": "The specified image path is not a file.",
            "model_used": None,
            "tools_used": [],
            "deliverable_paths": [],
            "citations": [],
            "warnings": [f"Not a file: {resolved_path}"],
        }

    extension = resolved_path.suffix.lower()

    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        return {
            "status": "failed",
            "response_type": "error",
            "answer": (
                "This file format is not currently supported by the "
                "general vision route."
            ),
            "model_used": None,
            "tools_used": [],
            "deliverable_paths": [],
            "citations": [],
            "warnings": [
                f"Unsupported image extension: {extension or 'no extension'}"
            ],
        }

    prompt = prepare_vision_prompt(user_message)

    try:
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [str(resolved_path)],
                }
            ],
            options={
                "temperature": 0,
                "num_ctx": 8192,
            },
        )

        answer = _extract_response_content(response)

        if not answer:
            raise ValueError(
                "The vision model returned an empty response."
            )

    except Exception as error:
        return {
            "status": "failed",
            "response_type": "error",
            "answer": (
                "I could not process the image with the local vision model. "
                "Check that Ollama is running and that "
                f"`{VISION_MODEL}` is installed."
            ),
            "model_used": VISION_MODEL,
            "tools_used": ["ollama_chat"],
            "deliverable_paths": [],
            "citations": [],
            "warnings": [f"Vision model error: {error}"],
        }

    return {
        "status": "success",
        "response_type": "summary",
        "answer": answer,
        "model_used": VISION_MODEL,
        "tools_used": ["ollama_chat"],
        "deliverable_paths": [],
        "structured_data": {
            "image_path": str(resolved_path),
            "filename": resolved_path.name,
            "extension": extension,
            "size_bytes": resolved_path.stat().st_size,
        },
        "citations": [
            {
                "source": resolved_path.name,
                "excerpt": "Local image processed by qwen2.5vl:7b.",
            }
        ],
        "warnings": [],
    }


if __name__ == "__main__":
    test_image = "data/uploads/test_image.png"

    result = run(
        user_message=(
            "Describe this screenshot accurately in 3–5 bullet points. "
            "Transcribe the central heading and summarize the visible "
            "on-screen text. Do not invent objects that are not visible."
        ),
        image_path=test_image,
    )

    print("\n--- STATUS ---")
    print(result["status"])

    print("\n--- CLEAN USER ANSWER ---")
    print(result["answer"])

    print("\n--- MODEL USED ---")
    print(result["model_used"])

    print("\n--- LOCAL SOURCE ---")
    print(result["citations"])

    print("\n--- WARNINGS ---")
    print(result["warnings"])