from .github_service import github_service
from .patchwork_service import patchwork_service
import asyncio

class PatchworkGitHub:
    async def review_pr(self, repo_full_name: str, pr_number: int, installation_id: int):
        try:
            print(f"Starting review for PR #{pr_number} in {repo_full_name}")
            pr_data = github_service.get_pr_diff(repo_full_name, pr_number, installation_id)
            
            review_results = []
            
            for file in pr_data["files"]:
                # Simple language detection
                language = self._detect_language(file["filename"])
                if not language:
                    continue
                    
                print(f"Reviewing {file['filename']} ({language})...")
                # Run review
                # Since patchwork_service.review_code is synchronous (wraps sync Groq client), 
                # we can run it directly or in thread pool if we want to be async. 
                # For now, running synchronously in the background task is acceptable for simplicity,
                # but blocking the event loop is bad practice. 
                # However, since this is running in a BackgroundTask from FastAPI, 
                # it's running in a separate context but still on the main thread if unrelated to async def.
                # Ideally we should offload to thread.
                
                review = await asyncio.to_thread(
                    patchwork_service.review_code, 
                    file["content"], 
                    language
                )
                
                if "error" not in review:
                    review_results.append({
                        "filename": file["filename"],
                        "issues": review
                    })
            
            if review_results:
                comment = self._format_review_comment(review_results)
                github_service.post_pr_comment(repo_full_name, pr_number, comment, installation_id)
                print(f"Posted review comment for PR #{pr_number}")
                
            return {"pr_number": pr_number, "files_reviewed": len(review_results), "comment_posted": bool(review_results)}

        except Exception as e:
            print(f"Error reviewing PR: {e}")
            return {"error": str(e)}

    async def autofix_pr(self, repo_full_name: str, pr_number: int, installation_id: int):
        try:
            print(f"Starting autofix for PR #{pr_number} in {repo_full_name}")
            pr_data = github_service.get_pr_diff(repo_full_name, pr_number, installation_id)
            
            fixed_files = {}
            vulnerabilities_resolved = 0
            
            for file in pr_data["files"]:
                language = self._detect_language(file["filename"])
                if not language:
                    continue
                    
                print(f"Autofixing {file['filename']}...")
                result = await asyncio.to_thread(
                    patchwork_service.rewrite_code,
                    file["content"],
                    language
                )
                
                if "error" not in result and result.get("rewritten_code"):
                    # Basic check if code changed (ignoring whitespace might be better but strictly different is okay)
                    if result["rewritten_code"].strip() != file["content"].strip():
                        fixed_files[file["filename"]] = result["rewritten_code"]
                        # We don't have exact count of vulnerabilities resolved without parsing improvements text
                        # Just incrementing for activity tracking
                        vulnerabilities_resolved += 1
            
            commit_sha = None
            if fixed_files:
                commit_message = "🤖 AI Auto-fix: Improved code quality and security"
                commit_sha = github_service.create_commit(
                    repo_full_name, 
                    pr_data["head_branch"], 
                    fixed_files, 
                    commit_message, 
                    installation_id
                )
                
                summary = f"## 🛠️ Patchwork Auto-Fix\n\nI have applied fixes to **{len(fixed_files)} files**.\n\n"
                summary += f"Commit: `{commit_sha}`\n\n"
                summary += "### Changes\n"
                for fname in fixed_files:
                    summary += f"- ✅ Rewrote `{fname}` to improve quality/security.\n"
                    
                github_service.post_pr_comment(repo_full_name, pr_number, summary, installation_id)
                print(f"Created commit {commit_sha} and posted summary.")
                
            return {
                "pr_number": pr_number, 
                "files_fixed": len(fixed_files), 
                "commit_sha": commit_sha
            }

        except Exception as e:
            print(f"Error autofixing PR: {e}")
            return {"error": str(e)}

    def _detect_language(self, filename: str) -> str:
        ext = filename.split('.')[-1].lower()
        mapping = {
            'py': 'Python', 'js': 'JavaScript', 'ts': 'TypeScript', 
            'java': 'Java', 'cpp': 'C++', 'c': 'C', 'go': 'Go', 
            'rs': 'Rust', 'php': 'PHP', 'rb': 'Ruby', 'html': 'HTML', 
            'css': 'CSS', 'jsx': 'React JavaScript', 'tsx': 'React TypeScript'
        }
        return mapping.get(ext)

    def _format_review_comment(self, review_results: list) -> str:
        md = "## 🤖 API Code Review\n\n"
        
        for item in review_results:
            fname = item["filename"]
            issues = item["issues"]
            
            md += f"<details>\n<summary><strong>📄 {fname}</strong></summary>\n\n"
            
            if issues.get("critical"):
                md += "### 🔴 Critical Issues\n"
                for bug in issues["critical"]:
                    md += f"- {bug}\n"
                md += "\n"
                
            if issues.get("high"):
                md += "### 🟠 High Priority\n"
                for bug in issues["high"]:
                    md += f"- {bug}\n"
                md += "\n"
                
            if issues.get("medium"):
                md += "### 🟡 Medium Priority\n"
                for bug in issues["medium"]:
                    md += f"- {bug}\n"
                md += "\n"
                
            if issues.get("summary"):
                md += f"**Summary:** {issues['summary']}\n"
                
            md += "\n</details>\n\n"
            
        md += "---\n*Powered by Patchwork AI*"
        return md

patchwork_github = PatchworkGitHub()
