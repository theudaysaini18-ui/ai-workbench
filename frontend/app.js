const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const fileInput = document.getElementById("file-input");
const attachButton = document.getElementById("attach-button");
const sendButton = document.getElementById("send-button");
const attachmentList = document.getElementById("attachment-list");
const chatMessages = document.getElementById("chat-messages");

const newChatButton = document.getElementById("new-chat-button");
const chatsButton = document.getElementById("chats-button");
const uploadsButton = document.getElementById("uploads-button");
const logsButton = document.getElementById("logs-button");
const topbarLogsButton = document.getElementById("topbar-logs-button");
const clearRecentButton = document.getElementById("clear-recent-button");
const recentChatsList = document.getElementById("recent-chats-list");

const privacyButton = document.getElementById("privacy-button");
const privacySidebarButton = document.getElementById(
  "privacy-sidebar-button"
);
const privacyPanel = document.getElementById("privacy-panel");
const closePrivacyPanelButton = document.getElementById(
  "close-privacy-panel"
);

const logsModal = document.getElementById("logs-modal");
const closeLogsButton = document.getElementById("close-logs-button");
const refreshLogsButton = document.getElementById("refresh-logs-button");
const logsStatus = document.getElementById("logs-status");
const logsList = document.getElementById("logs-list");

const uploadsModal = document.getElementById("uploads-modal");
const closeUploadsButton = document.getElementById("close-uploads-button");
const largeUploadButton = document.getElementById("large-upload-button");

const userMessageTemplate = document.getElementById("user-message-template");
const assistantMessageTemplate = document.getElementById(
  "assistant-message-template"
);
const loadingTemplate = document.getElementById("loading-template");

const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024;
const SESSION_STORAGE_KEY = "sih_workbench_session_id";
const RECENT_CHATS_STORAGE_KEY = "sih_workbench_recent_chats";

let pendingAttachments = [];
let isSending = false;
let sessionId = getSessionId();


function createSessionId() {
  if (window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}


function getSessionId() {
  let storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);

  if (!storedSessionId) {
    storedSessionId = createSessionId();
    localStorage.setItem(SESSION_STORAGE_KEY, storedSessionId);
  }

  return storedSessionId;
}


function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function renderInlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}


function renderMarkdown(markdown) {
  const rawLines = String(markdown || "")
    .replace(/\r\n/g, "\n")
    .split("\n");

  const lines = rawLines.map((line) => {
    const match = line.match(/^\s*1[.)]\s+(.+)$/);

    if (!match) {
      return line;
    }

    return `- ${match[1]}`;
  });

  const html = [];
  let inUnorderedList = false;
  let inOrderedList = false;
  let inCodeBlock = false;
  let codeLines = [];

  function closeLists() {
    if (inUnorderedList) {
      html.push("</ul>");
      inUnorderedList = false;
    }

    if (inOrderedList) {
      html.push("</ol>");
      inOrderedList = false;
    }
  }

  function closeCodeBlock() {
    if (inCodeBlock) {
      html.push(
        `<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`
      );

      codeLines = [];
      inCodeBlock = false;
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        closeCodeBlock();
      } else {
        closeLists();
        inCodeBlock = true;
      }

      continue;
    }

    if (inCodeBlock) {
      codeLines.push(rawLine);
      continue;
    }

    if (!line.trim()) {
      closeLists();
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);

    if (heading) {
      closeLists();

      const level = heading.length;[1]

      html.push(
        `<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`
      );

      continue;
    }

    const unorderedItem = line.match(/^\s*[-*]\s+(.+)$/);

    if (unorderedItem) {
      if (inOrderedList) {
        html.push("</ol>");
        inOrderedList = false;
      }

      if (!inUnorderedList) {
        html.push("<ul>");
        inUnorderedList = true;
      }

      html.push(`<li>${renderInlineMarkdown(unorderedItem[1])}</li>`);
      continue;
    }

    const orderedItem = line.match(/^\s*\d+[.)]\s+(.+)$/);

    if (orderedItem) {
      if (inUnorderedList) {
        html.push("</ul>");
        inUnorderedList = false;
      }

      if (!inOrderedList) {
        html.push("<ol>");
        inOrderedList = true;
      }

      html.push(`<li>${renderInlineMarkdown(orderedItem[1])}</li>`);
      continue;
    }

    const quote = line.match(/^>\s?(.+)$/);

    if (quote) {
      closeLists();
      html.push(`<blockquote>${renderInlineMarkdown(quote[1])}</blockquote>`);
      continue;
    }

    closeLists();
    html.push(`<p>${renderInlineMarkdown(line)}</p>`);
  }

  closeLists();
  closeCodeBlock();

  return html.join("") || "<p>No response content was returned.</p>";
}


function removeEmptyState() {
  const emptyState = chatMessages.querySelector(".hero-empty-state");

  if (emptyState) {
    emptyState.remove();
  }
}


function addUserMessage(message, attachmentNames) {
  removeEmptyState();

  const fragment = userMessageTemplate.content.cloneNode(true);
  const content = fragment.querySelector(".message-content");

  let html = `<p>${renderInlineMarkdown(message)}</p>`;

  if (attachmentNames.length > 0) {
    html += "<ul>";

    for (const filename of attachmentNames) {
      html += `<li>Attached: ${escapeHtml(filename)}</li>`;
    }

    html += "</ul>";
  }

  content.innerHTML = html;
  chatMessages.appendChild(fragment);
  scrollToBottom();
}


function downloadTextFile(content, filename, mimeType) {
  const blob = new Blob([content], {
    type: mimeType,
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}


async function downloadPdf(answer, button) {
  const originalText = button.innerHTML;

  try {
    button.disabled = true;
    button.textContent = "Creating…";

    const response = await fetch("/export/pdf", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: "Sovereign AI Workbench Response",
        answer,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();

      throw new Error(
        errorText || "Local PDF generation failed."
      );
    }

    const pdfBlob = await response.blob();
    const url = URL.createObjectURL(pdfBlob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "sovereign-ai-response.pdf";

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
  } catch (error) {
    alert(
      `Could not create the local PDF: ${
        error.message || "Unknown error"
      }`
    );
  } finally {
    button.disabled = false;
    button.innerHTML = originalText;
  }
}


function addAssistantMessage(response) {
  const fragment = assistantMessageTemplate.content.cloneNode(true);

  const content = fragment.querySelector(".message-content");
  const citationList = fragment.querySelector(".citation-list");
  const warningList = fragment.querySelector(".warning-list");
  const technicalContent = fragment.querySelector(".technical-content");
  const assistantMessage = fragment.querySelector(".assistant-message");

  const txtButton = fragment.querySelector(".export-txt");
  const mdButton = fragment.querySelector(".export-md");
  const pdfButton = fragment.querySelector(".export-pdf");

  content.innerHTML = renderMarkdown(response.answer);

  if (
    response.technical_trace?.safety_status ===
    "EXTERNAL_ACTION_BLOCKED"
  ) {
    assistantMessage.classList.add("blocked-message");

    const blockedBanner = document.createElement("div");
    blockedBanner.className = "blocked-banner";
    blockedBanner.textContent =
      "External transmission blocked — confidential data remains local.";

    assistantMessage.prepend(blockedBanner);
  }

  for (const citation of response.citations || []) {
    const chip = document.createElement("span");
    chip.className = "citation-chip";
    chip.title = citation.excerpt || "Local source";
    chip.textContent = `Source: ${citation.source}`;
    citationList.appendChild(chip);
  }

  for (const warning of response.warnings || []) {
    const chip = document.createElement("span");
    chip.className = "warning-chip";
    chip.textContent = `Warning: ${warning}`;
    warningList.appendChild(chip);
  }

  const trace = response.technical_trace;

  if (trace) {
    const rows = [
      ["Agent", (trace.agents || []).join(", ") || "Not recorded"],
      ["Model", (trace.models || []).join(", ") || "Not recorded"],
      ["Tools", (trace.tools || []).join(", ") || "None"],
      ["Safety", trace.safety_status || "Not recorded"],
      ["External calls", String(trace.external_call_count ?? 0)],
      ["Task ID", trace.task_id || "Not recorded"],
    ];

    for (const [label, value] of rows) {
      const row = document.createElement("div");

      row.innerHTML = `
        <strong>${escapeHtml(label)}:</strong>
        <code>${escapeHtml(value)}</code>
      `;

      technicalContent.appendChild(row);
    }
  } else {
    technicalContent.innerHTML =
      "<div>No technical trace was returned.</div>";
  }

  txtButton.addEventListener("click", () => {
    downloadTextFile(
      response.answer,
      "sovereign-ai-response.txt",
      "text/plain;charset=utf-8"
    );
  });

  mdButton.addEventListener("click", () => {
    downloadTextFile(
      response.answer,
      "sovereign-ai-response.md",
      "text/markdown;charset=utf-8"
    );
  });

  pdfButton.addEventListener("click", async () => {
    await downloadPdf(response.answer, pdfButton);
  });

  chatMessages.appendChild(fragment);
  scrollToBottom();
}


function addErrorMessage(message) {
  addAssistantMessage({
    answer: `**Unable to complete the request.**\n\n${message}`,
    citations: [],
    warnings: [message],
    technical_trace: {
      task_id: "frontend-error",
      agents: [],
      models: [],
      tools: [],
      safety_status: "REQUEST_NOT_COMPLETED",
      external_call_count: 0,
    },
  });
}


function addLoadingMessage() {
  const fragment = loadingTemplate.content.cloneNode(true);
  const loadingElement = fragment.querySelector(".loading-row");

  chatMessages.appendChild(fragment);
  scrollToBottom();

  return loadingElement;
}


function setComposerBusy(busy) {
  isSending = busy;
  sendButton.disabled = busy;
  attachButton.disabled = busy;
  messageInput.disabled = busy;

  if (!busy) {
    messageInput.focus();
  }
}


function autoResizeMessageInput() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(
    messageInput.scrollHeight,
    180
  )}px`;
}


function renderAttachmentList() {
  attachmentList.innerHTML = "";

  for (const attachment of pendingAttachments) {
    const chip = document.createElement("div");
    chip.className = "attachment-chip";

    const icon = document.createElement("span");
    icon.className = "attachment-icon";
    icon.textContent = "▣";

    const name = document.createElement("span");
    name.className = "attachment-name";
    name.textContent = attachment.file.name;
    name.title = attachment.file.name;

    const removeButton = document.createElement("button");
    removeButton.className = "remove-attachment";
    removeButton.type = "button";
    removeButton.title = "Remove attachment";
    removeButton.setAttribute("aria-label", "Remove attachment");
    removeButton.textContent = "×";

    removeButton.addEventListener("click", () => {
      pendingAttachments = pendingAttachments.filter(
        (item) => item.id !== attachment.id
      );

      renderAttachmentList();
    });

    chip.append(icon, name, removeButton);
    attachmentList.appendChild(chip);
  }
}


function addSelectedFiles(fileList) {
  const selectedFiles = Array.from(fileList || []);

  for (const file of selectedFiles) {
    if (file.size > MAX_FILE_SIZE_BYTES) {
      addErrorMessage(
        `${file.name} is larger than the current 25 MB upload limit.`
      );

      continue;
    }

    pendingAttachments.push({
      id: createSessionId(),
      file,
    });
  }

  renderAttachmentList();
}


async function uploadAttachment(attachment) {
  const formData = new FormData();
  formData.append("file", attachment.file);

  const response = await fetch("/upload", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();

    throw new Error(
      `Upload failed for ${attachment.file.name}: ${
        text || response.status
      }`
    );
  }

  const result = await response.json();

  if (!result.path) {
    throw new Error(
      "The local upload response did not include a file path."
    );
  }

  return {
    filename: result.filename || attachment.file.name,
    path: result.path,
  };
}


function getRecentChats() {
  try {
    const stored = localStorage.getItem(RECENT_CHATS_STORAGE_KEY);
    const parsed = JSON.parse(stored || "[]");

    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}


function saveRecentChat(message) {
  const cleanedMessage = String(message || "").trim();

  if (!cleanedMessage) {
    return;
  }

  const existing = getRecentChats().filter(
    (item) => item.message !== cleanedMessage
  );

  const next = [
    {
      id: createSessionId(),
      message: cleanedMessage,
      createdAt: new Date().toISOString(),
    },
    ...existing,
  ].slice(0, 10);

  localStorage.setItem(
    RECENT_CHATS_STORAGE_KEY,
    JSON.stringify(next)
  );

  renderRecentChats();
}


function renderRecentChats() {
  const recentChats = getRecentChats();

  recentChatsList.innerHTML = "";

  if (recentChats.length === 0) {
    recentChatsList.innerHTML =
      '<p class="recent-empty">Your recent chats will appear here.</p>';

    return;
  }

  for (const recentChat of recentChats) {
    const button = document.createElement("button");

    button.className = "recent-chat-button";
    button.type = "button";
    button.title = recentChat.message;
    button.textContent = recentChat.message;

    button.addEventListener("click", () => {
      messageInput.value = recentChat.message;
      autoResizeMessageInput();
      messageInput.focus();
    });

    recentChatsList.appendChild(button);
  }
}


async function sendMessage() {
  const message = messageInput.value.trim();

  if (isSending || (!message && pendingAttachments.length === 0)) {
    return;
  }

  if (!message) {
    addErrorMessage(
      "Please enter a message describing what you want done."
    );

    return;
  }

  const attachmentsForMessage = [...pendingAttachments];

  const attachmentNames = attachmentsForMessage.map(
    (attachment) => attachment.file.name
  );

  addUserMessage(message, attachmentNames);
  saveRecentChat(message);

  messageInput.value = "";
  autoResizeMessageInput();

  pendingAttachments = [];
  renderAttachmentList();

  setComposerBusy(true);

  const loadingMessage = addLoadingMessage();

  try {
    const uploadedAttachments = [];

    for (const attachment of attachmentsForMessage) {
      uploadedAttachments.push(await uploadAttachment(attachment));
    }

    const chatResponse = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        attachment_paths: uploadedAttachments.map(
          (attachment) => attachment.path
        ),
        use_knowledge_base: false,
      }),
    });

    if (!chatResponse.ok) {
      const text = await chatResponse.text();

      throw new Error(
        text || `Chat request failed: ${chatResponse.status}`
      );
    }

    const result = await chatResponse.json();

    loadingMessage.remove();
    addAssistantMessage(result);
  } catch (error) {
    loadingMessage.remove();

    addErrorMessage(
      error.message || "An unexpected local error occurred."
    );
  } finally {
    setComposerBusy(false);
  }
}


function renderNewChatEmptyState() {
  chatMessages.innerHTML = `
    <article class="hero-empty-state">
      <div class="hero-orb">
        <span>✦</span>
      </div>

      <p class="eyebrow">NEW PRIVATE CONVERSATION</p>

      <h2>What would you like to work on?</h2>

      <p class="hero-description">
        Upload confidential files, analyze images, write code, or ask a
        question using local AI models.
      </p>

      <div class="hero-features">
        <span>◈ Local models</span>
        <span>◌ File-aware chat</span>
        <span>◷ Auditable activity</span>
      </div>
    </article>
  `;
}


async function createNewChat() {
  if (isSending) {
    return;
  }

  try {
    await fetch(
      `/chat/clear?session_id=${encodeURIComponent(sessionId)}`,
      {
        method: "POST",
      }
    );
  } catch (error) {
    console.warn("Could not clear the previous local chat:", error);
  }

  sessionId = createSessionId();
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId);

  pendingAttachments = [];
  renderAttachmentList();

  renderNewChatEmptyState();

  messageInput.value = "";
  autoResizeMessageInput();
  messageInput.focus();
}


function formatLogDate(value) {
  if (!value) {
    return "Time not recorded";
  }

  const parsedDate = new Date(value);

  if (Number.isNaN(parsedDate.getTime())) {
    return String(value);
  }

  return parsedDate.toLocaleString();
}


function escapeLogValue(value) {
  return escapeHtml(
    Array.isArray(value)
      ? value.join(", ")
      : String(value ?? "Not recorded")
  );
}


function renderLogs(entries) {
  logsList.innerHTML = "";

  if (!entries || entries.length === 0) {
    logsList.innerHTML = `
      <div class="empty-logs">
        <div class="empty-logs-icon">◷</div>
        <strong>No activity logs yet</strong>
        <p>
          Send a message, analyze a file, or run a coding request to create a
          local audit record.
        </p>
      </div>
    `;

    return;
  }

  for (const entry of entries) {
    const taskId = entry.task_id || entry.id || "Task ID not recorded";

    const timestamp =
      entry.timestamp ||
      entry.created_at ||
      entry.time ||
      entry.logged_at;

    const status = entry.status || "completed";

    const models =
      entry.models_used ||
      entry.models ||
      [];

    const tools =
      entry.tools_used ||
      entry.tools ||
      [];

    const safetyStatus =
      entry.sovereignty_status ||
      entry.safety_status ||
      "LOCAL_ONLY_NO_EXTERNAL_CONNECTIONS_VISIBLE";

    const externalCallCount =
      entry.external_call_count ??
      0;

    const normalizedStatus = String(status)
      .toLowerCase()
      .replace(/\s+/g, "-");

    const logCard = document.createElement("article");
    logCard.className = "log-card";

    logCard.innerHTML = `
      <div class="log-card-top">
        <div>
          <span class="log-status ${escapeLogValue(normalizedStatus)}">
            ${escapeLogValue(status)}
          </span>

          <span class="log-time">
            ${escapeLogValue(formatLogDate(timestamp))}
          </span>
        </div>

        <code class="log-task-id">${escapeLogValue(taskId)}</code>
      </div>

      <div class="log-grid">
        <div>
          <span>Models</span>
          <strong>${escapeLogValue(
            models.length ? models : "None"
          )}</strong>
        </div>

        <div>
          <span>Tools</span>
          <strong>${escapeLogValue(
            tools.length ? tools : "None"
          )}</strong>
        </div>

        <div>
          <span>External calls</span>
          <strong>${escapeLogValue(externalCallCount)}</strong>
        </div>
      </div>

      <div class="log-safety">
        ◈ ${escapeLogValue(safetyStatus)}
      </div>
    `;

    logsList.appendChild(logCard);
  }
}


async function openLogsModal() {
  logsModal.classList.remove("hidden");
  logsStatus.textContent = "Loading local activity…";
  logsList.innerHTML = "";

  try {
    const response = await fetch("/logs?limit=100");

    if (!response.ok) {
      throw new Error(`Could not load logs: ${response.status}`);
    }

    const result = await response.json();
    const entries = result.entries || [];

    logsStatus.textContent =
      entries.length === 1
        ? "1 local activity record"
        : `${entries.length} local activity records`;

    renderLogs(entries);
  } catch (error) {
    logsStatus.textContent = "Could not load local activity.";

    logsList.innerHTML = `
      <div class="empty-logs error-logs">
        <div class="empty-logs-icon">!</div>
        <strong>Activity logs unavailable</strong>
        <p>${escapeHtml(error.message || "Unknown local error.")}</p>
      </div>
    `;
  }
}


function closeLogsModal() {
  logsModal.classList.add("hidden");
}


function openUploadsModal() {
  uploadsModal.classList.remove("hidden");
}


function closeUploadsModal() {
  uploadsModal.classList.add("hidden");
}


function togglePrivacyPanel() {
  const isHidden = privacyPanel.classList.toggle("hidden");

  privacyButton.setAttribute("aria-expanded", String(!isHidden));
  privacySidebarButton.setAttribute(
    "aria-expanded",
    String(!isHidden)
  );
}


function closePrivacyPanel() {
  privacyPanel.classList.add("hidden");

  privacyButton.setAttribute("aria-expanded", "false");
  privacySidebarButton.setAttribute("aria-expanded", "false");
}


function activateSidebarItem(button) {
  for (const navItem of document.querySelectorAll(".nav-item")) {
    navItem.classList.remove("active");
  }

  button.classList.add("active");
}


attachButton.addEventListener("click", () => {
  fileInput.click();
});

fileInput.addEventListener("change", (event) => {
  addSelectedFiles(event.target.files);
  fileInput.value = "";
});

largeUploadButton.addEventListener("click", () => {
  closeUploadsModal();
  fileInput.click();
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendMessage();
});

messageInput.addEventListener("input", autoResizeMessageInput);

messageInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    await sendMessage();
  }
});

newChatButton.addEventListener("click", createNewChat);

chatsButton.addEventListener("click", () => {
  activateSidebarItem(chatsButton);
  messageInput.focus();
});

uploadsButton.addEventListener("click", () => {
  activateSidebarItem(uploadsButton);
  openUploadsModal();
});

logsButton.addEventListener("click", () => {
  activateSidebarItem(logsButton);
  openLogsModal();
});

topbarLogsButton.addEventListener("click", openLogsModal);

closeLogsButton.addEventListener("click", closeLogsModal);

refreshLogsButton.addEventListener("click", openLogsModal);

closeUploadsButton.addEventListener("click", closeUploadsModal);

privacyButton.addEventListener("click", togglePrivacyPanel);

privacySidebarButton.addEventListener("click", togglePrivacyPanel);

closePrivacyPanelButton.addEventListener("click", closePrivacyPanel);

clearRecentButton.addEventListener("click", () => {
  localStorage.removeItem(RECENT_CHATS_STORAGE_KEY);
  renderRecentChats();
});

logsModal.addEventListener("click", (event) => {
  if (event.target === logsModal) {
    closeLogsModal();
  }
});

uploadsModal.addEventListener("click", (event) => {
  if (event.target === uploadsModal) {
    closeUploadsModal();
  }
});

document.addEventListener("keydown", async (event) => {
  const commandOrControl = event.metaKey || event.ctrlKey;

  if (commandOrControl && event.key.toLowerCase() === "k") {
    event.preventDefault();
    await createNewChat();
  }

  if (event.key === "Escape") {
    closeLogsModal();
    closeUploadsModal();
    closePrivacyPanel();
  }
});

for (const starterCard of document.querySelectorAll(".starter-card")) {
  starterCard.addEventListener("click", () => {
    messageInput.value = starterCard.dataset.prompt || "";
    autoResizeMessageInput();
    messageInput.focus();
  });
}

autoResizeMessageInput();
renderRecentChats();