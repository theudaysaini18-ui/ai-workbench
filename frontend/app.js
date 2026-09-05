const API_BASE_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 240000;

const taskConfigs = {
    approval_note: {
        eyebrow: "MULTI-AGENT WORKFLOW",
        title: "Draft Approval Note from Scanned Report",
        description:
            "Upload an inspection report. Vision and Document agents will " +
            "extract findings, consult local SOPs, and generate a formal " +
            "Word approval note.",
        route: "Vision → RAG → Document",
        needsFile: true,
        accept: ".jpg,.jpeg,.png",
        uploadTitle: "Upload Inspection Image",
        uploadHelp: "JPG or PNG · Stored only in local workspace",
        defaultInstruction:
            "Prepare an approval note for this industrial inspection report. " +
            "Identify non-conformities and check whether escalation is " +
            "required according to the local SOP.",
        workflowSteps: [
            {
                agent: "Vision Agent",
                detail: "Extract visible inspection findings with Qwen2.5-VL",
            },
            {
                agent: "Knowledge Retrieval",
                detail: "Retrieve relevant local SOP clauses from Chroma",
            },
            {
                agent: "Document Agent",
                detail: "Generate a grounded approval-note Word document",
            },
        ],
    },

    code_task: {
        eyebrow: "SANDBOXED CODING WORKFLOW",
        title: "Generate and Verify Python Code",
        description:
            "Describe an internal coding task. The Coder Agent will generate " +
            "Python code, run it in a Docker sandbox with network disabled, " +
            "and return verified output.",
        route: "Code LLM → Docker Sandbox → Verify",
        needsFile: false,
        accept: "",
        uploadTitle: "",
        uploadHelp: "",
        defaultInstruction:
            "Write a Python script that prints the squares of numbers from 1 to 5.",
        workflowSteps: [
            {
                agent: "Coder Agent",
                detail: "Generate Python code using Qwen2.5-Coder",
            },
            {
                agent: "Docker Sandbox",
                detail: "Execute with CPU, memory, and network restrictions",
            },
            {
                agent: "Verifier",
                detail: "Capture stdout, stderr, and execution status",
            },
        ],
    },

    vision_task: {
        eyebrow: "MULTIMODAL WORKFLOW",
        title: "Analyze Scanned Report / Image",
        description:
            "Upload an inspection image, handwritten maintenance note, or " +
            "industrial photograph. The Vision Agent returns structured " +
            "findings using an on-device multimodal model.",
        route: "Vision Model → Structured JSON",
        needsFile: true,
        accept: ".jpg,.jpeg,.png",
        uploadTitle: "Upload Image or Scanned Report",
        uploadHelp: "JPG or PNG · Processed only on this workstation",
        defaultInstruction:
            "Extract all visible equipment inspection details as structured JSON.",
        workflowSteps: [
            {
                agent: "Vision Agent",
                detail: "Analyze the local image with Qwen2.5-VL",
            },
            {
                agent: "Structured Extractor",
                detail: "Return equipment fields and observations as JSON",
            },
        ],
    },
};

let selectedTask = "approval_note";
let selectedFile = null;

const elements = {
    taskCards: document.querySelectorAll(".task-card"),
    taskEyebrow: document.getElementById("task-eyebrow"),
    taskTitle: document.getElementById("task-title"),
    taskDescription: document.getElementById("task-description"),
    modelRoute: document.getElementById("model-route"),
    uploadSection: document.getElementById("upload-section"),
    fileInput: document.getElementById("file-input"),
    filePreview: document.getElementById("file-preview"),
    previewImage: document.getElementById("preview-image"),
    selectedFileName: document.getElementById("selected-file-name"),
    selectedFileSize: document.getElementById("selected-file-size"),
    removeFileButton: document.getElementById("remove-file-button"),
    instructions: document.getElementById("instructions"),
    runTaskButton: document.getElementById("run-task-button"),
    executionSection: document.getElementById("execution-section"),
    workflowStatus: document.getElementById("workflow-status"),
    workflowTimeline: document.getElementById("workflow-timeline"),
    resultsSection: document.getElementById("results-section"),
    resultStatus: document.getElementById("result-status"),
    resultSummary: document.getElementById("result-summary"),
    deliverablesContainer: document.getElementById("deliverables-container"),
    rawResultJson: document.getElementById("raw-result-json"),
    fastapiStatus: document.getElementById("fastapi-status"),
    ollamaStatus: document.getElementById("ollama-status"),
    sandboxStatus: document.getElementById("sandbox-status"),
    externalStatus: document.getElementById("external-status"),
    latestAuditContent: document.getElementById("latest-audit-content"),
    refreshMonitorButton: document.getElementById("refresh-monitor-button"),
};


function formatFileSize(sizeInBytes) {
    if (sizeInBytes < 1024) {
        return `${sizeInBytes} B`;
    }

    if (sizeInBytes < 1024 * 1024) {
        return `${(sizeInBytes / 1024).toFixed(1)} KB`;
    }

    return `${(sizeInBytes / (1024 * 1024)).toFixed(2)} MB`;
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function renderTaskConfig() {
    const config = taskConfigs[selectedTask];

    elements.taskEyebrow.textContent = config.eyebrow;
    elements.taskTitle.textContent = config.title;
    elements.taskDescription.textContent = config.description;
    elements.modelRoute.innerHTML = `
        <span>ROUTE</span>
        <strong>${escapeHtml(config.route)}</strong>
    `;

    elements.instructions.value = config.defaultInstruction;

    if (config.needsFile) {
        elements.uploadSection.classList.remove("hidden");
        elements.fileInput.accept = config.accept;
        elements.fileInput.closest(".upload-box").querySelector("strong").textContent =
            config.uploadTitle;
        elements.fileInput.closest(".upload-box").querySelector("small").textContent =
            config.uploadHelp;
    } else {
        elements.uploadSection.classList.add("hidden");
        clearSelectedFile();
    }

    renderWorkflowTemplate();
    hidePreviousResult();
}


function renderWorkflowTemplate() {
    const config = taskConfigs[selectedTask];

    elements.workflowTimeline.innerHTML = config.workflowSteps
        .map(
            (step, index) => `
                <div class="timeline-item">
                    <span class="timeline-number">${index + 1}</span>
                    <div class="timeline-copy">
                        <strong>${escapeHtml(step.agent)}</strong>
                        <small>${escapeHtml(step.detail)}</small>
                    </div>
                    <span class="timeline-status">PENDING</span>
                </div>
            `
        )
        .join("");
}


function hidePreviousResult() {
    elements.executionSection.classList.add("hidden");
    elements.resultsSection.classList.add("hidden");
    elements.rawResultJson.textContent = "";
    elements.deliverablesContainer.innerHTML = "";
}


function clearSelectedFile() {
    selectedFile = null;
    elements.fileInput.value = "";
    elements.filePreview.classList.add("hidden");
    elements.previewImage.src = "";
    elements.selectedFileName.textContent = "No file selected";
    elements.selectedFileSize.textContent = "";
}


function handleFileSelection(event) {
    const file = event.target.files?.[0];

    if (!file) {
        clearSelectedFile();
        return;
    }

    selectedFile = file;

    elements.selectedFileName.textContent = file.name;
    elements.selectedFileSize.textContent = formatFileSize(file.size);

    const previewUrl = URL.createObjectURL(file);
    elements.previewImage.src = previewUrl;
    elements.filePreview.classList.remove("hidden");
}


async function requestWithTimeout(url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
        });

        const contentType = response.headers.get("content-type") || "";
        const body = contentType.includes("application/json")
            ? await response.json()
            : await response.text();

        if (!response.ok) {
            const message =
                typeof body === "object"
                    ? JSON.stringify(body, null, 2)
                    : body || `HTTP ${response.status}`;

            throw new Error(message);
        }

        return body;
    } finally {
        clearTimeout(timeoutId);
    }
}


async function uploadSelectedFile() {
    if (!selectedFile) {
        return null;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    const response = await requestWithTimeout(
        `${API_BASE_URL}/upload`,
        {
            method: "POST",
            body: formData,
        },
        30000
    );

    return response.path;
}


function setWorkflowRunning(isRunning) {
    elements.runTaskButton.disabled = isRunning;

    if (isRunning) {
        elements.runTaskButton.innerHTML = `
            <span>Running Local Workflow...</span>
            <span class="button-arrow">◌</span>
        `;
        elements.workflowStatus.textContent = "RUNNING";
        elements.workflowStatus.className = "running-badge";
    } else {
        elements.runTaskButton.innerHTML = `
            <span>Run Local Agent Workflow</span>
            <span class="button-arrow">→</span>
        `;
    }
}


function renderCompletedSteps(result) {
    const steps = result.steps || [];

    if (!steps.length) {
        return;
    }

    elements.workflowTimeline.innerHTML = steps
        .map((step) => {
            const status = step.status || "unknown";
            const agent = step.agent || "unknown_agent";
            const model = step.model_used || "No model recorded";
            const tools = (step.tools_used || []).join(", ") || "No tools recorded";

            return `
                <div class="timeline-item">
                    <span class="timeline-number">${escapeHtml(step.step || "?")}</span>
                    <div class="timeline-copy">
                        <strong>${escapeHtml(agent)}</strong>
                        <small>
                            Model: ${escapeHtml(model)}
                            <br>
                            Tools: ${escapeHtml(tools)}
                        </small>
                    </div>
                    <span class="timeline-status">${escapeHtml(status.toUpperCase())}</span>
                </div>
            `;
        })
        .join("");
}


function renderDeliverables(result) {
    const deliverables = result.deliverables || [];
    const paths = result.deliverable_paths || [];

    if (deliverables.length) {
        elements.deliverablesContainer.innerHTML = deliverables
            .map(
                (file) => `
                    <div class="deliverable-card">
                        <div>
                            <strong>📄 ${escapeHtml(file.filename)}</strong>
                            <small>Generated locally on this workstation</small>
                        </div>
                        <a
                            class="download-button"
                            href="${escapeHtml(file.download_url)}"
                            download
                        >
                            Download
                        </a>
                    </div>
                `
            )
            .join("");
        return;
    }

    if (paths.length) {
        elements.deliverablesContainer.innerHTML = paths
            .map(
                (filePath) => `
                    <div class="deliverable-card">
                        <div>
                            <strong>📄 ${escapeHtml(filePath.split("/").pop())}</strong>
                            <small>
                                Generated locally: ${escapeHtml(filePath)}
                            </small>
                        </div>
                        <span class="download-button">
                            Available in data/uploads
                        </span>
                    </div>
                `
            )
            .join("");
        return;
    }

    elements.deliverablesContainer.innerHTML = "";
}


function renderTaskResult(result) {
    elements.resultsSection.classList.remove("hidden");

    const successful = result.status === "success";

    elements.resultStatus.textContent = successful ? "COMPLETED" : "FAILED";
    elements.resultStatus.className = successful
        ? "success-badge"
        : "running-badge";

    const models = (result.models_used || []).join(" → ") || "None";
    const tools = (result.tools_used || []).join(" → ") || "None";

    elements.resultSummary.innerHTML = `
        <div class="result-meta-card">
            <span>TASK ID</span>
            <strong>${escapeHtml(result.task_id || "Unknown")}</strong>
        </div>
        <div class="result-meta-card">
            <span>WORKFLOW STATUS</span>
            <strong>${escapeHtml((result.status || "unknown").toUpperCase())}</strong>
        </div>
        <div class="result-meta-card">
            <span>MODELS AUTO-SELECTED</span>
            <strong>${escapeHtml(models)}</strong>
        </div>
        <div class="result-meta-card">
            <span>TOOLS EXECUTED</span>
            <strong>${escapeHtml(tools)}</strong>
        </div>
    `;

    renderCompletedSteps(result);
    renderDeliverables(result);

    elements.rawResultJson.textContent = JSON.stringify(result, null, 2);
}


async function refreshSovereigntyMonitor() {
    try {
        const health = await requestWithTimeout(
            `${API_BASE_URL}/health`,
            { method: "GET" },
            10000
        );

        elements.fastapiStatus.textContent = "Connected at 127.0.0.1:8000";
        elements.ollamaStatus.textContent =
            health.ollama_endpoint || "127.0.0.1:11434";
        elements.sandboxStatus.textContent =
            health.sandbox_network || "Docker --network none";

        const externalCount = health.external_call_count ?? "Unknown";

        if (externalCount === 0) {
            elements.externalStatus.textContent =
                "0 visible non-local connections";
        } else {
            elements.externalStatus.textContent =
                `${externalCount} visible external connection(s)`;
        }

        const logs = await requestWithTimeout(
            `${API_BASE_URL}/logs?limit=1`,
            { method: "GET" },
            10000
        );

        const latestAudit = logs.entries?.at(-1);

        if (!latestAudit) {
            elements.latestAuditContent.innerHTML = `
                <p class="muted-text">
                    No audit records yet. Run a local workflow to create one.
                </p>
            `;
            return;
        }

        const models = (latestAudit.models_used || []).join(", ") || "None";
        const tools = (latestAudit.tools_used || []).join(", ") || "None";

        elements.latestAuditContent.innerHTML = `
            <div class="audit-list">
                <div>
                    <span>TASK ID</span>
                    <strong>${escapeHtml(latestAudit.task_id || "Unknown")}</strong>
                </div>
                <div>
                    <span>SOVEREIGNTY STATUS</span>
                    <strong>${escapeHtml(
                        latestAudit.sovereignty_status || "Unknown"
                    )}</strong>
                </div>
                <div>
                    <span>MODELS</span>
                    <strong>${escapeHtml(models)}</strong>
                </div>
                <div>
                    <span>TOOLS</span>
                    <strong>${escapeHtml(tools)}</strong>
                </div>
            </div>
        `;
    } catch (error) {
        elements.fastapiStatus.textContent = "Backend unavailable";
        elements.externalStatus.textContent = "Monitor unavailable";

        elements.latestAuditContent.innerHTML = `
            <p class="muted-text">
                Could not reach local backend. Start FastAPI on port 8000.
            </p>
        `;

        console.error("Sovereignty monitor error:", error);
    }
}


async function runTask() {
    const config = taskConfigs[selectedTask];
    const instructions = elements.instructions.value.trim();

    if (!instructions) {
        alert("Please enter task instructions.");
        return;
    }

    if (config.needsFile && !selectedFile) {
        alert("Please choose an image before running this workflow.");
        return;
    }

    hidePreviousResult();
    elements.executionSection.classList.remove("hidden");
    elements.workflowStatus.textContent = "UPLOADING";
    renderWorkflowTemplate();
    setWorkflowRunning(true);

    try {
        let inputFiles = [];

        if (config.needsFile) {
            const uploadedPath = await uploadSelectedFile();
            inputFiles = [uploadedPath];
        }

        elements.workflowStatus.textContent = "AGENTS RUNNING";

        const result = await requestWithTimeout(
            `${API_BASE_URL}/run_task`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    task_type: selectedTask,
                    input_files: inputFiles,
                    instructions,
                }),
            }
        );

        elements.workflowStatus.textContent =
            result.status === "success" ? "COMPLETED" : "FAILED";

        renderTaskResult(result);
        await refreshSovereigntyMonitor();
    } catch (error) {
        elements.workflowStatus.textContent = "FAILED";

        elements.resultsSection.classList.remove("hidden");
        elements.resultStatus.textContent = "FAILED";
        elements.resultStatus.className = "running-badge";

        elements.resultSummary.innerHTML = `
            <div class="result-meta-card">
                <span>ERROR</span>
                <strong>${escapeHtml(error.message)}</strong>
            </div>
        `;

        elements.rawResultJson.textContent = error.message;
        console.error("Task execution error:", error);
    } finally {
        setWorkflowRunning(false);
    }
}


function setupEventListeners() {
    elements.taskCards.forEach((card) => {
        card.addEventListener("click", () => {
            selectedTask = card.dataset.task;

            elements.taskCards.forEach((item) => {
                item.classList.remove("active");
            });

            card.classList.add("active");
            renderTaskConfig();
        });
    });

    elements.fileInput.addEventListener("change", handleFileSelection);

    elements.removeFileButton.addEventListener("click", clearSelectedFile);

    elements.runTaskButton.addEventListener("click", runTask);

    elements.refreshMonitorButton.addEventListener(
        "click",
        refreshSovereigntyMonitor
    );
}


function initializeApp() {
    setupEventListeners();
    renderTaskConfig();
    refreshSovereigntyMonitor();

    // Refresh the monitor every 15 seconds while the dashboard is open.
    window.setInterval(refreshSovereigntyMonitor, 15000);
}


document.addEventListener("DOMContentLoaded", initializeApp);