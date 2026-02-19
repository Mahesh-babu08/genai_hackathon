from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from services.github_service import github_service
from services.patchwork_github import patchwork_github
import json

router = APIRouter(prefix="/api/github", tags=["github"])

@router.post("/webhook")
async def github_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None)
):
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing signature header")
        
    payload_body = await request.body()
    if not github_service.verify_webhook_signature(payload_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    try:
        payload = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    if x_github_event == "pull_request":
        action = payload.get("action")
        pr = payload.get("pull_request")
        installation = payload.get("installation")
        
        if action in ["opened", "reopened", "synchronize"] and pr and installation:
            # Auto review on open? Or wait for command?
            # User request said: "Get automatic code reviews on PRs"
            # It implies auto run.
            
            # Check for command in body if we want to support commands in PR body
            should_review = action == "opened" or "/patchwork review" in (pr.get("body") or "")
            should_autofix = "/patchwork autofix" in (pr.get("body") or "")
            
            if should_review:
                background_tasks.add_task(
                    patchwork_github.review_pr,
                    payload["repository"]["full_name"],
                    pr["number"],
                    installation["id"]
                )
            
            if should_autofix:
                background_tasks.add_task(
                    patchwork_github.autofix_pr,
                    payload["repository"]["full_name"],
                    pr["number"],
                    installation["id"]
                )
                
            return {"status": "processing", "action": action}
            
    elif x_github_event == "issue_comment":
        action = payload.get("action")
        issue = payload.get("issue")
        comment = payload.get("comment")
        installation = payload.get("installation")
        
        if action == "created" and issue and "pull_request" in issue and comment:
            body = comment.get("body", "")
            pr_number = issue["number"] # For PRs, issue number is PR number
            
            if "/patchwork review" in body:
                background_tasks.add_task(
                    patchwork_github.review_pr,
                    payload["repository"]["full_name"],
                    pr_number,
                    installation["id"]
                )
                return {"status": "reviewing"}
                
            if "/patchwork autofix" in body:
                background_tasks.add_task(
                    patchwork_github.autofix_pr,
                    payload["repository"]["full_name"],
                    pr_number,
                    installation["id"]
                )
                return {"status": "autofixing"}

    return {"status": "ignored"}

@router.get("/installations")
async def get_installations():
    # This endpoint is for the frontend to check status
    # In a real app we'd filter by user, but here we just return all for the app
    try:
        # We need a way to list installations.
        # GithubIntegration has get_installations()
        if not github_service.integration:
             return {"installations": []}
             
        installations = github_service.integration.get_installations()
        # Convert PaginatedList to list of dicts
        result = []
        for inst in installations:
            result.append({
                "id": inst.id,
                "account": inst.account.login,
                "type": inst.account.type,
                "repository_selection": inst.repository_selection
            })
        return {"installations": result}
    except Exception as e:
        print(f"Error fetching installations: {e}")
        return {"installations": [], "error": str(e)}
