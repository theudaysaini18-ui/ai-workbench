import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.model_router import call_ollama
from tools.sandbox import run_python_code

MODEL = "qwen2.5-coder:7b"

SYSTEM_PROMPT = """You are the Coder Agent. Write clean, working Python code for the user's request.
Return ONLY the code, no explanations, no markdown fences."""


def run(instructions: str, context: dict = None, max_retries: int = 3) -> dict:
    prompt = f"{SYSTEM_PROMPT}\n\nTask: {instructions}"
    code = call_ollama(MODEL, prompt).strip()
    code = code.replace("```python", "").replace("```", "").strip()

    for attempt in range(max_retries):
        result = run_python_code(code)
        if result["exit_code"] == 0:
            return {
                "model_used": MODEL,
                "tools_used": ["run_python_code"],
                "code": code,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "deliverable_paths": [],
                "status": "success",
            }
        fix_prompt = (
            f"{SYSTEM_PROMPT}\n\nThe following code failed:\n{code}\n\n"
            f"Error:\n{result['stderr']}\n\nFix it and return ONLY the corrected code."
        )
        code = call_ollama(MODEL, fix_prompt).strip().replace("```python", "").replace("```", "").strip()

    return {
        "model_used": MODEL,
        "tools_used": ["run_python_code"],
        "code": code,
        "stdout": "",
        "stderr": "Failed after retries",
        "deliverable_paths": [],
        "status": "failed",
    }


if __name__ == "__main__":
    out = run("Write a script that prints the first 10 fibonacci numbers.")
    print(out)