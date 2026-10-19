/**
 * DocChat AI - Enterprise Web Application Logic
 * Integrates directly with FastAPI Backend (http://127.0.0.1:8000)
 * Uses Unified Canonical Chat Endpoint (POST /api/v1/chat with stream=true)
 * Full Support for Correlation IDs (X-Request-ID) and Standardized RFC-7807 Error Handlers
 */

// Robust API Base URL detection
const API_BASE_URL = (window.location.protocol.startsWith("http") && (window.location.port === "8000" || window.location.port === "")) 
    ? window.location.origin 
    : "http://127.0.0.1:8000";

console.log("[DocChat Enterprise] API Base URL configured:", API_BASE_URL);

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
    const queryInput = document.getElementById("queryInput");
    const sendBtn = document.getElementById("sendBtn");
    const addFilesBtn = document.getElementById("addFilesBtn");
    const webSearchBtn = document.getElementById("webSearchBtn");
    const clearChatBtn = document.getElementById("clearChatBtn");
    const manageDocsBtn = document.getElementById("manageDocsBtn");

    if (!queryInput || !sendBtn) {
        console.error("[DocChat] Critical DOM elements missing!");
        return;
    }

    // 1. Initial Render & Health Check
    renderDocuments();
    checkBackendHealth();
    setInterval(checkBackendHealth, 8000);
    autoResizeTextarea();

    // 2. Dropzone & File Upload Listeners
    if (dropzone && fileInput) {
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
    }

    // Add Files button on prompt dock
    if (addFilesBtn && fileInput) {
        addFilesBtn.onclick = () => {
            fileInput.click();
        };
    }

    // Web Search button toggle
    if (webSearchBtn) {
        webSearchBtn.onclick = () => {
            webSearchBtn.classList.toggle("active");
            const isActive = webSearchBtn.classList.contains("active");
            showToast(isActive ? "Web Search enabled" : "Web Search disabled", "success");
        };
    }

    // Manage Docs button
    if (manageDocsBtn && fileInput) {
        manageDocsBtn.onclick = () => {
            fileInput.click();
        };
    }

    // 3. Prompt Submission & Enter Key Listener
    sendBtn.onclick = () => {
        handleUserQuery();
    };

    queryInput.onkeydown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
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

    console.log("[DocChat] Enterprise application initialized successfully!");
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
        console.log(`[DocChat] Sending upload to ${API_BASE_URL}/api/v1/documents/upload`);
        const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        console.log("[DocChat] Upload response:", data);

        if (!response.ok) {
            const errorMsg = data.message || data.detail || "Upload failed";
            throw new Error(errorMsg);
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

// Handle Real-Time Streaming User Chat Query via Unified Endpoint
async function handleUserQuery() {
    const queryInput = document.getElementById("queryInput");
    const welcomeHero = document.getElementById("welcomeHero");
    const sendBtn = document.getElementById("sendBtn");

    if (!queryInput) return;
    const question = queryInput.value.trim();
    if (!question) return;

    console.log("[DocChat] Submitting query to unified endpoint:", question);

    if (welcomeHero) {
        welcomeHero.style.display = "none";
    }

    // Add user message to UI
    appendMessage("user", question);
    queryInput.value = "";
    autoResizeTextarea();
    if (sendBtn) sendBtn.disabled = true;

    // Create placeholder AI message bubble for streaming
    const aiMsgId = appendMessage("ai", "");
    const aiBubble = document.querySelector(`#${aiMsgId} .msg-bubble`);
    
    // Show typing dots while waiting for first token
    if (aiBubble) {
        aiBubble.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
    }
    scrollToBottom();

    let accumulatedText = "";
    let firstTokenReceived = false;
    let requestId = null;

    try {
        console.log(`[DocChat] Requesting unified chat: ${API_BASE_URL}/api/v1/chat (stream: true)`);
        const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json"
            },
            body: JSON.stringify({ question, stream: true })
        });

        requestId = response.headers.get("X-Request-ID");

        if (!response.ok) {
            let errorObj = {
                status_code: response.status,
                error_code: `HTTP_${response.status}`,
                message: `Server returned error ${response.status}`,
                request_id: requestId
            };

            try {
                const errData = await response.json();
                if (errData) {
                    errorObj.message = errData.message || errData.detail || errorObj.message;
                    errorObj.error_code = errData.error_code || errorObj.error_code;
                    errorObj.request_id = errData.request_id || requestId;
                }
            } catch (e) {}

            renderEnterpriseError(aiBubble, errorObj);
            showToast(errorObj.message, "error");
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop(); // keep incomplete trailing line in buffer

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || !trimmed.startsWith("data:")) continue;

                const dataStr = trimmed.slice(5).trim();
                if (dataStr === "[DONE]") {
                    console.log("[DocChat] SSE Stream completed: [DONE]");
                    break;
                }

                try {
                    const parsed = JSON.parse(dataStr);
                    if (parsed.error) {
                        const errDetails = typeof parsed.error === "object" ? parsed.error : { message: parsed.error };
                        renderEnterpriseError(aiBubble, {
                            status_code: 400,
                            error_code: errDetails.code || "CHAT_ERROR",
                            message: errDetails.message || "An error occurred during generation.",
                            request_id: errDetails.request_id || requestId
                        });
                        showToast(errDetails.message || "Chat error", "error");
                        return;
                    }

                    if (parsed.token) {
                        if (!firstTokenReceived) {
                            firstTokenReceived = true;
                            if (aiBubble) aiBubble.innerHTML = "";
                        }
                        accumulatedText += parsed.token;
                        if (aiBubble) {
                            aiBubble.innerHTML = formatMarkdown(accumulatedText);
                        }
                        scrollToBottom();
                    }
                } catch (parseErr) {
                    if (parseErr.message && !parseErr.message.includes("JSON")) {
                        throw parseErr;
                    }
                }
            }
        }

        // Final render after stream ends
        if (aiBubble && accumulatedText) {
            aiBubble.innerHTML = formatMarkdown(accumulatedText);
        }

    } catch (err) {
        console.error("[DocChat] Chat execution error:", err);
        renderEnterpriseError(aiBubble, {
            status_code: 500,
            error_code: "NETWORK_OR_CLIENT_ERROR",
            message: err.message || "Failed to communicate with DocChat API.",
            request_id: requestId
        });
        showToast(err.message || "Failed to communicate with DocChat backend.", "error");
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        scrollToBottom();
        queryInput.focus();
    }
}

// Render Enterprise Error Card in Message Stream
function renderEnterpriseError(container, errorObj) {
    if (!container) return;
    const reqBadge = errorObj.request_id 
        ? `<div style="margin-top: 8px; font-size: 11px; opacity: 0.8; font-family: monospace;">Trace ID: <code>${errorObj.request_id}</code></div>`
        : "";

    container.innerHTML = `
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; padding: 10px 14px; border-radius: 6px; color: #fca5a5;">
            <div style="font-weight: 600; font-size: 13px; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
                <span>⚠️ [${errorObj.error_code || 'ERROR'}]</span>
            </div>
            <div style="font-size: 13px; color: #f1f5f9;">${errorObj.message}</div>
            ${reqBadge}
        </div>
    `;
}

// Append Message Row to Stream
function appendMessage(sender, text) {
    const messageStream = document.getElementById("messageStream");
    if (!messageStream) return "";

    const msgId = "msg-" + Date.now();
    const row = document.createElement("div");
    row.className = `message-row ${sender}`;
    row.id = msgId;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = sender === "user" ? "U" : "AI";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = text ? formatMarkdown(text) : "";

    row.appendChild(avatar);
    row.appendChild(bubble);
    messageStream.appendChild(row);
    scrollToBottom();

    return msgId;
}

// Markdown Formatter
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
