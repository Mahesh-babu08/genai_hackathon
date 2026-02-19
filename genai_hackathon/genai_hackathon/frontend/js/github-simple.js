// GitHub Simple Integration JavaScript

let githubTokenValid = false;

async function validateGitHubToken() {
    const token = document.getElementById('githubToken').value.trim();
    const statusDiv = document.getElementById('tokenStatus');

    if (!token) {
        statusDiv.innerHTML = '<span class="text-red-400">❌ Token required</span>';
        githubTokenValid = false;
        return;
    }

    statusDiv.innerHTML = '<span class="text-gray-400">🔄 Validating...</span>';

    try {
        const response = await fetch('/api/github-simple/validate-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ github_token: token })
        });

        const data = await response.json();

        if (data.valid) {
            statusDiv.innerHTML = `<span class="text-green-400">✅ Valid token for @${data.username}</span>`;
            githubTokenValid = true;
            localStorage.setItem('github_token', token);
        } else {
            statusDiv.innerHTML = '<span class="text-red-400">❌ Invalid token</span>';
            githubTokenValid = false;
        }
    } catch (error) {
        statusDiv.innerHTML = '<span class="text-red-400">❌ Validation failed</span>';
        githubTokenValid = false;
    }
}

async function analyzePR(postComment) {
    const token = document.getElementById('githubToken').value.trim();
    const prUrl = document.getElementById('prUrl').value.trim();

    if (!token) {
        alert('Please provide GitHub token');
        return;
    }

    if (!prUrl) {
        alert('Please provide PR URL');
        return;
    }

    // Show loading
    const resultsDiv = document.getElementById('prReviewResults');
    const contentDiv = document.getElementById('prReviewContent');
    resultsDiv.classList.remove('hidden');
    contentDiv.innerHTML = `
        <div class="flex flex-col items-center justify-center py-12">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mb-4"></div>
            <p class="text-gray-300">Analyzing pull request...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/github-simple/analyze-pr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pr_url: prUrl,
                github_token: token,
                post_comment: postComment
            })
        });

        if (!response.ok) {
            throw new Error('Analysis failed');
        }

        const data = await response.json();

        if (data.success) {
            displayPRReview(data);

            if (postComment && data.comment_posted) {
                // Using alert for simplicity if showToast is not defined
                if (typeof showToast === 'function') {
                    showToast('✅ Review comment posted to PR!', 'success');
                } else {
                    alert('✅ Review comment posted to PR!');
                }
            }
        } else {
            throw new Error(data.error || 'Analysis returned error');
        }

    } catch (error) {
        contentDiv.innerHTML = `
            <div class="bg-red-500/20 border border-red-500 rounded-lg p-4">
                <p class="text-red-400">❌ Error: ${error.message}</p>
            </div>
        `;
    }
}

async function autofixPR(autoCommit) {
    const token = document.getElementById('githubToken').value.trim();
    const prUrl = document.getElementById('prUrl').value.trim();

    if (!token || !prUrl) {
        alert('Please provide both token and PR URL');
        return;
    }

    const resultsDiv = document.getElementById('prReviewResults');
    const contentDiv = document.getElementById('prReviewContent');
    resultsDiv.classList.remove('hidden');
    contentDiv.innerHTML = `
        <div class="flex flex-col items-center justify-center py-12">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-green-500 mb-4"></div>
            <p class="text-gray-300">Running auto-fix...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/github-simple/autofix-pr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pr_url: prUrl,
                github_token: token,
                auto_commit: autoCommit
            })
        });

        const data = await response.json();

        if (data.success) {
            displayAutofixResults(data);

            if (autoCommit && data.commit_sha) {
                if (typeof showToast === 'function') {
                    showToast('✅ Fixes committed to PR branch!', 'success');
                } else {
                    alert('✅ Fixes committed to PR branch!');
                }
            }
        } else {
            throw new Error(data.error || 'Auto-fix failed');
        }

    } catch (error) {
        contentDiv.innerHTML = `
            <div class="bg-red-500/20 border border-red-500 rounded-lg p-4">
                <p class="text-red-400">❌ Error: ${error.message}</p>
            </div>
        `;
    }
}

function displayPRReview(data) {
    const contentDiv = document.getElementById('prReviewContent');

    let html = `
        <div class="mb-6">
            <h4 class="text-lg font-semibold text-white mb-2">
                PR #${data.pr_info.pr_number}: ${data.pr_info.title}
            </h4>
            <p class="text-sm text-gray-400">
                by ${data.pr_info.author} | ${data.review_results.length} files reviewed
            </p>
        </div>
    `;

    data.review_results.forEach(result => {
        html += `
            <div class="bg-gray-800 rounded-lg p-4 mb-4">
                <h5 class="text-white font-semibold mb-3">📄 ${result.filename}</h5>
                <div class="space-y-2">
                    ${result.review ? `
                        <div class="text-gray-300 text-sm whitespace-pre-wrap markdown-body">${marked.parse(result.review)}</div>
                    ` : '<div class="text-gray-500 text-sm">No issues found</div>'}
                </div>
            </div>
        `;
    });

    if (data.comment_posted) {
        html += `
            <div class="bg-green-500/20 border border-green-500 rounded-lg p-4 mt-4">
                <p class="text-green-400">✅ Review comment posted to PR</p>
            </div>
        `;
    }

    contentDiv.innerHTML = html;
}

function displayAutofixResults(data) {
    const contentDiv = document.getElementById('prReviewContent');

    let html = `
        <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="bg-green-500/20 border border-green-500 rounded-lg p-4">
                <div class="text-3xl font-bold text-green-400">${data.files_fixed}</div>
                <div class="text-sm text-gray-400">Files Fixed</div>
            </div>
            <div class="bg-blue-500/20 border border-blue-500 rounded-lg p-4">
                <div class="text-3xl font-bold text-blue-400">${data.vulnerabilities_resolved}</div>
                <div class="text-sm text-gray-400">Issues Resolved</div>
            </div>
            <div class="bg-purple-500/20 border border-purple-500 rounded-lg p-4">
                <div class="text-3xl font-bold text-purple-400">${data.commit_sha ? '✓' : '—'}</div>
                <div class="text-sm text-gray-400">Committed</div>
            </div>
        </div>
    `;

    if (Object.keys(data.fixed_files).length > 0) {
        html += '<h5 class="text-white font-semibold mb-3">Fixed Files:</h5>';
        Object.keys(data.fixed_files).forEach(filename => {
            html += `
                <div class="bg-gray-800 rounded-lg p-3 mb-2 text-gray-300 text-sm">
                    ✅ ${filename}
                </div>
            `;
        });
    }

    if (data.commit_sha) {
        html += `
            <div class="bg-green-500/20 border border-green-500 rounded-lg p-4 mt-4">
                <p class="text-green-400">✅ Commit: ${data.commit_sha.substring(0, 7)}</p>
            </div>
        `;
    }

    contentDiv.innerHTML = html;
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Load saved token on page load
document.addEventListener('DOMContentLoaded', () => {
    const savedToken = localStorage.getItem('github_token');
    if (savedToken) {
        // Only set if element exists (in case user switches tabs and this loads on other pages)
        const tokenInput = document.getElementById('githubToken');
        if (tokenInput) {
            tokenInput.value = savedToken;
            validateGitHubToken();
        }
    }
});
