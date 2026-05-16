"""
Development server runner for the downloader page backend
"""

import uvicorn
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    print("=" * 60)
    print("AI CLI Orchestrator - Downloader Page Backend")
    print("=" * 60)
    print("\nStarting development server...")
    print("Frontend: http://127.0.0.1:8000")
    print("API Docs: http://127.0.0.1:8000/api/docs")
    print("\nPress CTRL+C to stop the server\n")
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

# Made with Bob
