/**
 * DocChat AI - Interactive Web Application Logic
 * Integrates directly with FastAPI Backend (http://127.0.0.1:8000)
 */

// Safe API Base URL (works for localhost, 127.0.0.1, or custom host)
const API_BASE_URL = (window.location.origin && window.location.origin.startsWith("http")) 
    ? window.location.origin 
    : "http://127.0.0.1:8000";

console.log("[DocChat] API Base URL configured:", API_BASE_URL);

// State
let indexedDocuments = [];
try {
    indexedDocuments = JSON.parse(localStorage.getItem("docchat_documents") || "[]");
} catch (e) {
    indexedDocuments = [];
}

function initApp() {
    console.log("[DocChat] Initializing application...");
    
    // DOM Elements
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("fileInput");
    const promptForm = document.getElementById("promptForm");
    const queryInput = document.getElementById("queryInput");
    const sendBtn = document.getElementById("sendBtn");
    const clearChatBtn = document.getElementById("clearChatBtn");

    if (!dropzone || !queryInput || !promptForm) {
        console.error("[DocChat] Critical DOM elements missing!");
        return;
    }

    // 1. Initial Render & Health Check
    renderDocuments();
    checkBackendHealth();
    setInterval(checkBackendHealth, 8000);
    autoResizeTextarea();

    // 2. Dropzone & File Upload Listeners
    dropzone.onclick = () => {
        console.log("[DocChat] Dropzone clicked, opening file dialog...");
        fileInput.click();
    };

    fileInput.onchange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            console.log("[DocChat] File selected:", e.target.files[0].name);
            uploadFile(e.target.files[0]);
        }
    };

    dropzone.ondragover = (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    };

    dropzone.ondragleave = () => {
        dropzone.classList.remove("dragover");
    };

    dropzone.ondrop = (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            console.log("[DocChat] File dropped:", e.dataTransfer.files[0].name);
            uploadFile(e.dataTransfer.files[0]);
        }
    };

    // 3. Prompt Submission & Enter Key Listener
    promptForm.onsubmit = (e) => {
        e.preventDefault();
        console.log("[DocChat] Prompt form submitted via button/enter");
        handleUserQuery();
    };

    queryInput.onkeydown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            console.log("[DocChat] Enter key pressed in query input");
            handleUserQuery();
        }
    };

    queryInput.oninput = autoResizeTextarea;

    // 4. Starter Prompt Chips
    document.querySelectorAll(".prompt-chip").forEach(chip => {
        chip.onclick = () => {
            const prompt = chip.getAttribute("data-prompt");
            if (prompt) {
                queryInput.value = prompt;
                autoResizeTextarea();
                handleUserQuery();
            }
        };
    });

    // 5. Clear Chat
    if (clearChatBtn) {
        clearChatBtn.onclick = clearChat;
    }

    console.log("[DocChat] Application initialized successfully with all event listeners!");
}

// Ensure initApp runs regardless of document readyState
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}

// Auto-resizing textarea
function autoResizeTextarea() {
    const queryInput = document.getElementById("queryInput");
    if (!queryInput) return;
    queryInput.style.height = "auto";
    queryInput.style.height = Math.min(queryInput.scrollHeight, 160) + "px";
}

// Check Backend Health
async function checkBackendHealth() {
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    if (!statusDot || !statusText) return;

    try {
        const response = await fetch(`${API_BASE_URL}/docs`);
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

// Upload & Index Document
async function uploadFile(file) {
    const uploadProgress = document.getElementById("uploadProgress");
    const progressText = document.getElementById("progressText");
    const fileInput = document.getElementById("fileInput");

    const validExtensions = [".pdf", ".txt"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    
    if (!validExtensions.includes(ext)) {
        showToast("Only .pdf and .txt files are supported.", "error");
        return;
    }

    if (uploadProgress) uploadProgress.style.display = "flex";
    if (progressText) progressText.textContent = `Uploading & indexing ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        console.log(`[DocChat] Sending POST request to ${API_BASE_URL}/api/v1/documents/upload`);
        const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        console.log("[DocChat] Upload response:", data);

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

        indexedDocuments = indexedDocuments.filter(d => d.filename !== docEntry.filename);
        indexedDocuments.unshift(docEntry);
        localStorage.setItem("docchat_documents", JSON.stringify(indexedDocuments));

        renderDocuments();
        showToast(`Indexed ${data.chunks_indexed} chunks for ${data.filename}!`, "success");

    } catch (err) {
        console.error("[DocChat] Upload error:", err);
        showToast(err.message || "Failed to upload document", "error");
    } finally {
        if (uploadProgress) uploadProgress.style.display = "none";
        if (fileInput) fileInput.value = "";
    }
}

// Render Active Document Cards
function renderDocuments() {
    const documentList = document.getElementById("documentList");
    const emptyDocsState = document.getElementById("emptyDocsState");
    const docCountBadge = document.getElementById("docCountBadge");

    if (!documentList) return;

    documentList.innerHTML = "";

    if (indexedDocuments.length === 0) {
        if (emptyDocsState) {
            emptyDocsState.style.display = "flex";
            documentList.appendChild(emptyDocsState);
        }
        if (docCountBadge) docCountBadge.textContent = "0 files";
        return;
    }

    if (docCountBadge) {
        docCountBadge.textContent = `${indexedDocuments.length} file${indexedDocuments.length > 1 ? 's' : ''}`;
    }

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
                <div class="doc-meta-badge">&#10003; ${doc.chunks} chunks indexed</div>
            </div>
        `;
        documentList.appendChild(card);
    });
}

// Handle User Chat Query
async function handleUserQuery() {
    const queryInput = document.getElementById("queryInput");
    const welcomeHero = document.getElementById("welcomeHero");
    const sendBtn = document.getElementById("sendBtn");

    if (!queryInput) return;
    const question = queryInput.value.trim();
    if (!question) return;

    console.log("[DocChat] Processing user query:", question);

    if (welcomeHero) {
        welcomeHero.style.display = "none";
    }

    appendMessage("user", question);
    queryInput.value = "";
    autoResizeTextarea();
    if (sendBtn) sendBtn.disabled = true;

    const loadingId = appendLoadingIndicator();
    scrollToBottom();

    try {
        console.log(`[DocChat] Sending POST request to ${API_BASE_URL}/api/v1/chat`);
        const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });

        const data = await response.json();
        console.log("[DocChat] Chat response:", data);

        removeMessage(loadingId);

        if (!response.ok) {
            throw new Error(data.detail || "Failed to generate answer");
        }

        appendMessage("ai", data.answer);

    } catch (err) {
        console.error("[DocChat] Chat error:", err);
        removeMessage(loadingId);
        appendMessage("ai", `⚠️ **Error:** ${err.message}`);
        showToast(err.message, "error");
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        scrollToBottom();
        queryInput.focus();
    }
}

// Append Message Row to Stream
function appendMessage(sender, text) {
    const messageStream = document.getElementById("messageStream");
    if (!messageStream) return;

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
    const messageStream = document.getElementById("messageStream");
    if (!messageStream) return "";

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
    html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
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
    html = html.split("\n\n").map(para => {
        if (!para.startsWith("<pre>") && !para.startsWith("<ul>")) {
            return `<p>${para.replace(/\n/g, "<br>")}</p>`;
        }
        return para;
    }).join("");

    return html;
}

function scrollToBottom() {
    const chatContainer = document.getElementById("chatContainer");
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

function clearChat() {
    const messageStream = document.getElementById("messageStream");
    const welcomeHero = document.getElementById("welcomeHero");
    if (messageStream) messageStream.innerHTML = "";
    if (welcomeHero) welcomeHero.style.display = "flex";
    showToast("Chat history cleared", "success");
}

function showToast(message, type = "success") {
    const toastContainer = document.getElementById("toastContainer");
    if (!toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 4000);
}
