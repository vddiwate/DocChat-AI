/**
 * DocChat AI - Interactive Web Application Logic
 * Integrates directly with FastAPI Backend (http://127.0.0.1:8000)
 */

const API_BASE_URL = "http://127.0.0.1:8000";

// DOM Elements
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const uploadProgress = document.getElementById("uploadProgress");
const progressText = document.getElementById("progressText");
const documentList = document.getElementById("documentList");
const emptyDocsState = document.getElementById("emptyDocsState");
const docCountBadge = document.getElementById("docCountBadge");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

const chatContainer = document.getElementById("chatContainer");
const welcomeHero = document.getElementById("welcomeHero");
const messageStream = document.getElementById("messageStream");
const promptForm = document.getElementById("promptForm");
const queryInput = document.getElementById("queryInput");
const sendBtn = document.getElementById("sendBtn");
const clearChatBtn = document.getElementById("clearChatBtn");
const toastContainer = document.getElementById("toastContainer");

// In-Memory & LocalStorage State
let indexedDocuments = JSON.parse(localStorage.getItem("docchat_documents") || "[]");
let chatHistory = [];

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    renderDocuments();
    checkBackendHealth();
    setInterval(checkBackendHealth, 10000);
    setupEventListeners();
    autoResizeTextarea();
});

function setupEventListeners() {
    // Dropzone Events
    dropzone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", handleFileSelection);

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    // Prompt Submission
    promptForm.addEventListener("submit", (e) => {
        e.preventDefault();
        handleUserQuery();
    });

    queryInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleUserQuery();
        }
    });

    queryInput.addEventListener("input", autoResizeTextarea);

    // Starter Prompt Chips
    document.querySelectorAll(".prompt-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const prompt = chip.getAttribute("data-prompt");
            queryInput.value = prompt;
            autoResizeTextarea();
            handleUserQuery();
        });
    });

    // Clear Chat
    clearChatBtn.addEventListener("click", clearChat);
}

// Auto-resizing textarea
function autoResizeTextarea() {
    queryInput.style.height = "auto";
    queryInput.style.height = Math.min(queryInput.scrollHeight, 160) + "px";
}

// Check Backend Health
async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            statusDot.className = "status-dot online";
            statusText.textContent = "FastAPI Live (8000)";
        } else {
            throw new Error();
        }
    } catch {
        statusDot.className = "status-dot offline";
        statusText.textContent = "Backend Offline";
    }
}

// Handle File Selection
function handleFileSelection(e) {
    if (e.target.files.length > 0) {
        uploadFile(e.target.files[0]);
    }
}

// Upload & Index Document
async function uploadFile(file) {
    const validExtensions = [".pdf", ".txt"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    
    if (!validExtensions.includes(ext)) {
        showToast("Only .pdf and .txt files are supported.", "error");
        return;
    }

    uploadProgress.style.display = "flex";
    progressText.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Upload failed");
        }

        // Add to active docs
        const docEntry = {
            filename: data.filename,
            chunks: data.chunks_indexed,
            size: data.file_size_bytes,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        // Prevent duplicate file entries in UI
        indexedDocuments = indexedDocuments.filter(d => d.filename !== docEntry.filename);
        indexedDocuments.unshift(docEntry);
        localStorage.setItem("docchat_documents", JSON.stringify(indexedDocuments));

        renderDocuments();
        showToast(`Indexed ${data.chunks_indexed} chunks for ${data.filename}!`, "success");

    } catch (err) {
        showToast(err.message || "Failed to upload document", "error");
    } finally {
        uploadProgress.style.display = "none";
        fileInput.value = "";
    }
}

// Render Active Document Cards
function renderDocuments() {
    documentList.innerHTML = "";

    if (indexedDocuments.length === 0) {
        emptyDocsState.style.display = "flex";
        documentList.appendChild(emptyDocsState);
        docCountBadge.textContent = "0 files";
        return;
    }

    emptyDocsState.style.display = "none";
    docCountBadge.textContent = `${indexedDocuments.length} file${indexedDocuments.length > 1 ? 's' : ''}`;

    indexedDocuments.forEach(doc => {
        const card = document.createElement("div");
        card.className = "doc-card";
        card.innerHTML = `
            <div class="doc-icon-wrapper">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
            </div>
            <div class="doc-info">
                <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
                <div class="doc-meta-badge">✓ ${doc.chunks} chunks indexed</div>
            </div>
        `;
        documentList.appendChild(card);
    });
}

// Handle User Chat Query
async function handleUserQuery() {
    const question = queryInput.value.trim();
    if (!question) return;

    // Hide welcome hero on first message
    welcomeHero.style.display = "none";

    // Add user message to UI
    appendMessage("user", question);
    queryInput.value = "";
    autoResizeTextarea();
    sendBtn.disabled = true;

    // Add temporary AI thinking loader
    const loadingId = appendLoadingIndicator();
    scrollToBottom();

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        // Remove thinking loader
        removeMessage(loadingId);

        if (!response.ok) {
            throw new Error(data.detail || "Failed to generate answer");
        }

        appendMessage("ai", data.answer);

    } catch (err) {
        removeMessage(loadingId);
        appendMessage("ai", `⚠️ **Error:** ${err.message}`);
        showToast(err.message, "error");
    } finally {
        sendBtn.disabled = false;
        scrollToBottom();
    }
}

// Append Message Row to Stream
function appendMessage(sender, text) {
    const msgId = "msg-" + Date.now();
    const row = document.createElement("div");
    row.className = `message-row ${sender}`;
    row.id = msgId;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = sender === "user" ? "U" : "AI";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = formatMarkdown(text);

    row.appendChild(avatar);
    row.appendChild(bubble);
    messageStream.appendChild(row);
    scrollToBottom();

    return msgId;
}

// Append Thinking / Loading Indicator
function appendLoadingIndicator() {
    const loadId = "loading-" + Date.now();
    const row = document.createElement("div");
    row.className = "message-row ai";
    row.id = loadId;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = "AI";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = `
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;

    row.appendChild(avatar);
    row.appendChild(bubble);
    messageStream.appendChild(row);

    return loadId;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// Markdown Formatter (Lightweight parser)
function formatMarkdown(text) {
    if (!text) return "";
    
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Code blocks ```code```
    html = html.replace(/```([a-z]*)
([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Bullet points
    html = html.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

    // Paragraphs
    html = html.split("

").map(para => {
        if (!para.startsWith("<pre>") && !para.startsWith("<ul>")) {
            return `<p>${para.replace(/
/g, "<br>")}</p>`;
        }
        return para;
    }).join("");

    return html;
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function clearChat() {
    messageStream.innerHTML = "";
    welcomeHero.style.display = "flex";
    showToast("Chat cleared", "success");
}

function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 4000);
}
