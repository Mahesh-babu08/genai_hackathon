import os
import subprocess
import logging
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

class BumbleService:
    """Service to launch Bumble Python application"""
    
    def __init__(self):
        self.script_path = os.getenv("BUMBLE_SCRIPT_PATH", "C:/gya/Bumble/Bee/run.py")
        self.working_dir = os.getenv("BUMBLE_WORKING_DIR", "C:/gya/Bumble/Bee")
        self.python_path = os.getenv("PYTHON_PATH", "python")
    
    def launch(self):
        """Launch Bumble Python application"""
        
        # Check if script exists
        if not Path(self.script_path).exists():
            return {
                "success": False,
                "message": f"Bumble script not found at: {self.script_path}"
            }
        
        # Check if working directory exists
        if not Path(self.working_dir).exists():
            return {
                "success": False,
                "message": f"Bumble directory not found at: {self.working_dir}"
            }
        
        try:
            logger.info(f"Launching Bumble from: {self.script_path}")
            logger.info(f"Working directory: {self.working_dir}")
            
            # Launch Python script in its own directory
            if platform.system() == "Windows":
                # Windows: Open in new console window
                subprocess.Popen(
                    [self.python_path, "run.py"],
                    cwd=self.working_dir,  # Run from Bumble's directory
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    shell=False
                )
            else:
                # Linux/Mac
                subprocess.Popen(
                    [self.python_path, "run.py"],
                    cwd=self.working_dir
                )
            
            logger.info("✅ Bumble launched successfully")
            
            return {
                "success": True,
                "message": "Bumble launched successfully",
                "script": self.script_path,
                "working_dir": self.working_dir
            }
            
        except FileNotFoundError as e:
            logger.error(f"Python or script not found: {e}")
            return {
                "success": False,
                "message": f"Python not found. Make sure Python is installed and in PATH, or set PYTHON_PATH in .env"
            }
        
        except Exception as e:
            logger.error(f"Failed to launch Bumble: {e}")
            return {
                "success": False,
                "message": f"Failed to launch: {str(e)}"
            }

bumble_service = BumbleService()
