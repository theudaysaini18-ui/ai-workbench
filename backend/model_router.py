import ollama

TASK_MODEL_MAP = {
    "general": "qwen2.5:7b",
    "code": "qwen2.5-coder:7b",
    "vision": "qwen2.5vl:7b",
}

CODE_KEYWORDS = ["script", "code", "function", "debug", "calculate", "program", "algorithm"]


def classify_task(user_input: str, has_image: bool = False) -> str:
    """Very simple rule-based router. Swap for an LLM classifier later if time allows."""
    if has_image:
        return "vision"
    lowered = user_input.lower()
    if any(k in lowered for k in CODE_KEYWORDS):
        return "code"
    return "general"


def route_model(task_type: str) -> str:
    return TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP["general"])


def call_ollama(
    model: str,
    prompt: str,
    image_path: str = None,
    json_schema: dict = None,
    messages: list[dict] | None = None,
) -> str:
    """Thin wrapper around the local Ollama client. Always talks to 127.0.0.1:11434."""
    if messages is None:
        messages = [{"role": "user", "content": prompt}]
    if image_path:
        messages[0]["images"] = [image_path]

    kwargs = {
        "model": model,
        "messages": messages,
        "options": {
            "num_ctx": 8192,
            "temperature": 0,
        },
    }
    if json_schema:
        kwargs["format"] = json_schema

    response = ollama.chat(**kwargs)
    return response["message"]["content"]


if __name__ == "__main__":
    task = classify_task("Write a script to compute averages")
    model = route_model(task)
    print(f"task={task}, model={model}")
    print(call_ollama(model, "Say OK if you can hear me."))