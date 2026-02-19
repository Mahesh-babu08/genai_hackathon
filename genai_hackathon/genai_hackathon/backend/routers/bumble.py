from fastapi import APIRouter, HTTPException
from services.bumble_service import bumble_service

router = APIRouter(prefix="/api/bumble", tags=["bumble"])

@router.post("/launch")
async def launch_bumble():
    """Launch Bumble AI Assistant"""
    result = bumble_service.launch()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result
