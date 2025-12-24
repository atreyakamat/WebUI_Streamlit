import subprocess
import sys
import time
import os

def run_project():
    print("🚀 Starting WebUI Streamlit Project...")
    
    # 0. Start Ollama (LLM Service)
    print("Starting Ollama Service...")
    try:
        # Attempt to start ollama serve. If it's already running as a service, this might fail or just log.
        # We use shell=True for better compatibility with command line tools in some environments
        ollama = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10) # Increased wait time for Ollama to be ready
    except FileNotFoundError:
        print("⚠️  Warning: 'ollama' command not found. Please ensure Ollama is installed and running.")
        ollama = None

    # 1. Start Backend (api.py)
    print("Starting Backend (api.py)...")
    # Using Popen to run in parallel
    backend = subprocess.Popen([sys.executable, "api.py"])
    
    # Give backend a moment to initialize
    time.sleep(2)
    
    # 2. Start Frontend (app_unified.py)
    print("Starting Frontend (app_unified.py)...")
    print("   - Features: Chat Context, OCR Extract, Summarise")
    # Using 'streamlit run' command
    frontend = subprocess.Popen(["streamlit", "run", "app_unified.py"])
    
    print("\n✅ Project is running!")
    print("Backend: http://127.0.0.1:8000")
    print("Frontend: http://localhost:8501")
    print("Press Ctrl+C to stop.")

    try:
        backend.wait()
        frontend.wait()
        if ollama: ollama.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        backend.terminate()
        frontend.terminate()
        if ollama: ollama.terminate()
        print("Services stopped.")

if __name__ == "__main__":
    run_project()
