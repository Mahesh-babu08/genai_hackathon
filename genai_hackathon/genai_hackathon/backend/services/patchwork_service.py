import os
from typing import List, Optional
from groq import Groq
from dotenv import load_dotenv
import re

load_dotenv()

class PatchworkService:
    def __init__(self):
        self.client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )
        self.model = "llama-3.3-70b-versatile"

    def review_code(self, code: str, language: str, focus_areas: List[str] = None) -> dict:
        if focus_areas is None:
            focus_areas = ["Bugs", "Security", "Performance", "Best Practices"]
            
        prompt = f"""You are a senior software engineer with 15+ years of experience.
Analyze the following {language} code focusing on: {', '.join(focus_areas)}.

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

{code}
"""
        try:
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
                max_tokens=2000,
                top_p=0.9,
            )
            review_text = completion.choices[0].message.content
            parsed = self._parse_review_response(review_text)
            parsed["raw_review"] = review_text
            return parsed
        except Exception as e:
            print(f"Error in review_code: {e}")
            return {"error": str(e)}

    def rewrite_code(self, code: str, language: str) -> dict:
        prompt = f"""You are an expert software architect.
Rewrite the following {language} code to:

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
{code}
"""
        try:
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
                max_tokens=2000,
                top_p=0.9,
            )
            response_text = completion.choices[0].message.content
            
            # Extract code block
            code_match = re.search(r"```(?:\w+)?\n(.*?)```", response_text, re.DOTALL)
            rewritten_code = code_match.group(1) if code_match else response_text
            
            return {
                "rewritten_code": rewritten_code,
                "improvements": response_text
            }
        except Exception as e:
            print(f"Error in rewrite_code: {e}")
            return {"error": str(e)}

    def _parse_review_response(self, review_text: str):
        sections = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "summary": ""
        }
        
        critical_pattern = re.search(r"🔴 Critical Issues(.*?)(?=🟠|🟡|🟢|📌|$)", review_text, re.DOTALL)
        high_pattern = re.search(r"🟠 High Priority(.*?)(?=🟡|🟢|📌|$)", review_text, re.DOTALL)
        medium_pattern = re.search(r"🟡 Medium Priority(.*?)(?=🟢|📌|$)", review_text, re.DOTALL)
        low_pattern = re.search(r"🟢 Low Priority(.*?)(?=📌|$)", review_text, re.DOTALL)
        summary_pattern = re.search(r"📌 Overall Summary(.*?)$", review_text, re.DOTALL)

        def extract_bullets(text):
            if not text: return []
            return [line.strip().lstrip("-*•").strip() for line in text.strip().split('\n') if line.strip().startswith(("-", "*", "•"))]

        if critical_pattern: sections["critical"] = extract_bullets(critical_pattern.group(1))
        if high_pattern: sections["high"] = extract_bullets(high_pattern.group(1))
        if medium_pattern: sections["medium"] = extract_bullets(medium_pattern.group(1))
        if low_pattern: sections["low"] = extract_bullets(low_pattern.group(1))
        if summary_pattern: sections["summary"] = summary_pattern.group(1).strip()
            
        return sections

patchwork_service = PatchworkService()
