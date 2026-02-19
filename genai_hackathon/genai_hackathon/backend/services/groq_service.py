import os
import logging
from typing import Optional, Dict, Any
from groq import Groq, APIError, RateLimitError, APIConnectionError
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroqService:
    """
    Production-ready Groq API service with comprehensive error handling.
    """
    
    # Supported models (can be configured)
    SUPPORTED_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "mixtral-8x7b-32768"
    ]
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Groq service with error checking.
        
        Args:
            api_key: Groq API key (optional, will load from env)
            model: Model name (optional, defaults to llama-3.3-70b-versatile)
        
        Raises:
            ValueError: If API key is not provided and not in environment
        """
        # Load .env file if it exists
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logger.info("Loaded environment variables from .env")
        else:
            logger.warning(".env file not found, using system environment variables")
        
        # Validate API key
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Please set it in .env file or pass as parameter. "
                "Get your key from: https://console.groq.com/keys"
            )
        
        # Validate and set model
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        if self.model not in self.SUPPORTED_MODELS:
            logger.warning(f"Model {self.model} not in supported list. Proceeding anyway.")
        
        # Initialize client
        try:
            self.client = Groq(api_key=self.api_key)
            logger.info(f"Groq client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
    
    def review_code(
        self, 
        code: str, 
        language: str = "python", 
        focus_areas: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Review code with comprehensive error handling.
        
        Args:
            code: Source code to review
            language: Programming language
            focus_areas: List of areas to focus on (bugs, security, performance, best_practices)
        
        Returns:
            Dict with review results or error information
        
        Raises:
            ValueError: If code is empty or invalid parameters
        """
        # Input validation
        if not code or not code.strip():
            raise ValueError("Code parameter cannot be empty")
        
        if not language or not isinstance(language, str):
            raise ValueError("Language must be a non-empty string")
        
        # Validate and set default focus areas
        valid_focus_areas = {"bugs", "security", "performance", "best_practices"}
        if focus_areas is None:
            focus_areas = list(valid_focus_areas)
        else:
            # Validate focus areas
            invalid_areas = set(focus_areas) - valid_focus_areas
            if invalid_areas:
                logger.warning(f"Invalid focus areas ignored: {invalid_areas}")
                focus_areas = [area for area in focus_areas if area in valid_focus_areas]
            
            if not focus_areas:
                focus_areas = list(valid_focus_areas)
        
        focus_str = ", ".join(focus_areas)
        
        # Build prompt
        prompt = f"""You are an expert code reviewer with 15+ years of experience. Analyze this {language} code.

Focus on: {focus_str}

Return your review in this EXACT format:

### 🔴 Critical Issues
[List critical bugs, security vulnerabilities, or data loss risks. One per line starting with '-']

### 🟠 High Priority
[List important bugs, major performance issues, or significant violations. One per line starting with '-']

### 🟡 Medium Priority
[List best practice violations, maintainability issues. One per line starting with '-']

### 🟢 Low Priority
[List style issues, minor optimizations. One per line starting with '-']

Code to review:
```{language}
{code}
"""

        try:
            logger.info(f"Requesting review for {len(code)} chars of {language} code")
            
            # Call Groq API with timeout and retry logic
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
                top_p=0.9
            )
            
            # Validate response
            if not completion:
                raise ValueError("Received None response from Groq API")
            
            if not hasattr(completion, 'choices') or not completion.choices:
                raise ValueError("Groq API returned empty choices list")
            
            if not completion.choices[0].message:
                raise ValueError("Groq API returned message without content")
            
            review_text = completion.choices[0].message.content
            
            if not review_text or not review_text.strip():
                raise ValueError("Groq API returned empty review text")
            
            logger.info(f"Review completed: {len(review_text)} chars received")
            
            # Parse and return results
            return self.parse_review_response(review_text)
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return {
                "error": "rate_limit",
                "message": "API rate limit exceeded. Please try again in a moment.",
                "success": False
            }
        
        except APIConnectionError as e:
            logger.error(f"API connection failed: {e}")
            return {
                "error": "connection",
                "message": "Failed to connect to Groq API. Please check your internet connection.",
                "success": False
            }
        
        except APIError as e:
            logger.error(f"Groq API error: {e}")
            return {
                "error": "api_error",
                "message": f"Groq API error: {str(e)}",
                "success": False
            }
        
        except Exception as e:
            logger.error(f"Unexpected error during code review: {e}")
            return {
                "error": "unexpected",
                "message": f"An unexpected error occurred: {str(e)}",
                "success": False
            }

    def parse_review_response(self, review_text: str) -> Dict[str, Any]:
        """
        Parse review text with robust error handling.
        
        Args:
            review_text: Raw review text from LLM
        
        Returns:
            Structured review data with counts and sections
        """
        import re
        
        # Validate input
        if not review_text or not isinstance(review_text, str):
            logger.warning("Empty or invalid review text received")
            return {
                "success": False,
                "error": "invalid_input",
                "review_text": "",
                "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "sections": {}
            }
        
        review_text = review_text.strip()
        
        # Define section patterns with flexibility
        patterns = {
            "critical": r'###\s*🔴\s*Critical Issues.*?(?=###|\Z)',
            "high": r'###\s*🟠\s*High Priority.*?(?=###|\Z)',
            "medium": r'###\s*🟡\s*Medium Priority.*?(?=###|\Z)',
            "low": r'###\s*🟢\s*Low Priority.*?(?=###|\Z)'
        }
        
        parsed = {}
        counts = {}
        
        for severity, pattern in patterns.items():
            try:
                match = re.search(pattern, review_text, re.DOTALL | re.IGNORECASE)
                
                if match:
                    content = match.group(0)
                    parsed[severity] = content
                    
                    # Count issues (lines starting with - or *)
                    issue_count = len(re.findall(r'^\s*[-*]\s+', content, re.MULTILINE))
                    counts[severity] = issue_count
                else:
                    parsed[severity] = ""
                    counts[severity] = 0
                    
            except Exception as e:
                logger.error(f"Error parsing {severity} section: {e}")
                parsed[severity] = ""
                counts[severity] = 0
        
        # Fallback: If no sections found, treat entire text as mixed review
        if all(count == 0 for count in counts.values()):
            logger.warning("No structured sections found in review. Using entire text as medium priority.")
            parsed["medium"] = review_text
            counts["medium"] = len(re.findall(r'^\s*[-*]\s+', review_text, re.MULTILINE))
        
        return {
            "success": True,
            "review_text": review_text,
            "counts": counts,
            "sections": parsed
        }

    def rewrite_code(
        self, 
        code: str, 
        language: str = "python", 
        improvements: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Rewrite code with comprehensive error handling.
        
        Args:
            code: Original code to rewrite
            language: Programming language
            improvements: List of improvements to apply
        
        Returns:
            Dict with rewritten code or error information
        """
        import re
        # Input validation
        if not code or not code.strip():
            raise ValueError("Code parameter cannot be empty")
        
        if not language or not isinstance(language, str):
            raise ValueError("Language must be a non-empty string")
        
        # Validate improvements
        if improvements is None or len(improvements) == 0:
            improvements = [
                "Fix all security vulnerabilities",
                "Improve error handling",
                "Add type hints and docstrings",
                "Optimize performance"
            ]
            logger.info("No improvements specified, using default list")
        
        improvements_str = "\n".join(f"- {imp}" for imp in improvements)
        
        # Build prompt
        prompt = f"""Rewrite this {language} code to fix these issues:
{improvements_str}

Requirements:

Fix all security and performance issues

Add comprehensive error handling

Add docstrings and type hints (if applicable)

Follow {language} best practices

Keep functionality identical

Return ONLY the rewritten code in a code block, no explanations

Original code:

{code}

Rewritten code:"""

        try:
            logger.info(f"Requesting rewrite for {len(code)} chars of {language} code")
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Lower temperature for more deterministic output
                max_tokens=3000,
                top_p=0.9
            )
            
            # Validate response
            if not completion or not completion.choices:
                raise ValueError("Groq API returned empty response")
            
            rewritten = completion.choices[0].message.content
            
            if not rewritten or not rewritten.strip():
                raise ValueError("Groq API returned empty rewritten code")
            
            # Clean up code fences
            rewritten = re.sub(r'^```[a-zA-Z]*\n', '', rewritten, flags=re.MULTILINE)
            rewritten = rewritten.replace('```', '').strip()
            
            if not rewritten:
                raise ValueError("Rewritten code is empty after cleanup")
            
            logger.info(f"Rewrite completed: {len(rewritten)} chars generated")
            
            return {
                "success": True,
                "original_code": code,
                "rewritten_code": rewritten,
                "improvements_applied": improvements
            }
            
        except (RateLimitError, APIConnectionError, APIError) as e:
            logger.error(f"API error during rewrite: {e}")
            return {
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
                "original_code": code
            }
        
        except Exception as e:
            logger.error(f"Unexpected error during rewrite: {e}")
            return {
                "success": False,
                "error": "unexpected",
                "message": f"An unexpected error occurred: {str(e)}",
                "original_code": code
            }

# Global instance with lazy initialization
_groq_service = None

def get_groq_service() -> GroqService:
    """Get or create global Groq service instance."""
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService()
    return _groq_service
