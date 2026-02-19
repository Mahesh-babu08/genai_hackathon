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
    focus_areas: Optional[List[str]] = []

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = None
    context_code: Optional[str] = None
    review_summary: Optional[str] = None

class ScoreRequest(BaseModel):
    code: str
    language: str

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
    print("DEBUG: Entered /api/rewrite")
    try:
        # Validate input
        if not request.code or not request.code.strip():
             raise HTTPException(status_code=400, detail="Code cannot be empty")

        prompt = f"""You are an expert software architect.
Rewrite the following {request.language} code to:

- Fix all bugs
- Improve performance
- Remove security vulnerabilities
- Apply best practices
- Add docstrings/comments
- Make it production-ready

Provide output in this format:
```code
(put the rewritten code here)
```

Improvements:
(list improvements here)

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
        print(f"DEBUG: Rewrite LLM Response length: {len(response_text)}")
        
        # Robust extraction logic
        rewritten_code = response_text
        improvements = "See rewritten code for details."
        
        # Try to extract code block
        code_match = re.search(r"```(?:(\w+)\n)?(.*?)```", response_text, re.DOTALL)
        if code_match:
             # If there are two groups (lang, code) or just code. 
             # The regex `(?:(\w+)\n)?` captures optional language identifier.
             # `(.*?)` captures the code.
             # behavior depends on if lang identifier is present.
             # re.search returns groups.
             # If `(?:...)` is non-capturing group for the outer part? No, `(\w+)` is capturing inside.
             # Let's use a simpler regex to be safe and consistent with previous working regex but improved.
             pass

        # Better Regex
        code_pattern = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
        matches = code_pattern.findall(response_text)
        
        if matches:
            # Assume the largest block is the code, or the first one.
            # Usually the first one is the implementation.
            rewritten_code = matches[0]
            
            # Remove the code block from text to find improvements
            improvements_text = code_pattern.sub("", response_text).strip()
            if improvements_text:
                improvements = improvements_text
        
        return JSONResponse(content={
            "rewritten_code": rewritten_code.strip(),
            "improvements": improvements.strip()
        })

    except Exception as e:
        import traceback
        import sys
        print(f"DEBUG: Exception in /api/rewrite: {repr(e)}")
        traceback.print_exc()
        
        error_msg = str(e)
        if "rate_limit_exceeded" in error_msg.lower():
             return JSONResponse(status_code=429, content={"detail": "AI Service Rate Limit Exceeded. Please try again later."})
        
        return JSONResponse(status_code=500, content={"detail": f"Internal Server Error: {error_msg}"})

@app.post("/api/score")
async def evaluate_score(request: ScoreRequest):
    print("DEBUG: Entered /api/score")
    try:
        # Input Validation
        if not request.code or not request.code.strip():
             raise HTTPException(status_code=400, detail="Code cannot be empty")

        system_prompt = f"""You are a strict senior software engineer and technical interviewer.

Your job is to critically evaluate the following {request.language} code.

IMPORTANT RULES:
1. NEVER give 100% unless the code is PERFECT.
2. If there is ANY syntax error → deduct heavily.
3. If there is ANY logical error → deduct heavily.
4. If edge cases are not handled → deduct marks.
5. If code is incomplete → score below 50%.
6. If code would fail compilation or execution → score below 40%.
7. Do NOT be polite. Be honest and strict.
8. Be extremely critical like a real technical interviewer.

Evaluate based on:
- Syntax correctness (30%)
- Logic correctness (30%)
- Edge case handling (20%)
- Code quality & readability (10%)
- Efficiency (10%)

Return output as a single valid JSON object. Do not wrap in markdown code blocks. Do not add explanations outside the JSON.
{{
"performance_score": number, // Score 0-100 based on Efficiency
"security_score": number, // Score 0-100 based on Logic and Correctness
"readability_score": number, // Score 0-100 based on Readability
"maintainability_score": number, // Score 0-100 based on Code Quality/Syntax
"overall_score": number, // The calculated Final Score (0-100)
"time_complexity": "string",
"space_complexity": "string",
"reasoning_summary": "string" // MUST contain the detailed text report below
}}

For `reasoning_summary`, provide a string formatted exactly like this (use \\n for newlines):

FINAL SCORE: X/100

DETAILED BREAKDOWN:
Syntax: X/30
Logic: X/30
Edge Cases: X/20
Readability: X/10
Efficiency: X/10

REASONS FOR DEDUCTIONS:
- [point 1]
- [point 2]
...

Programming Language:
{request.language}

Code:
{request.code}
"""
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": system_prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=1000,
            top_p=0.85,
        )
        
        response_text = completion.choices[0].message.content
        print(f"DEBUG: Score LLM Response: {response_text}")
        
        score_data = None
        import json
        try:
            score_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Robust JSON extraction
            try:
                # Find start and end of JSON object
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx : end_idx + 1]
                    score_data = json.loads(json_str)
            except Exception:
                pass
        
        if not score_data:
             print(f"DEBUG: Failed to parse JSON. Raw: {response_text}")
             raise ValueError("Failed to parse JSON response from LLM")
        
        if not score_data:
             raise ValueError("Failed to parse JSON response from LLM")
             
        # Normalize fields if needed (LLM sometimes misses keys)
        required_keys = ["performance_score", "security_score", "readability_score", "maintainability_score", 
                         "overall_score", "time_complexity", "space_complexity", "reasoning_summary"]
        
        for key in required_keys:
            if key not in score_data:
                score_data[key] = "N/A" if "complexity" in key or "summary" in key else 0
        
        return JSONResponse(content=score_data)

    except Exception as e:
        import traceback
        import sys
        print(f"DEBUG: Exception in /api/score: {repr(e)}")
        traceback.print_exc()
        
        error_msg = str(e)
        if "rate_limit_exceeded" in error_msg.lower():
            return JSONResponse(status_code=429, content={"detail": "AI Service Rate Limit Exceeded. Please try again later."})
        
        return JSONResponse(status_code=500, content={"detail": f"Internal Server Error: {error_msg}"})

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
