# Sovereign AI

> **Your Data. Your Models. Your Control.**

Sovereign AI is a local-first, on-premise agentic AI workbench for confidential industrial, enterprise, and government workflows. It combines open-weight multimodal language models, specialist agents, controlled local tools, a local knowledge base, and a transparent audit trail so sensitive work can be supported by AI without intentionally sending data to public cloud services.

---

## Problem Statement

Organizations in refineries, manufacturing units, PSUs, government offices, regulated enterprises, and defense-linked environments manage confidential information such as:

- Standard operating procedures and maintenance manuals
- Technical reports and inspection records
- Equipment images and defect photographs
- Internal policies, tenders, and compliance documents
- Source code, scripts, and technical logs
- Scanned reports, diagrams, and internal knowledge repositories

Cloud-based AI tools may create concerns related to:

- Sensitive-data exposure
- Data sovereignty and regulatory compliance
- Vendor lock-in
- Dependency on external internet/cloud services
- Lack of visibility into AI actions
- Limited auditability
- Uncontrolled tool or API access

Sovereign AI addresses these concerns through a controlled, local-first AI workbench designed for confidential workflows.

---

## Solution

Sovereign AI is an on-premise agentic AI platform that processes text, documents, images, code, and internal knowledge using locally controlled models and tools.

### Core Workflow

1. The user submits a query and optionally attaches a document, image, or technical file.
2. The request classifier determines the task type.
3. The sovereignty guard checks the task against local-first and tool-use policies.
4. The orchestrator builds the execution workflow.
5. The model router selects the appropriate specialist model or agent.
6. Approved local tools read documents, analyze images, search the local knowledge base, execute controlled code, or generate reports.
7. The system returns a structured response to the user.
8. The activity is saved in a local audit log.

---

## Key Features

### Local-first and On-premise Design

- Designed for deployment inside an organization-controlled environment.
- Supports locally hosted open-weight model workflows.
- Keeps audit records in local storage.
- Reduces reliance on public cloud AI services for confidential tasks.
- Makes execution posture visible through the audit trail.

### Multimodal AI Workbench

Sovereign AI is designed to work with:

- Text prompts and conversational queries
- Technical documents and reports
- Images, inspection photographs, and diagrams
- Code and scripts
- Local organizational knowledge bases

### Specialist-Agent Routing

Instead of forcing every task through one model, the system identifies the type of work and routes it to a suitable specialist capability.

| Capability | Purpose |
|---|---|
| General reasoning agent | Summarization, explanation, drafting, checklists, and general queries |
| Vision agent | Image understanding, inspection-image analysis, visual document interpretation |
| Code agent | Code explanation, debugging, scripts, and technical logic |
| Knowledge-base tool | Retrieval of relevant internal procedures and documents |
| Document tools | Reading uploaded files and generating structured reports |

### Controlled Local Tools

The platform can use approved tools such as:

- `run_python_code` — controlled computation and technical analysis
- `vision_query` — image/vision-model analysis
- `search_kb` — search over the local knowledge base
- `generate_docx` — generation of structured report documents

### Sovereignty Guardrails

The sovereignty guard acts as a policy checkpoint before task execution. It is designed to govern:

- Local-first model routing
- Tool permissions
- Sensitive workflow handling
- External-call visibility
- Audit logging

### Local Audit Trail

The Activity Logs interface records information such as:

- Task status: success or failure
- Models used
- Tools invoked
- Number of external calls
- Sovereignty status
- Activity/task identifier

Example audit entry:

```text
SUCCESS
Models: qwen2.5-vl:7b, qwen2.5:7b
Tools: vision_query, search_kb, generate_docx
External Calls: 0
LOCAL_ONLY_NO_EXTERNAL_CONNECTIONS_VISIBLE
```

---

## System Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                         Web Workbench                        │
│  Chat -  File Upload -  Activity Logs -  Privacy Status         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                       Backend API Layer                      │
│                     Python / FastAPI                         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Request Classification                    │
│     Text -  Document -  Image -  Code -  Retrieval -  Output      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Sovereignty Guard Agent                   │
│       Local policy -  Tool control -  Privacy posture          │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                   Orchestrator + Model Router                │
│       Selects the required local agent, model, and tools     │
└──────────────┬──────────────────┬──────────────────┬─────────┘
               │                  │                  │
               ▼                  ▼                  ▼
┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│ General AI Agent   │ │ Vision AI Agent    │ │ Code AI Agent      │
│ qwen2.5:7b         │ │ qwen2.5-vl:7b      │ │ qwen2.5-coder:7b   │
└─────────┬──────────┘ └─────────┬──────────┘ └─────────┬──────────┘
          │                      │                      │
          └──────────────────┬───┴───────────────┬──────┘
                             ▼                   ▼
              ┌────────────────────────┐  ┌─────────────────────┐
              │ Controlled Local Tools │  │ Local Knowledge Base│
              │ Read -  Search -  Run -   │  │ Internal documents  │
              │ Generate               │  │ and procedures      │
              └────────────┬───────────┘  └─────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Local Audit Trail      │
              │ Status -  Models -  Tools│
              │ External-call count    │
              └────────────────────────┘
```

---

## Project Structure

```text
ai-workbench/
├── agents/
│   ├── general_vision_agent.py
│   └── sovereignty_guard_agent.py
├── backend/
│   ├── assistant_service.py
│   ├── logging_audit.py
│   ├── main.py
│   ├── model_router.py
│   ├── orchestrator.py
│   ├── request_classifier.py
│   ├── schemas.py
│   └── session_store.py
├── data/
├── docs/
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── kb/
├── logs/
│   └── audit.jsonl
├── sandbox_docker/
├── tools/
│   ├── document_reader.py
│   ├── doc_generation.py
│   └── request_classifier.py
├── requirements.txt
└── README.md
```

---

## Technology Stack

| Layer | Technology / Component | Purpose |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | Browser-based user interface |
| Backend | Python | APIs, orchestration, services, agents, and logging |
| API Server | FastAPI + Uvicorn | Backend server and local API endpoints |
| General Model | Qwen 2.5, e.g. `qwen2.5:7b` | General chat, reasoning, summaries, report drafting |
| Code Model | Qwen 2.5 Coder, e.g. `qwen2.5-coder:7b` | Code analysis and technical assistance |
| Vision Model | Qwen 2.5 VL, e.g. `qwen2.5-vl:7b` | Image and visual-document analysis |
| Knowledge Base | Local `kb/` directory | Internal information retrieval |
| Tool Layer | Document, vision, code, and report tools | Controlled task execution |
| Audit Storage | `logs/audit.jsonl` | Local activity/audit records |
| Sandbox Layer | Controlled execution environment | Safer code/tool execution design |

---

## Use Cases

### Industrial Maintenance Intelligence

An engineer uploads an inspection image and technical procedure. Sovereign AI can provide visible observations, identify relevant safety and maintenance considerations, retrieve internal guidance, and produce a concise draft summary for a supervisor.

### Secure Document Analysis

A government office or PSU can upload a confidential policy, circular, SOP, or report. Sovereign AI can summarize it, extract important points, identify action items, and generate a checklist without intentionally using public cloud AI services.

### Code and Technical Support

Engineering teams can submit scripts, technical logs, or code snippets for explanation, debugging support, and improvement suggestions through the code-specialist workflow.

### Knowledge-base Search

Users can search internal procedures, manuals, or organization-specific documentation and receive concise, context-aware responses.

---

## Prerequisites

Before running the project, ensure that you have:

- Python 3.10 or newer
- `pip`
- A local AI model runtime/configuration compatible with the project
- Required local models, if model workflows are enabled
- Optional: Docker or another sandbox environment for controlled execution

---

## Installation

### 1. Open the Project

```bash
cd ai-workbench
```

### 2. Create a Virtual Environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Ensure Audit-log Path Exists

```bash
mkdir -p logs
: > logs/audit.jsonl
```

---

## Running the Application

From the project root, run:

```bash
uvicorn backend.main:app --reload
```

Then open the local address shown in your terminal, usually:

```text
http://127.0.0.1:8000
```

For a hard refresh during development:

```text
Cmd + Shift + R     # macOS
Ctrl + Shift + R    # Windows/Linux
```

---

## How to Use

1. Open Sovereign AI in the browser.
2. Start a new chat or use the current session.
3. Enter a text query.
4. Optionally upload a document, image, or relevant file.
5. Submit the query.
6. The backend classifies the task and routes it to the appropriate local model, agent, and tool workflow.
7. Review the generated response.
8. Open **Activity Logs** to verify task status, models used, tools invoked, and external-call visibility.

---

## Demo Prompts

### Document Analysis

```text
Summarize this document in five bullet points.
List the critical safety precautions and create a concise action checklist.
```

### Image Analysis

```text
Analyze the attached inspection image.
List visible observations, identify key maintenance considerations,
and draft a concise note for a maintenance supervisor.
```

### Code Analysis

```text
Review this code for errors, explain its logic,
and suggest improvements.
```

### Knowledge-base Query

```text
Search the internal knowledge base for relevant procedures
and provide a concise step-by-step answer.
```

---

## Activity Logs

Local audit logs are stored in:

```text
logs/audit.jsonl
```

The Activity Logs interface helps users and administrators inspect how the system processed a request. It can show:

- Whether the task succeeded or failed
- Which model or models were used
- Which tools were used
- Whether external calls were recorded
- The local sovereignty status

This makes the workbench more transparent than a conventional black-box AI chat interface.

---

## Clear Logs for Demo

Before recording a demo video or presenting to judges, clear all local logs with:

```bash
: > logs/audit.jsonl
```

Verify that logs are empty:

```bash
wc -l logs/audit.jsonl
```

Expected output:

```text
0 logs/audit.jsonl
```

Then refresh the browser or reopen Activity Logs.

This command only empties the audit log file. It does not delete your code, models, files, or project directory.

---

## Security and Data Sovereignty

Sovereign AI is designed around these principles:

1. **Local-first processing** — Prefer local model and tool workflows for confidential tasks.
2. **Controlled data boundary** — Keep uploaded files, knowledge-base content, audit records, and execution artifacts inside the organization-controlled environment.
3. **Sovereignty guard** — Apply policy and tool-use checks before task execution.
4. **Controlled tools** — Restrict the AI workflow to approved local tools rather than unrestricted system access.
5. **Auditability** — Record models, tools, task status, and external-call visibility.
6. **Human oversight** — Treat outputs as decision support, not autonomous final decisions.

### Production Security Roadmap

For enterprise deployment, the following additions are recommended:

- Role-based access control
- Single sign-on and multi-factor authentication
- Encryption at rest and in transit
- Network egress controls and firewall policies
- Secure secret management
- Sandboxed tool execution
- Signed or tamper-evident audit logs
- Centralized monitoring and alerting
- Model version governance and evaluation
- Human approval workflows for high-impact actions

---

## Limitations

- AI output quality depends on model capability, compute resources, prompts, and available context.
- AI responses can be incomplete or inaccurate; expert review is required.
- Vision analysis should not be treated as a certified engineering diagnosis.
- JSONL audit logs are suitable for a prototype but are not a complete enterprise-grade compliance system.
- Offline operation requires all models, runtimes, tools, and dependencies to be installed locally.
- Production deployments require additional hardening, monitoring, access control, and security validation.

---

## Future Scope

- Role-based user access for engineers, supervisors, auditors, and administrators
- SSO and MFA integration
- Encrypted document and audit-log storage
- Tamper-evident audit trails using hashing or digital signatures
- Local vector database and retrieval-augmented generation
- OCR for scanned documents
- Hindi and regional-language support
- Domain-specific models for refinery, manufacturing, power, and government workflows
- Human approval checkpoints before sensitive actions
- Confidence scoring and escalation for high-risk requests
- Docker/Kubernetes deployment for scalable private infrastructure
- Air-gapped deployment for restricted environments
- Performance, model-usage, and policy-compliance dashboards

---

## Responsible Use

Sovereign AI is an AI-assisted workbench and should be used as a decision-support system. For safety-critical, legal, financial, medical, industrial-control, defense, or other high-impact scenarios, outputs must be reviewed and approved by qualified humans before action is taken.

---

## Final Statement

**Sovereign AI enables organizations to use modern multimodal AI without giving up control of confidential data.** By combining local open-weight models, specialist agents, controlled tools, knowledge retrieval, and a transparent audit trail, it provides a practical foundation for secure, accountable, and sovereign AI adoption.