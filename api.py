from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import requests
import time

app = FastAPI()

# Configuration for Ollama
OLLAMA_BASE_URL = "http://localhost:11434"

class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    model: str

@app.get("/")
def read_root():
    return {"status": "ok", "message": "FastAPI backend is running. Connects to Ollama at " + OLLAMA_BASE_URL}

@app.get("/api/models")
def get_models():
    """Fetch models from Ollama or return default list if Ollama is down."""
    try:
        # Try to get models from Ollama
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            # Extract model names
            model_names = [m["name"] for m in models_data]
            return {"models": model_names}
    except requests.exceptions.ConnectionError:
        print("Ollama not detected. Using fallback models.")
    
    # Fallback if Ollama is not running
    return {"models": ["llama3.2", "mistral", "codellama", "Mock Mode (Demo)"]}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    """Forward chat request to Ollama."""
    
    # 1. Handle Mock Mode
    if request.model == "Mock Mode (Demo)":
        time.sleep(1)
        return {"content": f"This is a mock response. I received: '{request.message}'"}

    # 2. Forward to Ollama
    try:
        # Construct payload for Ollama
        # Note: For a full chat history, the frontend should send the whole context.
        # Here we send just the latest message for simplicity.
        ollama_payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.message}],
            "stream": False
        }
        
        response = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=ollama_payload, timeout=60)
        
        if response.status_code == 200:
            response_json = response.json()
            # Ollama returns 'message': {'role': 'assistant', 'content': '...'}
            ai_content = response_json.get("message", {}).get("content", "")
            return {"content": ai_content}
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Ollama Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Could not connect to Ollama (localhost:11434). Is it running?")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
