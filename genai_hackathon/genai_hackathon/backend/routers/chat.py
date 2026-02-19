from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import logging
from groq import Groq
import os

from services.groq_service import get_groq_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = None
    context_code: Optional[str] = None
    review_summary: Optional[str] = None

@router.post("/chat")
async def chat_assistant(request: ChatRequest):
    try:
        # utilize the service client if possible, but the service doesn't have a generic chat method exposed yet.
        # We can use the service client directly
        groq_service = get_groq_service()
        client = groq_service.client
        model = groq_service.model
        
        system_prompt = f"""You are an expert AI Programming Assistant with 15+ years of experience in software engineering.

Your job:
- Explain bugs clearly
- Explain security issues
- Explain performance problems
- Explain best practices
- Explain rewritten code
- Answer programming doubts
- Provide simple beginner-friendly explanations
- Give examples if needed

If context_code is provided, use it to explain.
If review_summary is provided, explain the detected issues clearly.

Always:
- Be clear
- Be structured
- Be concise but informative
- Use bullet points when needed
- Give example fixes when explaining

User Question:
{request.message}

Programming Language:
{request.language if request.language else "Not specified"}

Code Context:
{request.context_code if request.context_code else "No code context provided"}

Review Summary:
{request.review_summary if request.review_summary else "No review summary provided"}
"""
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": system_prompt,
                }
            ],
            model=model,
            temperature=0.4,
            max_tokens=1500,
            top_p=0.9,
        )
        
        reply = completion.choices[0].message.content
        
        return {"reply": reply}

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
