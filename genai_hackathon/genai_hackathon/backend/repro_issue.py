import os
import sys
from dotenv import load_dotenv

# Add backend to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from services.groq_service import GroqService
    
    print("Initializing GroqService...")
    service = GroqService()
    print("Service initialized successfully.")
    
    print("Attempting to review code...")
    code = "print('hello world')"
    result = service.review_code(code, "python", ["bugs"])
    
    print("Review result:", result)

    print("Attempting to calculate scores...")
    from services.code_scorer import code_scorer
    scores = code_scorer.calculate_scores(result, code, "python")
    print("Scores:", scores)


except Exception as e:
    print(f"FAILED with error: {e}")
    import traceback
    traceback.print_exc()
