import re


EXTERNAL_SERVICE_TERMS = {
    "openai",
    "chatgpt",
    "claude",
    "anthropic",
    "gemini",
    "google drive",
    "dropbox",
    "onedrive",
    "aws",
    "amazon s3",
    "azure",
    "cloud",
    "external api",
    "internet",
    "web",
    "upload",
    "send externally",
    "send online",
}


def looks_like_external_request(message: str) -> bool:
    """
    Detect requests that appear to ask for sending confidential material
    outside the local workstation.

    This does not make any network request. It is a local policy check.
    """
    normalized = str(message or "").lower()
    normalized = re.sub(r"\s+", " ", normalized)

    return any(term in normalized for term in EXTERNAL_SERVICE_TERMS)


def run(user_message: str) -> dict:
    """
    Return a blocked result for a simulated or requested external action.

    `external_call_count` is represented through the warning/trace path
    as a policy-detected attempted external action, not a completed call.
    No external network request is made.
    """
    return {
        "status": "blocked",
        "response_type": "error",
        "answer": (
            "External action blocked.\n\n"
            "This Sovereign AI Workbench is configured for local-only "
            "processing of confidential work. Your request appears to ask "
            "for information or files to be sent to an external cloud, web "
            "service, or third-party AI provider.\n\n"
            "No file was transmitted and no external API call was made. "
            "You can continue by asking me to analyze, summarize, extract, "
            "or generate content entirely on this workstation."
        ),
        "model_used": None,
        "tools_used": ["local_policy_guard"],
        "deliverable_paths": [],
        "structured_data": {
            "policy_decision": "blocked",
            "reason": "Potential external transmission request detected.",
        },
        "citations": [],
        "warnings": [
            "Potential external transmission request detected and blocked.",
            "No external network request was made.",
        ],
        "safety_status": "EXTERNAL_ACTION_BLOCKED",
        "external_call_count": 0,
    }