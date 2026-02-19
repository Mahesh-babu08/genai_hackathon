from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from services.github_simple import github_simple
from services.groq_service import get_groq_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/github-simple", tags=["github-simple"])

class PRRequest(BaseModel):
    pr_url: str
    github_token: str
    post_comment: bool = False

class AutofixRequest(BaseModel):
    pr_url: str
    github_token: str
    auto_commit: bool = False

@router.post("/analyze-pr")
async def analyze_pr(request: PRRequest):
    """
    Analyze PR and optionally post comment.
    NO BRANCH/COMMIT OPERATIONS - COMMENTS ONLY.
    """
    try:
        pr_info = github_simple.parse_pr_url(request.pr_url)
        
        pr_data = await github_simple.fetch_pr_data(
            pr_info["owner"],
            pr_info["repo"],
            pr_info["number"],
            request.github_token
        )
        
        groq = get_groq_service()
        review_results = []
        
        for file in pr_data["files_changed"]:
            if file["status"] == "removed" or not file["content"]:
                continue
            
            language = github_simple.detect_language(file["filename"])
            result = groq.review_code(
                code=file["content"],
                language=language,
                focus_areas=["bugs", "security", "performance"]
            )
            
            if result.get("success"):
                review_results.append({
                    "filename": file["filename"],
                    "review": result["review_text"],
                    "counts": result["counts"]
                })
        
        formatted_review = format_review_markdown(review_results, pr_data)
        
        comment_posted = False
        if request.post_comment:
            comment_result = await github_simple.post_pr_comment(
                pr_info["owner"],
                pr_info["repo"],
                pr_info["number"],
                formatted_review,
                request.github_token
            )
            
            if not comment_result["success"]:
                return {
                    "success": False,
                    "error": comment_result.get("error"),
                    "message": comment_result.get("message"),
                    "review_results": review_results,
                    "formatted_review": formatted_review,
                    "pr_info": pr_data,
                    "comment_posted": False
                }
            
            comment_posted = True
        
        return {
            "success": True,
            "pr_info": pr_data,
            "review_results": review_results,
            "formatted_review": formatted_review,
            "comment_posted": comment_posted
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/autofix-pr")
async def autofix_pr(request: AutofixRequest):
    """Auto-fix and optionally commit. REQUIRES BRANCH ACCESS."""
    try:
        pr_info = github_simple.parse_pr_url(request.pr_url)
        
        pr_data = await github_simple.fetch_pr_data(
            pr_info["owner"],
            pr_info["repo"],
            pr_info["number"],
            request.github_token
        )
        
        # Check PR state
        if pr_data["state"] != "open":
            return {
                "success": False,
                "error": "pr_closed",
                "message": f"PR is {pr_data['state']}. Cannot commit."
            }
        
        groq = get_groq_service()
        fixed_files = {}
        vuln_count = 0
        
        for file in pr_data["files_changed"]:
            if file["status"] == "removed" or not file["content"]:
                continue
            
            language = github_simple.detect_language(file["filename"])
            
            review = groq.review_code(
                code=file["content"],
                language=language,
                focus_areas=["bugs", "security"]
            )
            
            if review.get("success"):
                counts = review["counts"]
                issues = counts.get("critical", 0) + counts.get("high", 0)
                
                if issues > 0:
                    rewrite = groq.rewrite_code(
                        code=file["content"],
                        language=language
                    )
                    
                    if rewrite.get("success"):
                        fixed_code = rewrite["rewritten_code"]
                        if fixed_code != file["content"]:
                            fixed_files[file["filename"]] = fixed_code
                            vuln_count += issues
        
        commit_sha = None
        if request.auto_commit and fixed_files:
            commit_result = await github_simple.create_commit_with_fixes(
                pr_info["owner"],
                pr_info["repo"],
                pr_data["head_branch"],  # Use PR's head branch
                fixed_files,
                f"🤖 Auto-fix: Resolved {vuln_count} issues",
                request.github_token
            )
            
            if not commit_result["success"]:
                return {
                    "success": False,
                    "error": commit_result.get("error"),
                    "message": commit_result.get("message"),
                    "fixed_files": fixed_files,
                    "files_fixed": len(fixed_files),
                    "vulnerabilities_resolved": vuln_count
                }
            
            commit_sha = commit_result["commit_sha"]
            
            # Post summary
            file_list = ''.join(f'- `{f}`\n' for f in fixed_files.keys())
            summary = f"""## 🤖 Auto-Fix Applied

✅ Fixed {len(fixed_files)} file(s)
🔒 Resolved {vuln_count} issue(s)
📝 Commit: `{commit_sha[:7]}`

Files:
{file_list}"""
            
            await github_simple.post_pr_comment(
                pr_info["owner"],
                pr_info["repo"],
                pr_info["number"],
                summary,
                request.github_token
            )
        
        return {
            "success": True,
            "files_fixed": len(fixed_files),
            "vulnerabilities_resolved": vuln_count,
            "fixed_files": fixed_files,
            "commit_sha": commit_sha
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-token")
async def validate_token(request: dict):
    """Validate GitHub token"""
    try:
        from github import Github
        token = request.get("github_token")
        client = Github(token)
        user = client.get_user()
        return {"valid": True, "username": user.login, "scopes": ["repo"]}
    except Exception as e:
        return {"valid": False, "error": str(e)}

def format_review_markdown(results: list, pr_data: dict) -> str:
    """Format as markdown"""
    md = f"""## 🤖 AI Code Review

**PR:** #{pr_data['pr_number']} - {pr_data['title']}
**Author:** @{pr_data['author']}
**Files:** {len(results)}

***

"""
    for r in results:
        counts = r['counts']
        md += f"### 📄 `{r['filename']}`\n\n"
        md += f"**Issues:** 🔴 {counts.get('critical',0)} | 🟠 {counts.get('high',0)} | 🟡 {counts.get('medium',0)} | 🟢 {counts.get('low',0)}\n\n"
        md += f"{r['review']}\n\n---\n\n"
    
    md += "*Powered by CodeRefine AI*"
    return md
