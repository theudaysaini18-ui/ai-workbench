import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.model_router import call_ollama
from kb.retriever import search_kb
from tools.doc_generation import generate_docx


MODEL = "qwen2.5:7b"


SYSTEM_PROMPT = """
You are the Document and Approval-Note Agent in a sovereign industrial AI workbench.

Your job is to create a concise, formal approval note using:
1. Inspection findings extracted from an industrial report.
2. SOP excerpts retrieved from the organization's local knowledge base.

Rules:
- Use only the given findings and SOP context.
- Do not invent equipment details, measurements, dates, or SOP clause numbers.
- If a fact is not available, write "Not available in the supplied report."
- Mention the SOP filename and clause number only when it appears in the supplied SOP context.
- Use exactly these sections:
  Background
  Observations
  Non-Conformities
  Recommendation
"""


def build_prompt(findings: dict, kb_results: list[dict]) -> str:
    """Creates the grounded prompt passed to the local general-purpose LLM."""
    sop_context = "\n\n".join(
        f"Source: {item['source']}\nContent: {item['text']}"
        for item in kb_results
    )

    if not sop_context:
        sop_context = "No relevant SOP content was found in the local knowledge base."

    return f"""
{SYSTEM_PROMPT}

Inspection findings:
{json.dumps(findings, indent=2)}

Retrieved local SOP context:
{sop_context}

Return the approval note as plain text.
Use the exact heading format below:

Background:
...

Observations:
...

Non-Conformities:
...

Recommendation:
...
"""


def parse_sections(draft: str) -> dict:
    """
    Converts the LLM draft into a dictionary required by generate_docx().

    If the model does not follow the expected headings perfectly,
    the whole draft is safely placed under 'Observations'.
    """
    expected_headings = [
        "Background",
        "Observations",
        "Non-Conformities",
        "Recommendation",
    ]

    sections = {heading: "" for heading in expected_headings}
    current_heading = None

    for line in draft.splitlines():
        cleaned = line.strip()
        matched_heading = None

        for heading in expected_headings:
            if cleaned.lower().rstrip(":") == heading.lower():
                matched_heading = heading
                break

        if matched_heading:
            current_heading = matched_heading
            continue

        if current_heading and cleaned:
            sections[current_heading] += cleaned + "\n"

    if not any(value.strip() for value in sections.values()):
        sections["Observations"] = draft

    return {
        heading: content.strip() or "Not available in the supplied report."
        for heading, content in sections.items()
    }


def run(instructions: str, context: dict | None = None) -> dict:
    """
    Creates an SOP-grounded approval note and saves it as a .docx file.

    `context` will later be supplied by the Controller after the Vision Agent runs.
    Expected context example:
    {
        "findings": {
            "equipment_id": "B-07",
            "inspection_date": "2026-09-05",
            "observations": [...]
        }
    }
    """
    context = context or {}
    findings = context.get("findings", context)

    query = (
        f"{instructions}\n"
        f"Equipment: {findings.get('equipment_id', 'unknown')}\n"
        f"Observations: {json.dumps(findings.get('observations', []))}"
    )

    kb_results = search_kb(query, top_k=3)
    prompt = build_prompt(findings, kb_results)
    draft = call_ollama(MODEL, prompt)

    sections = parse_sections(draft)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"data/uploads/approval_note_{timestamp}.docx"

    created_path = generate_docx(
        sections={
            "title": "Inspection Approval Note",
            "body": sections,
        },
        out_path=out_path,
    )

    return {
        "model_used": MODEL,
        "tools_used": ["search_kb", "generate_docx"],
        "status": "success",
        "draft_text": draft,
        "retrieved_sources": [
            {
                "source": item["source"],
                "score": round(float(item["score"]), 4),
            }
            for item in kb_results
        ],
        "deliverable_paths": [created_path],
    }


if __name__ == "__main__":
    sample_findings = {
        "equipment_id": "Boiler Unit B-07",
        "inspection_date": "2026-09-05",
        "inspector_name": "Demo Inspector",
        "observations": [
            {
                "parameter": "Operating pressure",
                "reading": "13.2 bar",
                "standard_range": "Maximum 12 bar",
                "status": "Non-conforming",
            }
        ],
    }

    result = run(
        instructions=(
            "Prepare an approval note for the boiler pressure inspection. "
            "Check whether the observed pressure requires escalation."
        ),
        context={"findings": sample_findings},
    )

    print("\nStatus:", result["status"])
    print("Model used:", result["model_used"])
    print("Sources:", result["retrieved_sources"])
    print("Document:", result["deliverable_paths"][0])
    print("\nDraft:\n")
    print(result["draft_text"])