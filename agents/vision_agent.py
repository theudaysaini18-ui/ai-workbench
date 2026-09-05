import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.model_router import call_ollama


MODEL = "qwen2.5vl:7b"


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "equipment_id": {
            "type": "string",
            "description": "Equipment or asset identifier visible in the report."
        },
        "inspection_date": {
            "type": "string",
            "description": "Inspection date visible in the report."
        },
        "inspector_name": {
            "type": "string",
            "description": "Inspector name visible in the report."
        },
        "observations": {
            "type": "array",
            "description": "All inspection observations visible in the report.",
            "items": {
                "type": "object",
                "properties": {
                    "parameter": {"type": "string"},
                    "reading": {"type": "string"},
                    "standard_range": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["parameter", "reading", "status"],
            },
        },
    },
    "required": ["equipment_id", "inspection_date", "observations"],
}


VISION_PROMPT = """
You are the Vision and Scanned-Document Agent in a sovereign industrial AI workbench.

Analyze the supplied inspection report, scanned form, handwritten note, engineering drawing, or photograph.

Extract only information visible in the image.

Return a JSON object that follows the provided schema exactly.

Rules:
- Never guess unreadable text; use "Not visible" when a field cannot be read.
- Preserve units exactly where they appear, for example bar, °C, mm, kW.
- For every observation, identify parameter, reading, standard range if visible, and status.
- If status is not explicitly written, infer only from clearly visible reading versus clearly visible standard range; otherwise use "Not determined".
- Do not include markdown, explanations, or text outside JSON.
"""


def safe_json_loads(raw_text: str) -> dict:
    """
    Converts the model output into a Python dictionary.

    The fallback protects the app if the model returns invalid JSON,
    even though the Ollama JSON schema usually prevents that.
    """
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "equipment_id": "Not visible",
            "inspection_date": "Not visible",
            "inspector_name": "Not visible",
            "observations": [],
            "raw_model_output": raw_text,
        }


def run(input_files: list[str], context: dict | None = None) -> dict:
    """
    Extracts structured inspection findings from the first supplied image.

    Args:
        input_files: List containing a local image path, such as:
                     ['data/sample_scans/inspection_report.jpg']
        context: Reserved for future Controller-provided context.

    Returns:
        Standard agent result dictionary used by the orchestrator.
    """
    if not input_files:
        return {
            "model_used": MODEL,
            "tools_used": ["vision_query"],
            "status": "failed",
            "error": "No image file was provided.",
            "deliverable_paths": [],
        }

    image_path = input_files[0]

    if not os.path.exists(image_path):
        return {
            "model_used": MODEL,
            "tools_used": ["vision_query"],
            "status": "failed",
            "error": f"Image file not found: {image_path}",
            "deliverable_paths": [],
        }

    raw_output = call_ollama(
        model=MODEL,
        prompt=VISION_PROMPT,
        image_path=image_path,
        json_schema=EXTRACTION_SCHEMA,
    )

    findings = safe_json_loads(raw_output)

    return {
        "model_used": MODEL,
        "tools_used": ["vision_query"],
        "status": "success",
        "findings": findings,
        "raw_output": raw_output,
        "deliverable_paths": [],
    }


if __name__ == "__main__":
    image_path = "data/sample_scans/inspection_report.jpg"

    result = run([image_path])

    print("\nStatus:", result["status"])

    if result["status"] == "success":
        print("\nStructured findings:\n")
        print(json.dumps(result["findings"], indent=2))
    else:
        print("\nError:", result["error"])