"""
FastAPI Backend for Ollama UI
This server connects the Streamlit frontend to Ollama for LLM inference.
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
EXPECTED_API_KEY = "77d9e9492a0645e197fe948e3d24da4c.tC3UJDhc1Ol_O3wjAZpoj_nP"

@app.get("/api/models")
async def get_models(authorization: str = Header(None)):
    # Validate API Key
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization.split(" ")[1]
    if token != EXPECTED_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    try:
        logger.info("Fetching available models from Ollama...")
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            # Extract model names (e.g., "llama3.2:latest")
            models = [m["name"] for m in data.get("models", [])]
            return {"models": models}
        
        logger.error(f"Ollama tags endpoint returned {response.status_code}")
        return {"models": []}
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return {"models": []}

@app.post("/api/chat")
async def chat(request: Request, authorization: str = Header(None)):
    # 1. Validate API Key
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    if token != EXPECTED_API_KEY:
        logger.warning("Invalid API Key")
        raise HTTPException(status_code=403, detail="Invalid API Key")

    # 2. Parse Request
    data = await request.json()
    user_message = data.get("message")
    model = data.get("model", "llama3.2")
    conversation_id = data.get("conversation_id")
    
    logger.info(f"Received chat request for model: {model}")

    # 3. Prepare Payload for Ollama
    ollama_payload = {
        "model": model,
        "messages": [{"role": "user", "content": user_message}],
        "stream": True
    }

    try:
        # 4. Call Ollama (Streamed)
        logger.info(f"Forwarding request to Ollama: {OLLAMA_API_URL}")
        # Increased timeout to 120s because loading a model into RAM can take time
        response = requests.post(OLLAMA_API_URL, json=ollama_payload, stream=True, timeout=120)
        
        # Check if Ollama rejected the request immediately (e.g. Model not found)
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"Ollama returned error {response.status_code}: {error_text}")
            raise HTTPException(status_code=response.status_code, detail=f"Ollama Error: {error_text}")

        def iter_content():
            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    try:
                        # Parse Ollama's JSON response
                        json_line = json.loads(line)
                        
                        # Check for explicit error in the stream
                        if "error" in json_line:
                            error_msg = json_line["error"]
                            logger.error(f"Ollama stream error: {error_msg}")
                            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                            break

                        content = json_line.get("message", {}).get("content", "")
                        done = json_line.get("done", False)
                        
                        if content:
                            chunk_count += 1
                            chunk = json.dumps({"type": "chunk", "content": content})
                            yield f"data: {chunk}\n\n"
                            
                        if done:
                            logger.info(f"Stream complete. Sent {chunk_count} chunks.")
                            break
                    except ValueError:
                        continue
            
            if chunk_count == 0:
                logger.warning("Ollama returned 200 OK but no content chunks were yielded.")

        return StreamingResponse(iter_content(), media_type="text/event-stream")

    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Ollama")
        raise HTTPException(status_code=503, detail="Ollama is not running. Run 'ollama serve'.")
    except requests.exceptions.ReadTimeout:
        logger.error("Ollama timed out")
        raise HTTPException(status_code=504, detail="Ollama timed out loading the model.")
