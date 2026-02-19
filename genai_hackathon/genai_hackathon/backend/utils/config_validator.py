import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def validate_environment():
    """
    Validate required environment variables on startup.
    Exits with error if critical variables missing.
    """
    required_vars = {
        "GROQ_API_KEY": "Get from https://console.groq.com/keys"
    }
    
    optional_vars = {
        "PATCHED_API_KEY": "Get from https://app.patched.codes",
        "GROQ_MODEL": "Defaults to llama-3.3-70b-versatile"
    }
    
    # Check for .env file
    env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        logger.warning(f".env file not found at {env_path}")
        logger.info("Create .env file with required variables")
    
    # Check required variables
    missing_required = []
    for var, help_text in required_vars.items():
        if not os.getenv(var):
            missing_required.append(f"  - {var}: {help_text}")
    
    if missing_required:
        logger.error("Missing required environment variables:")
        for msg in missing_required:
            logger.error(msg)
        sys.exit(1)
    
    # Check optional variables
    for var, help_text in optional_vars.items():
        if not os.getenv(var):
            logger.info(f"Optional variable {var} not set: {help_text}")
    
    logger.info("✅ Environment variables validated successfully")
