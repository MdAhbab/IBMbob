#!/usr/bin/env python3
"""
Cross-platform script to start the frontend development server.
Replaces the Windows-specific start.bat file.
"""

import subprocess
import sys
import os

def main():
    print("============================================")
    print(" AI CLI Orchestrator - Frontend Dev Server")
    print("============================================")
    print("\nStarting Frontend (Vite)...")
    print("Press Ctrl+C to stop the server\n")
    
    # Check if npm is installed
    try:
        # Run npm run dev
        # Use shell=True on Windows for npm to be resolved properly
        is_windows = os.name == 'nt'
        subprocess.run(["npm", "run", "dev"], shell=is_windows, check=True)
    except KeyboardInterrupt:
        print("\n\nServer stopped gracefully.")
    except subprocess.CalledProcessError as e:
        print(f"\nError starting the server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
