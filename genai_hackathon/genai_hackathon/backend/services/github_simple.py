import os
import logging
from typing import Optional, Dict, Any
from github import Github, GithubException
from github.GithubException import UnknownObjectException
import re

logger = logging.getLogger(__name__)

class GitHubSimple:
    """Simple GitHub service using Personal Access Token"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if self.token:
            self.client = Github(self.token)
    
    def parse_pr_url(self, pr_url: str) -> Dict[str, Any]:
        """
        Parse GitHub PR URL.
        Format: https://github.com/owner/repo/pull/123
        """
        pattern = r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
        match = re.match(pattern, pr_url)
        
        if not match:
            raise ValueError(
                f"Invalid PR URL format. Expected: https://github.com/owner/repo/pull/123"
            )
        
        owner, repo, number = match.groups()
        
        return {
            "owner": owner,
            "repo": repo,
            "number": int(number),
            "full_name": f"{owner}/{repo}"
        }
    
    async def fetch_pr_data(
        self, 
        owner: str, 
        repo: str, 
        pr_number: int, 
        token: str
    ) -> Dict[str, Any]:
        """Fetch PR diff and file contents"""
        try:
            client = Github(token)
            user = client.get_user()
            logger.info(f"Authenticated as: {user.login}")
            
            repo_obj = client.get_repo(f"{owner}/{repo}")
            pr = repo_obj.get_pull(pr_number)
            logger.info(f"Fetched PR #{pr_number}: {pr.title}")
            
            files_changed = []
            for file in pr.get_files():
                file_data = {
                    "filename": file.filename,
                    "status": file.status,
                    "patch": file.patch if file.patch else "",
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "content": ""
                }
                
                # Get full content if not deleted
                if file.status != "removed":
                    try:
                        content_file = repo_obj.get_contents(file.filename, ref=pr.head.sha)
                        file_data["content"] = content_file.decoded_content.decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Could not fetch {file.filename}: {e}")
                
                files_changed.append(file_data)
            
            return {
                "pr_number": pr_number,
                "title": pr.title,
                "body": pr.body or "",
                "base_branch": pr.base.ref,
                "head_branch": pr.head.ref,
                "head_sha": pr.head.sha,
                "author": pr.user.login,
                "files_changed": files_changed,
                "url": pr.html_url,
                "state": pr.state
            }
            
        except UnknownObjectException:
            raise ValueError(f"Repository {owner}/{repo} or PR #{pr_number} not found")
        except GithubException as e:
            raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")
    
    async def post_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comment: str,
        token: str
    ) -> Dict[str, Any]:
        """
        Post comment on PR. NO BRANCH ACCESS NEEDED.
        This is an issue comment, not a code review comment.
        """
        try:
            client = Github(token)
            repo_obj = client.get_repo(f"{owner}/{repo}")
            pr = repo_obj.get_pull(pr_number)
            
            # Post as issue comment (works without branch access)
            pr.create_issue_comment(comment)
            logger.info(f"✅ Comment posted to PR #{pr_number}")
            
            return {
                "success": True,
                "message": "Comment posted successfully",
                "pr_url": pr.html_url
            }
            
        except GithubException as e:
            logger.error(f"Failed to post comment: {e.status} - {e.data}")
            
            if e.status == 403:
                return {
                    "success": False,
                    "error": "forbidden",
                    "message": "Token lacks permission. Need 'repo' scope with write access."
                }
            elif e.status == 404:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": f"PR #{pr_number} not found"
                }
            else:
                return {
                    "success": False,
                    "error": f"github_{e.status}",
                    "message": e.data.get('message', str(e))
                }
    
    async def create_commit_with_fixes(
        self,
        owner: str,
        repo: str,
        branch: str,
        files: Dict[str, str],
        message: str,
        token: str
    ) -> Dict[str, Any]:
        """
        Create commit on PR branch. REQUIRES WRITE ACCESS.
        
        Args:
            branch: Branch name WITHOUT 'heads/' prefix (e.g. 'feature-branch')
        """
        try:
            client = Github(token)
            repo_obj = client.get_repo(f"{owner}/{repo}")
            
            logger.info(f"Creating commit on branch: {branch}")
            
            # Get branch reference with correct format
            try:
                ref = repo_obj.get_git_ref(f"heads/{branch}")
            except GithubException as e:
                logger.error(f"Branch not found: {e}")
                return {
                    "success": False,
                    "error": "branch_not_found",
                    "message": f"Branch '{branch}' not found. PR may be merged/closed."
                }
            
            # Get latest commit on branch
            latest_commit_sha = ref.object.sha
            latest_commit = repo_obj.get_git_commit(latest_commit_sha)
            base_tree = latest_commit.tree
            
            # Create blobs for changed files
            tree_elements = []
            for filename, content in files.items():
                blob = repo_obj.create_git_blob(content, "utf-8")
                tree_elements.append({
                    "path": filename,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob.sha
                })
            
            # Create tree
            tree = repo_obj.create_git_tree(tree_elements, base_tree)
            
            # Create commit
            new_commit = repo_obj.create_git_commit(message, tree, [latest_commit])
            
            # Update branch
            ref.edit(new_commit.sha)
            logger.info(f"✅ Commit created: {new_commit.sha}")
            
            return {
                "success": True,
                "commit_sha": new_commit.sha,
                "message": "Commit created successfully"
            }
            
        except GithubException as e:
            logger.error(f"Commit failed: {e.status} - {e.data}")
            
            if e.status == 404:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": "Branch or repository not found"
                }
            elif e.status == 403:
                return {
                    "success": False,
                    "error": "forbidden",
                    "message": "No permission to push. Token needs 'repo' scope."
                }
            else:
                return {
                    "success": False,
                    "error": f"github_{e.status}",
                    "message": e.data.get('message', str(e))
                }
    
    def detect_language(self, filename: str) -> str:
        """Detect language from file extension"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust"
        }
        _, ext = os.path.splitext(filename)
        return ext_map.get(ext.lower(), "python")

github_simple = GitHubSimple()
