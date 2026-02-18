import os
import re
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# Models
class ReviewRequest(BaseModel):
    code: str
    language: str
    focus_areas: List[str]

class RewriteRequest(BaseModel):
    code: str
    language: str
    focus_areas: List[str] # Added to pass focus areas if needed for rewrite context

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = None
    context_code: Optional[str] = None
    review_summary: Optional[str] = None

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("../frontend/login.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/app", response_class=HTMLResponse)
async def read_app():
    with open("../frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/review")
async def review_code(request: ReviewRequest):
    try:
        prompt = f"""You are a senior software engineer with 15+ years of experience.
Analyze the following {request.language} code focusing on: {', '.join(request.focus_areas)}.

Provide output in EXACT structure:

🔴 Critical Issues

bullet points

🟠 High Priority

bullet points

🟡 Medium Priority

bullet points

🟢 Low Priority

bullet points

📌 Overall Summary

Short summary paragraph.

Code:

{request.code}
"""
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2000,
            top_p=0.9,
        )
        
        review_text = completion.choices[0].message.content
        parsed_review = parse_review_response(review_text)
        parsed_review["raw_review"] = review_text
        
        return JSONResponse(content=parsed_review)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rewrite")
async def rewrite_code(request: RewriteRequest):
    try:
        prompt = f"""You are an expert software architect.
Rewrite the following {request.language} code to:

- Fix all bugs
- Improve performance
- Remove security vulnerabilities
- Apply best practices
- Add docstrings/comments
- Make it production-ready

Provide:
1. Rewritten code only
2. List of improvements

Code:
{request.code}
"""
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2000,
            top_p=0.9,
        )
        
        response_text = completion.choices[0].message.content
        
        # Simple extraction logic (can be refined)
        # Assuming the model follows instructions, we might need to parse
        # But for now, returning the raw text which the frontend can render is safer 
        # unless we strictly enforce JSON output from LLM, which is harder with just text prompting.
        # Let's try to structure it a bit if possible, or just return as is.
        # The user requirement say "Return { rewritten_code: "", improvements: [] }"
        # We'll try to parse typical markdown code blocks.
        
        code_match = re.search(r"```(?:\w+)?\n(.*?)```", response_text, re.DOTALL)
        rewritten_code = code_match.group(1) if code_match else response_text
        
        # Extract improvements (assuming they are listed after the code or before, usually formatted as list)
        # We can just return the full text for specific sections if strictly parsing is too brittle without JSON mode.
        # However, let's try to provide the requested structure.
        
        return JSONResponse(content={
            "rewritten_code": rewritten_code,
            "improvements": response_text # sending full text for now so frontend can display the list and everything
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
@app.post("/api/chat")
async def chat_assistant(request: ChatRequest):
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="Message is required")

        # --- 1. CONTEXT GATING MECHANISM ---
        # Only include code context if the user actually refers to it.
        # This prevents the model from obsessing over the code when the user asks a general question.
        triggers = ["this code", "above code", "my code", "the bug", "fix this", "why is this"]
        include_context = False
        
        # Check if message contains any trigger phrase (case-insensitive)
        if any(trigger in request.message.lower() for trigger in triggers):
            include_context = True
        
        # Also include context if the message is very short (likely referring to context implicitly like "fix it")
        if len(request.message.split()) < 5:
             include_context = True

        final_context_code = request.context_code if (include_context and request.context_code) else None
        final_review_summary = request.review_summary if (include_context and request.review_summary) else None

        # --- 2. SYSTEM PROMPT ---
        system_prompt = f"""You are an elite AI Coding Copilot comparable to ChatGPT and Gemini.

You must:
- Be precise.
- Answer only what is asked.
- Avoid unnecessary length.
- Strictly follow requested programming language.
- Never switch languages.
- Use context_code only if question refers to it.
- Avoid hallucinating libraries or APIs.
- Provide production-grade answers.
- Adapt explanation depth automatically.
- Use structured but concise formatting.

Language Lock Rule:
You MUST generate code only in the requested programming language: {request.language if request.language else "Unknown"}.
If user did not request code, do NOT generate code.

Precision Rule:
If question is simple -> answer simply (3-5 lines).
If question is advanced -> answer technically.
Do not waste tokens on "Certainly!" or "Here is the code". Just give the answer.

Programming Language: {request.language if request.language else "Not specified"}

Code Context:
{final_context_code if final_context_code else "No code context provided (answer generally)"}

Review Summary:
{final_review_summary if final_review_summary else "N/A"}

User Question:
{request.message}
"""

        # --- 3. STREAMING GENERATION ---
        async def generate_stream():
            stream = client.chat.completions.create(
                messages=[
                    {"role": "user", "content": system_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.15, # Low temp for precision
                max_tokens=1500,
                top_p=0.85,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        from fastapi.responses import StreamingResponse
        return StreamingResponse(generate_stream(), media_type="text/plain")

    except Exception as e:
        print(f"Error: {e}") # Log error
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def parse_review_response(review_text: str):
    """
    Parses the review text into structured sections.
    """
    sections = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": [],
        "summary": ""
    }
    
    # Regex patterns for sections
    critical_pattern = re.search(r"🔴 Critical Issues(.*?)(?=🟠|🟡|🟢|📌|$)", review_text, re.DOTALL)
    high_pattern = re.search(r"🟠 High Priority(.*?)(?=🟡|🟢|📌|$)", review_text, re.DOTALL)
    medium_pattern = re.search(r"🟡 Medium Priority(.*?)(?=🟢|📌|$)", review_text, re.DOTALL)
    low_pattern = re.search(r"🟢 Low Priority(.*?)(?=📌|$)", review_text, re.DOTALL)
    summary_pattern = re.search(r"📌 Overall Summary(.*?)$", review_text, re.DOTALL)

    def extract_bullets(text):
        if not text:
            return []
        # Extract lines starting with hyphens, asterisks, or numbers
        return [line.strip().lstrip("-*•").strip() for line in text.strip().split('\n') if line.strip().startswith(("-", "*", "•"))]

    if critical_pattern:
        sections["critical"] = extract_bullets(critical_pattern.group(1))
    
    if high_pattern:
        sections["high"] = extract_bullets(high_pattern.group(1))

    if medium_pattern:
        sections["medium"] = extract_bullets(medium_pattern.group(1))

    if low_pattern:
        sections["low"] = extract_bullets(low_pattern.group(1))

    if summary_pattern:
        sections["summary"] = summary_pattern.group(1).strip()
        
    return sections

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
