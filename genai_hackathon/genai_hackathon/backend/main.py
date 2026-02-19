from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import logging
import os

# Load environment first
load_dotenv()

# Validate environment before starting
from utils.config_validator import validate_environment
validate_environment()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CodeRefine AI",
    description="AI-Powered Code Review & Rewrite Agent",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from routers import review, rewrite, github_simple, chat, bumble

app.include_router(review.router)
app.include_router(rewrite.router)
app.include_router(github_simple.router)
app.include_router(chat.router)
app.include_router(bumble.router)

# Static files
# Check if frontend directory exists, if so mount it
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
else:
    logger.warning("Frontend directory not found, static files will not be served")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the login page"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'login.html')
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)

@app.get("/app", response_class=HTMLResponse)
async def read_app():
    """Serve the main app page"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'index.html')
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CodeRefine AI",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting CodeRefine AI...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
