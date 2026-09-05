import os
import sys

import ollama


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


CODING_MODEL = "qwen2.5-coder:7b"


def run(
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Handle coding, debugging, and code-explanation requests locally.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful local coding assistant. "
                "Write correct, runnable code. "
                "Explain assumptions briefly. "
                "Do not claim that code was executed unless it was actually "
                "run by a tool. "
                "When appropriate, include the complete code in a fenced "
                "code block."
            ),
        }
    ]

    if conversation_history:
        messages.extend(conversation_history[-8:])

    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    try:
        response = ollama.chat(
            model=CODING_MODEL,
            messages=messages,
            options={
                "temperature": 0,
                "num_ctx": 8192,
            },
        )

        if hasattr(response, "message"):
            answer = response.message.content.strip()
        else:
            answer = response["message"]["content"].strip()

        return {
            "status": "success",
            "response_type": "code",
            "answer": answer,
            "model_used": CODING_MODEL,
            "tools_used": ["ollama_chat"],
            "deliverable_paths": [],
            "structured_data": None,
            "citations": [],
            "warnings": [],
        }

    except Exception as error:
        return {
            "status": "failed",
            "response_type": "error",
            "answer": (
                "I could not process the coding request with the local "
                "coding model."
            ),
            "model_used": CODING_MODEL,
            "tools_used": ["ollama_chat"],
            "deliverable_paths": [],
            "structured_data": None,
            "citations": [],
            "warnings": [f"Coding model error: {error}"],
        }


if __name__ == "__main__":
    result = run(
        "Write Python code to generate the first 10 Fibonacci numbers."
    )

    print("\n--- STATUS ---")
    print(result["status"])

    print("\n--- ANSWER ---")
    print(result["answer"])

    print("\n--- MODEL ---")
    print(result["model_used"])