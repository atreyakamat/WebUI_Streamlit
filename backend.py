"""
FastAPI Backend for Ollama UI
This server connects the Streamlit frontend to Ollama for LLM inference.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Ollama Backend API", version="1.0.0")

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_BASE_URL}/api/generate"

# Request model
class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    model: str = "llama3.2"
    temperature: float = 0.7
    max_tokens: int = 2000

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check if backend and Ollama are running."""
    try:
        # Check Ollama connectivity
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        ollama_status = "running" if response.status_code == 200 else "error"
        
        return {
            "status": "healthy",
            "backend": "running",
            "ollama": ollama_status,
            "ollama_url": OLLAMA_BASE_URL
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama connection failed: {e}")
        return {
            "status": "degraded",
            "backend": "running",
            "ollama": "unreachable",
            "error": str(e)
        }

# List available models
@app.get("/models")
async def list_models():
    """Get list of available Ollama models."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            return {"models": models}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch models from Ollama")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching models: {e}")
        raise HTTPException(status_code=503, detail=f"Ollama service unavailable: {str(e)}")

# Main chat endpoint with streaming
@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Stream chat responses from Ollama.
    Uses Server-Sent Events (SSE) for real-time streaming.
    """
    logger.info(f"Chat request - Model: {request.model}, Conversation: {request.conversation_id}")
    
    # Prepare request payload for Ollama
    payload = {
        "model": request.model,
        "prompt": request.message,
        "stream": True,
        "options": {
            "temperature": request.temperature,
            "num_predict": request.max_tokens,
        }
    }
    
    async def generate_stream():
        """Generator function for streaming responses."""
        try:
            # Make streaming request to Ollama
            with requests.post(
                OLLAMA_GENERATE_ENDPOINT,
                json=payload,
                stream=True,
                timeout=120
            ) as response:
                
                if response.status_code != 200:
                    error_msg = f"Ollama API error: {response.status_code}"
                    logger.error(error_msg)
                    yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                    return
                
                # Stream chunks from Ollama
                for line in response.iter_lines():
                    if line:
                        try:
                            # Parse JSON response from Ollama
                            chunk_data = json.loads(line.decode('utf-8'))
                            
                            # Extract the generated text
                            if "response" in chunk_data:
                                text_chunk = chunk_data["response"]
                                
                                # Send chunk to frontend
                                sse_data = {
                                    "type": "chunk",
                                    "content": text_chunk,
                                    "done": chunk_data.get("done", False)
                                }
                                yield f"data: {json.dumps(sse_data)}\n\n"
                                
                                # Break if generation is complete
                                if chunk_data.get("done", False):
                                    logger.info("Stream completed successfully")
                                    break
                                    
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing chunk: {e}")
                            continue
                
        except requests.exceptions.Timeout:
            error_msg = "Request timed out. Please try again."
            logger.error(error_msg)
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
    
    # Return streaming response
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Ollama Backend API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "models": "/models",
            "chat": "/api/chat (POST)"
        },
        "ollama_url": OLLAMA_BASE_URL
    }

# Run the server
if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("Starting Ollama Backend Server")
    logger.info("=" * 60)
    logger.info(f"Backend URL: http://127.0.0.1:8000")
    logger.info(f"Ollama backend running at: {OLLAMA_BASE_URL}")
    logger.info(f"Health check: http://127.0.0.1:8000/health")
    logger.info(f"Available models: http://127.0.0.1:8000/models")
    logger.info("=" * 60)
    
    # Start server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
