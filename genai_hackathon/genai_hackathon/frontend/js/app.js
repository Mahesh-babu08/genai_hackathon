// Tab Switching
const tabs = document.querySelectorAll('.tab-btn');
const contents = document.querySelectorAll('.tab-content');

// Helper to show a specific tab
function showTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });

    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(button => {
        button.classList.remove('border-blue-500', 'text-white', 'active');
        button.classList.add('border-transparent', 'text-slate-400');
    });

    // Show selected tab content
    const contentId = (tabName === 'github') ? 'githubContent' : `tab-${tabName}`;
    const content = document.getElementById(contentId);
    if (content) content.classList.remove('hidden');

    // Add active class to selected tab button
    // Handle both data-tab and onClick styles
    const tabSelector = (tabName === 'github') ? '#githubTab' : `[data-tab="${tabName}"]`;
    const tabButton = document.querySelector(tabSelector);

    if (tabButton) {
        if (tabName === 'github') {
            // GitHub tab has different styling in user request, but let's try to match existing if possible or use user's custom style
            tabButton.classList.add('text-white', 'bg-gray-800'); // User requested style classes
            tabButton.classList.remove('text-gray-400');
        } else {
            tabButton.classList.remove('border-transparent', 'text-slate-400');
            tabButton.classList.add('border-blue-500', 'text-white', 'active');
        }
    }

    // If GitHub tab, check connection
    if (tabName === 'github') {
        checkGitHubConnection();
    }
}


tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const target = tab.dataset.tab;
        showTab(target);
    });
});

// App Logic
const API_URL = 'http://127.0.0.1:8000/api';

const codeInput = document.getElementById('code-input');
const langSelect = document.getElementById('language-select');
const loader = document.getElementById('loader');

const clearCodeBtn = document.getElementById('clear-code');
if (clearCodeBtn) {
    clearCodeBtn.addEventListener('click', () => {
        codeInput.value = '';
        codeInput.focus();
    });
}

function getFocusAreas() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

async function postData(endpoint, data) {
    loader.classList.remove('hidden');
    try {
        const response = await fetch(`${API_URL}/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail?.user_message || errData.detail?.message || `Error: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error("API Error:", error);
        alert("An error occurred. Check console for details.");
        return null;
    } finally {
        loader.classList.add('hidden');
    }
}

// Review Logic
const btnReview = document.getElementById('btn-review');
if (btnReview) {
    btnReview.addEventListener('click', async () => {
        const code = codeInput.value;
        if (!code.trim()) return alert("Please enter some code first.");

        // Switch to review tab
        showTab('review');

        const data = await postData('review', {
            code: code,
            language: langSelect.value,
            focus_areas: getFocusAreas(),
            calculate_score: true
        });

        if (data) {
            document.getElementById('review-empty').classList.add('hidden');
            document.getElementById('review-content').classList.remove('hidden');

            // Display Scores
            if (data.quality_scores) {
                displayQualityScores(data.quality_scores);
            }

            // Update counts
            document.getElementById('count-critical').textContent = data.critical ? data.critical.length : 0;
            document.getElementById('count-high').textContent = data.high ? data.high.length : 0;
            document.getElementById('count-medium').textContent = data.medium ? data.medium.length : 0;
            document.getElementById('count-low').textContent = data.low ? data.low.length : 0;

            // Update text
            document.getElementById('review-summary').textContent = data.summary || "No summary provided.";

            // Render Markdown
            document.getElementById('review-markdown').innerHTML = marked.parse(data.raw_review || "");
        }
    });
}

// Rewrite Logic
const btnRewrite = document.getElementById('btn-rewrite');
if (btnRewrite) {
    btnRewrite.addEventListener('click', async () => {
        const code = codeInput.value;
        if (!code.trim()) return alert("Please enter some code first.");

        // Switch to rewrite tab
        showTab('rewrite');

        const data = await postData('rewrite', {
            code: code,
            language: langSelect.value,
            focus_areas: getFocusAreas()
        });

        if (data) {
            document.getElementById('rewrite-empty').classList.add('hidden');
            document.getElementById('rewrite-content').classList.remove('hidden');
            document.getElementById('improvements-panel').classList.remove('hidden');

            // Update Code display
            document.getElementById('original-code-display').textContent = code;

            let cleanCode = data.rewritten_code;
            if (cleanCode.startsWith('```')) {
                const matches = cleanCode.match(/```(?:\w+)?\n([\s\S]*?)```/);
                if (matches && matches[1]) cleanCode = matches[1];
            }

            const rewrittenBlock = document.getElementById('rewritten-code-display');
            rewrittenBlock.textContent = cleanCode;

            // Highlight
            hljs.highlightElement(document.getElementById('original-code-display'));
            hljs.highlightElement(rewrittenBlock);

            // Improvements
            document.getElementById('improvements-list').innerHTML = marked.parse(data.improvements || "");
        }
    });
}

function copyText(elementId) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
        // Could show a toast here
        const btn = event.currentTarget; // This might fail if called from inline onclick. 
        // Need to pass event or handle differently. Use closest button.
        // But for now keeping as is from original code.
        alert('Copied!');
    });
}

// --- AI Chat Logic ---
const chatInput = document.getElementById('chat-input');
const chatHistory = document.getElementById('chat-history');
const typingIndicator = document.getElementById('typing-indicator');
const sendChatBtn = document.getElementById('send-chat');
const clearChatBtn = document.getElementById('clear-chat');

function getLatestReviewSummary() {
    const summaryEl = document.getElementById('review-summary');
    return summaryEl ? summaryEl.textContent : "";
}

function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `flex gap-4 ${role === 'user' ? 'flex-row-reverse' : ''}`;

    const avatar = role === 'ai'
        ? `<div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0">🤖</div>`
        : `<div class="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center shrink-0"><i class="fas fa-user"></i></div>`;

    const bubbleClass = role === 'ai'
        ? 'bg-slate-800/80 border border-slate-700 rounded-tl-none'
        : 'bg-blue-600 text-white rounded-tr-none';

    // Parse Markdown for AI, text for User
    const content = role === 'ai' ? marked.parse(text) : text.replace(/\n/g, '<br>');

    div.innerHTML = `
        ${avatar}
        <div class="${bubbleClass} p-4 rounded-2xl max-w-[80%] text-sm ${role === 'ai' ? 'text-slate-300 markdown-body' : ''}">
            ${content}
            ${role === 'ai' ? `
            <div class="mt-2 flex justify-end">
                <button class="text-xs text-slate-500 hover:text-white transition-colors" onclick="navigator.clipboard.writeText(this.parentElement.parentElement.innerText).then(() => alert('Copied!'))">
                    <i class="fas fa-copy mr-1"></i>Copy
                </button>
            </div>` : ''}
        </div>
    `;

    chatHistory.appendChild(div);
    if (role === 'ai') {
        div.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }
    scrollToBottom();
}

function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function showTyping() {
    typingIndicator.classList.remove('hidden');
    scrollToBottom();
}

function hideTyping() {
    typingIndicator.classList.add('hidden');
}

async function handleSendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    chatInput.value = '';
    appendMessage('user', message);
    showTyping();

    const context = {
        message: message,
        language: langSelect.value,
        context_code: codeInput.value,
        review_summary: getLatestReviewSummary()
    };

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(context)
        });

        if (!response.ok) throw new Error(`Error: ${response.statusText}`);
        const data = await response.json();

        hideTyping();
        appendMessage('ai', data.reply);

    } catch (error) {
        console.error("Chat Error:", error);
        hideTyping();
        appendMessage('ai', "⚠️ Sorry, I encountered an error creating a response.");
    }
}

if (sendChatBtn) sendChatBtn.addEventListener('click', handleSendMessage);

if (chatInput) {
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSendMessage();
        }
    });
}

if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
        if (confirm("Clear chat history?")) {
            const welcome = chatHistory.firstElementChild;
            chatHistory.innerHTML = '';
            chatHistory.appendChild(welcome);
        }
    });
}


// --- GitHub Integration ---

async function checkGitHubConnection() {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');

    if (!statusIndicator || !statusText) return;

    try {
        // Note: Using relative path to match API_URL structure or root relative
        const response = await fetch('/api/github/installations');

        if (!response.ok) {
            throw new Error('Failed to fetch installations');
        }

        const data = await response.json();

        if (data.installations && data.installations.length > 0) {
            statusIndicator.className = 'w-3 h-3 bg-green-500 rounded-full animate-pulse';
            statusText.textContent = `✅ Connected to ${data.installations.length} installation(s)`;
            statusText.className = 'text-green-400 font-semibold';

            // Display installations
            displayInstallations(data.installations);
        } else {
            statusIndicator.className = 'w-3 h-3 bg-yellow-500 rounded-full';
            statusText.textContent = '⚠️ Not connected - Install the GitHub App first';
            statusText.className = 'text-yellow-400';
        }

    } catch (error) {
        console.error('Error checking GitHub connection:', error);
        statusIndicator.className = 'w-3 h-3 bg-red-500 rounded-full';
        statusText.textContent = '❌ Error checking connection';
        statusText.className = 'text-red-400';
    }
}

function displayInstallations(installations) {
    const activityDiv = document.getElementById('recentActivity');
    if (!activityDiv) return;

    activityDiv.innerHTML = installations.map(inst => `
        <div class="bg-gray-700 rounded-lg p-4 mb-3 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                    ${inst.account.toUpperCase().substring(0, 2)}
                </div>
                <div>
                    <div class="text-white font-semibold">${inst.account}</div>
                    <div class="text-sm text-gray-400">Type: ${inst.type}</div>
                </div>
            </div>
            <div class="text-sm text-green-400">
                ✓ Active
            </div>
        </div>
    `).join('');
}

// Check connection on load if we are on the page
document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('githubTab')) {
        checkGitHubConnection();
    }
});

// --- Bumble Launch Logic ---
async function launchBumble() {
    const btn = document.getElementById('btn-bumble');
    const originalContent = btn.innerHTML;

    // Loading state
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-circle-notch fa-spin"></i> Launching...`;

    try {
        const response = await fetch(`${API_URL}/bumble/launch`, {
            method: 'POST'
        });

        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || 'Failed to launch');

        // Success state
        btn.innerHTML = `<i class="fas fa-check"></i> Launched!`;
        btn.classList.remove('from-pink-500', 'to-purple-600');
        btn.classList.add('bg-green-500');

        // Reset after 2 seconds
        setTimeout(() => {
            btn.innerHTML = originalContent;
            btn.disabled = false;
            btn.classList.remove('bg-green-500');
            btn.classList.add('from-pink-500', 'to-purple-600');
        }, 2000);

    } catch (error) {
        console.error('Bumble Launch Error:', error);

        // Error state
        btn.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Error`;
        btn.classList.remove('from-pink-500', 'to-purple-600');
        btn.classList.add('bg-red-500');

        alert(`Failed to launch Bumble:\n${error.message}`);

        // Reset
        setTimeout(() => {
            btn.innerHTML = originalContent;
            btn.disabled = false;
            btn.classList.remove('bg-red-500');
            btn.classList.add('from-pink-500', 'to-purple-600');
        }, 3000);
    }
}
