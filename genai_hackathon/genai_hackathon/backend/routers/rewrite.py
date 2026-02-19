from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import logging

from services.groq_service import get_groq_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["rewrite"])

class RewriteRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to rewrite")
    language: str = Field(default="python", description="Programming language")
    improvements: Optional[List[str]] = Field(
        default=None,
        description="List of improvements to apply"
    )
    
    @validator('code')
    def validate_code(cls, v):
        if not v or not v.strip():
            raise ValueError('Code cannot be empty')
        if len(v) > 50000:
            raise ValueError('Code too large (max 50,000 characters)')
        return v.strip()

@router.post("/rewrite")
async def rewrite_code(request: RewriteRequest):
    """
    Rewrite code based on improvements.
    """
    try:
        groq_service = get_groq_service()
        
        result = groq_service.rewrite_code(
            code=request.code,
            language=request.language,
            improvements=request.improvements
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": result.get("error", "unknown"),
                    "message": result.get("message", "Rewrite failed")
                }
            )
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in rewrite endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please contact support."
        )
