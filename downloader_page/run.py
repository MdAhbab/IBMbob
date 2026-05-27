import os
import subprocess
import sys

def main():
    print("============================================")
    print(" AI CLI Orchestrator - Installer & Dev Runner")
    print("============================================")
    
    # Define root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("\n[1/3] Checking environment elements...")
    env_file = os.path.join(root_dir, ".env")
    env_example = os.path.join(root_dir, ".env.example")
    if not os.path.exists(env_file) and os.path.exists(env_example):
        print("Creating .env from .env.example...")
        import shutil
        shutil.copy2(env_example, env_file)
    else:
        print(".env already exists or .env.example not found.")
    
    print("\n[2/3] Installing frontend dependencies (npm install)...")
    try:
        subprocess.run(["npm", "install"], cwd=root_dir, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nError installing frontend dependencies: {e}")
        sys.exit(1)
        
    print("\n[3/3] Starting Frontend Dev Server (npm run dev)...")
    try:
        subprocess.run(["npm", "run", "dev"], cwd=root_dir, shell=True, check=True)
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
