# Backend Setup & Usage Guide

## Architecture Overview

The project now consists of two components:

1. **Frontend** (`app.py`): Streamlit UI that displays chat interface
2. **Backend** (`backend/main.py`): FastAPI server with Ollama integration and SQLite database

```
WebUI_Streamlit/
├── app.py                    # Streamlit frontend
├── requirements.txt          # Frontend dependencies
├── backend/
│   ├── main.py              # FastAPI backend with Ollama
│   ├── requirements.txt     # Backend dependencies
│   └── chatbot.db           # SQLite database (auto-created)
└── BUILD_DOC.md             # Project documentation
```

---

## Backend Features

- **Ollama Integration**: Streams responses from your local Ollama instance
- **SQLite Database**: Persists all conversations and messages
- **RESTful API**: Clean endpoints for chat, conversation management
- **Server-Sent Events (SSE)**: Real-time streaming responses
- **CORS Enabled**: Works seamlessly with Streamlit frontend

### Database Schema

**Conversations Table:**
- `id`: Unique conversation identifier
- `title`: Auto-generated from first user message
- `created`: Timestamp of creation
- `updated`: Last activity timestamp

**Messages Table:**
- `id`: Unique message identifier
- `conversation_id`: Foreign key to conversation
- `role`: Either 'user' or 'assistant'
- `content`: Message text
- `timestamp`: When the message was created

---

## Prerequisites

1. **Ollama installed and running**
   - Download from: https://ollama.ai
   - Verify it's running: `ollama --version`
   - Pull a model (e.g., `ollama pull llama3.2`)

2. **Python 3.9+**

---

## Installation & Setup

### Step 1: Install Backend Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### Step 2: Install/Update Frontend Dependencies

```powershell
cd ..
pip install -r requirements.txt
```

### Step 3: Verify Ollama is Running

```powershell
# Check if Ollama is responding
curl http://localhost:11434/api/version
```

If you get a connection error, start Ollama:
```powershell
ollama serve
```

### Step 4: Start the Backend Server

In one terminal:
```powershell
cd backend
python main.py
```

The backend will start on `http://localhost:8000`. You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Start the Streamlit Frontend

In a second terminal:
```powershell
python -m streamlit run app.py
```

The frontend will open at `http://localhost:8501`.

---

## API Endpoints

### Health Check
```http
GET /health
```

### Chat (Streaming)
```http
POST /api/chat
Content-Type: application/json

{
  "message": "Your prompt here",
  "conversation_id": "optional-uuid",
  "model": "llama3.2"
}
```

Returns Server-Sent Events with streaming response.

### Get All Conversations
```http
GET /api/conversations
```

### Get Conversation Messages
```http
GET /api/conversations/{conversation_id}/messages
```

### Delete Conversation
```http
DELETE /api/conversations/{conversation_id}
```

### Update Conversation Title
```http
POST /api/conversations/{conversation_id}/title?title=New+Title
```

---

## How It Works

1. **User types a message** in Streamlit UI
2. **Frontend sends HTTP POST** to `http://localhost:8000/api/chat`
3. **Backend:**
   - Saves user message to SQLite
   - Builds conversation context from message history
   - Sends prompt to Ollama via HTTP streaming
   - Streams chunks back to frontend as SSE
   - Saves assistant response to database
4. **Frontend receives stream**, displays typing animation, and updates UI

---

## Configuration

### Change Ollama Model

Edit `backend/main.py` or pass `model` parameter in requests:

```python
# Default model (line 54)
model: str = "llama3.2"
```

Available models (after pulling):
- `llama3.2` (3B, fast)
- `llama3.1` (8B, balanced)
- `mistral` (7B)
- `codellama` (for code)

Pull a model:
```powershell
ollama pull mistral
```

### Change Backend Port

In `backend/main.py`, last line:
```python
uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

If you change the port, update `app.py`:
```python
"http://localhost:8000/api/chat"  # Change to your port
```

---

## Troubleshooting

### "Connection refused" Error

**Problem**: Frontend can't reach backend.

**Solution**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check for port conflicts: `netstat -ano | findstr :8000`
3. Restart backend server

### "Ollama not responding"

**Problem**: Backend can't reach Ollama.

**Solution**:
1. Check Ollama is running: `ollama list`
2. Verify API endpoint: `curl http://localhost:11434/api/version`
3. Restart Ollama: `ollama serve`

### Database Locked

**Problem**: SQLite database locked error.

**Solution**:
1. Stop all backend processes
2. Delete `backend/chatbot.db`
3. Restart backend (database recreates automatically)

### Slow Responses

**Problem**: Ollama takes too long to respond.

**Solution**:
1. Use a smaller model: `ollama pull llama3.2` (3B is faster)
2. Check system resources (RAM, CPU)
3. Reduce conversation history context (edit `backend/main.py`)

---

## Database Management

### View Database Contents

```powershell
# Install DB Browser for SQLite or use sqlite3 CLI
sqlite3 backend/chatbot.db

# List conversations
SELECT * FROM conversations;

# List messages
SELECT * FROM messages;
```

### Reset Database

```powershell
rm backend/chatbot.db
# Backend will recreate on next startup
```

---

## Production Considerations

For deployment:

1. **Change CORS settings** in `backend/main.py`:
   ```python
   allow_origins=["https://your-streamlit-app.com"]
   ```

2. **Use environment variables** for configuration:
   ```python
   import os
   OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
   ```

3. **Use PostgreSQL** instead of SQLite for better concurrency

4. **Add authentication** to backend endpoints

5. **Deploy backend separately** (e.g., Railway, Render, AWS)

6. **Use HTTPS** for production traffic

---

## Development Tips

### Auto-reload Backend

Backend uses `reload=True` by default, so code changes auto-restart the server.

### Debug Mode

Add logging to `backend/main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test API Directly

```powershell
# Test chat endpoint
curl -X POST http://localhost:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{"message":"Hello", "model":"llama3.2"}'
```

---

## Next Steps

1. Add user authentication
2. Implement conversation sharing
3. Add model selection UI in Streamlit
4. Support for image/file uploads
5. Add conversation export (JSON/PDF)
6. Implement RAG (Retrieval-Augmented Generation) with vector DB

---

## Performance Tips

- **Context window management**: Limit conversation history sent to Ollama (currently sends all)
- **Response caching**: Cache common queries
- **Connection pooling**: Reuse HTTP connections to Ollama
- **Async processing**: Already implemented with `httpx.AsyncClient`

---

For more details, see `BUILD_DOC.md`.
