import json
import os
from datetime import datetime, timezone

import psutil


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_PATH = os.path.join(LOG_DIR, "audit.jsonl")

LOCAL_IPS = {
    "127.0.0.1",
    "::1",
    "0.0.0.0",
}


def inspect_network_connections() -> dict:
    """
    Inspects visible network connections.

    Returns:
    {
        "external_connections": [...],
        "permission_limited": bool
    }

    macOS may deny visibility into some system processes. That is logged
    separately and is NOT treated as proof of an external connection.
    """
    external_connections = []
    permission_limited = False

    try:
        connections = psutil.net_connections(kind="inet")

        for connection in connections:
            if not connection.raddr:
                continue

            remote_ip = connection.raddr.ip
            remote_port = connection.raddr.port

            if remote_ip not in LOCAL_IPS:
                external_connections.append(
                    {
                        "pid": connection.pid,
                        "remote_ip": remote_ip,
                        "remote_port": remote_port,
                        "status": connection.status,
                    }
                )

    except (psutil.AccessDenied, PermissionError):
        permission_limited = True

    return {
        "external_connections": external_connections,
        "permission_limited": permission_limited,
    }


def log_task_result(task_result: dict) -> dict:
    """
    Writes one final task-level audit entry to logs/audit.jsonl.

    Expected input: the unified dictionary returned by Controller.run_task().
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    network_status = inspect_network_connections()
    external_connections = network_status["external_connections"]
    permission_limited = network_status["permission_limited"]

    if external_connections:
        sovereignty_status = "EXTERNAL_CONNECTIONS_DETECTED"
    elif permission_limited:
        sovereignty_status = "LOCAL_ONLY_NO_EXTERNAL_CONNECTIONS_VISIBLE"
    else:
        sovereignty_status = "LOCAL_ONLY_CONFIRMED"

    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "task_id": task_result.get("task_id"),
        "status": task_result.get("status"),
        "models_used": task_result.get("models_used", []),
        "tools_used": task_result.get("tools_used", []),
        "deliverable_paths": task_result.get("deliverable_paths", []),
        "steps": [
            {
                "step": step.get("step"),
                "agent": step.get("agent"),
                "status": step.get("status"),
                "model_used": step.get("model_used"),
                "tools_used": step.get("tools_used", []),
            }
            for step in task_result.get("steps", [])
        ],
        "external_connections_detected": external_connections,
        "external_call_count": len(external_connections),
        "monitor_permission_limited": permission_limited,
        "sovereignty_status": sovereignty_status,
        "local_endpoints": {
            "fastapi": "http://127.0.0.1:8000",
            "ollama": "http://127.0.0.1:11434",
            "sandbox_network": "disabled (--network none)",
        },
    }

    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry) + "\n")

    return entry


def get_recent_logs(limit: int = 20) -> list[dict]:
    """Reads the newest audit entries from the local JSONL audit file."""
    if not os.path.exists(LOG_PATH):
        return []

    with open(LOG_PATH, "r", encoding="utf-8") as log_file:
        lines = log_file.readlines()

    entries = []

    for line in lines[-limit:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return entries


if __name__ == "__main__":
    demo_task = {
        "task_id": "demo-audit-task-002",
        "status": "success",
        "models_used": [
            "qwen2.5vl:7b",
            "qwen2.5:7b",
        ],
        "tools_used": [
            "vision_query",
            "search_kb",
            "generate_docx",
        ],
        "deliverable_paths": [
            "data/uploads/approval_note_demo.docx",
        ],
        "steps": [
            {
                "step": 1,
                "agent": "vision_agent",
                "status": "success",
                "model_used": "qwen2.5vl:7b",
                "tools_used": ["vision_query"],
            },
            {
                "step": 2,
                "agent": "document_agent",
                "status": "success",
                "model_used": "qwen2.5:7b",
                "tools_used": [
                    "search_kb",
                    "generate_docx",
                ],
            },
        ],
    }

    audit_entry = log_task_result(demo_task)

    print("\nAudit entry written:")
    print(json.dumps(audit_entry, indent=2))

    print("\nMost recent log:")
    print(json.dumps(get_recent_logs(limit=1), indent=2))