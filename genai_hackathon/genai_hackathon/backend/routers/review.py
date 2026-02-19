from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Dict
import logging

from services.groq_service import get_groq_service
from services.code_scorer import code_scorer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["review"])

class CodeReviewRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to review")
    language: str = Field(default="python", description="Programming language")
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="Focus areas: bugs, security, performance, best_practices"
    )
    calculate_score: bool = Field(default=True, description="Calculate quality scores")
    
    @validator('code')
    def validate_code(cls, v):
        if not v or not v.strip():
            raise ValueError('Code cannot be empty')
        if len(v) > 50000:  # Reasonable limit
            raise ValueError('Code too large (max 50,000 characters)')
        return v.strip()
    
    @validator('language')
    def validate_language(cls, v):
        supported = {'python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'go', 'rust'}
        if v.lower() not in supported:
            logger.warning(f"Unsupported language: {v}")
        return v.lower()
    
    @validator('focus_areas')
    def validate_focus_areas(cls, v):
        if v is None:
            return None
        valid = {'bugs', 'security', 'performance', 'best_practices'}
        invalid = [area for area in v if area not in valid]
        if invalid:
            logger.warning(f"Invalid focus areas removed: {invalid}")
            return [area for area in v if area in valid]
        return v

@router.post("/review")
async def review_code(request: CodeReviewRequest):
    """
    Review code and return structured feedback with quality scores.
    """
    try:
        groq_service = get_groq_service()
        
        result = groq_service.review_code(
            code=request.code,
            language=request.language,
            focus_areas=request.focus_areas
        )
        

        
        if not result.get("success", False):
            error_detail = {
                "error": result.get("error", "unknown"),
                "message": result.get("message", "Review failed"),
                "user_message": "Failed to complete code review. Please try again."
            }
            logger.error(f"Review failed with error: {error_detail}")
            # Return user-friendly error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail
            )
            
        # Calculate scores if requested
        quality_scores = None
        if request.calculate_score:
            quality_scores = code_scorer.calculate_scores(
                result, 
                request.code, 
                request.language
            )
        
        return {
            "success": True,
            "review": result["review_text"],
            "counts": result["counts"],
            "sections": result["sections"],
            "quality_scores": quality_scores
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        import traceback
        logger.error(f"Unexpected error in review endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please contact support."
        )
