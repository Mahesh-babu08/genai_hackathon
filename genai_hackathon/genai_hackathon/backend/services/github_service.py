import os
import time
import jwt
import requests
from github import Github, GithubIntegration, Auth, InputGitTreeElement
from dotenv import load_dotenv
import hashlib
import hmac

load_dotenv()

class GitHubService:
    def __init__(self):
        self.app_id = os.getenv("GITHUB_APP_ID")
        self.private_key_path = os.getenv("GITHUB_PRIVATE_KEY_PATH")
        self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        
        self.integration = None
        if self.app_id and self.private_key_path:
            self._init_integration()

    def _init_integration(self):
        try:
            with open(self.private_key_path, 'r') as f:
                private_key = f.read()
            
            auth = Auth.AppAuth(
                self.app_id,
                private_key,
            )
            self.integration = GithubIntegration(auth=auth)
        except Exception as e:
            print(f"Error initializing GitHub Integration: {e}")

    def get_installation_client(self, installation_id: int) -> Github:
        if not self.integration:
            raise Exception("GitHub App not configured properly")
        
        # Get an access token for the installation
        access_token = self.integration.get_access_token(installation_id).token
        
        # Return authenticated Github client
        return Github(auth=Auth.Token(access_token))

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret:
            print("Warning: GITHUB_WEBHOOK_SECRET not set")
            return False
            
        if not signature:
            return False
            
        sha_name, signature = signature.split('=')
        if sha_name != 'sha256':
            return False
            
        mac = hmac.new(
            self.webhook_secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        return hmac.compare_digest(mac.hexdigest(), signature)

    def get_pr_diff(self, repo_full_name: str, pr_number: int, installation_id: int):
        gh = self.get_installation_client(installation_id)
        repo = gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        
        files_data = []
        for file in pr.get_files():
            # Skip deleted files
            if file.status == "removed":
                continue
                
            content = None
            try:
                # Fetch full content from the head SHA
                content_file = repo.get_contents(file.filename, ref=pr.head.sha)
                content = content_file.decoded_content.decode('utf-8')
            except Exception as e:
                print(f"Error fetching content for {file.filename}: {e}")
                # Fallback to patch if content fetch fails or for large files? 
                # Ideally we want full content for context, but patch is what changed.
                # Let's use full content as requested.
                pass
            
            if content:
                files_data.append({
                    "filename": file.filename,
                    "status": file.status,
                    "patch": file.patch,
                    "content": content,
                    "additions": file.additions,
                    "deletions": file.deletions
                })
                
        return {
            "pr_number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "head_sha": pr.head.sha,
            "files": files_data,
            "author": pr.user.login
        }

    def post_pr_comment(self, repo_full_name: str, pr_number: int, comment: str, installation_id: int):
        gh = self.get_installation_client(installation_id)
        repo = gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(comment)

    def create_commit(self, repo_full_name: str, branch: str, files: dict, message: str, installation_id: int) -> str:
        """
        Creates a commit with multiple file changes.
        files: dict where key is filename and value is new content
        """
        gh = self.get_installation_client(installation_id)
        repo = gh.get_repo(repo_full_name)
        
        # Get latest commit SHA of the branch
        ref = repo.get_git_ref(f"heads/{branch}")
        latest_commit_sha = ref.object.sha
        base_tree = repo.get_git_tree(latest_commit_sha)
        
        element_list = []
        for filename, content in files.items():
            blob = repo.create_git_blob(content, "utf-8")
            element = InputGitTreeElement(path=filename, mode='100644', type='blob', sha=blob.sha)
            element_list.append(element)
            
        # Create new tree
        # Note: PyGithub create_git_tree might need correct usage for 'tree' arg
        # We need to construct InputGitTreeElement objects.
        # However, PyGithub interface for create_git_tree takes a list of InputGitTreeElement
        
        # BUT wait, I need to import InputGitTreeElement from github
        # It's actually: from github import InputGitTreeElement
        
        new_tree = repo.create_git_tree(element_list, base_tree)
        
        parent = repo.get_git_commit(latest_commit_sha)
        new_commit = repo.create_git_commit(message, new_tree, [parent])
        
        # Update branch ref
        ref.edit(new_commit.sha)
        
        return new_commit.sha

# Helper to avoid circular imports / global instance
github_service = GitHubService()
