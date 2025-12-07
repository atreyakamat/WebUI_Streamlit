"""FastAPI backend with Ollama integration and SQLite persistence."""
from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import httpx

# Database setup
DATABASE_URL = "sqlite:///./chatbot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database models
class ConversationDB(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New chat")
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("MessageDB", back_populates="conversation", cascade="all, delete-orphan")


class MessageDB(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("ConversationDB", back_populates="messages")


# Pydantic models
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    model: str = "llama3.2"  # Default Ollama model


class ConversationResponse(BaseModel):
    id: str
    title: str
    created: str
    updated: str
    message_count: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str


# Ollama integration
OLLAMA_API_URL = "http://localhost:11434/api/generate"


async def stream_ollama_response(prompt: str, model: str = "llama3.2") -> AsyncGenerator[str, None]:
    """Stream response from Ollama."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                "POST",
                OLLAMA_API_URL,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as e:
            yield f"[Error connecting to Ollama: {str(e)}]"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    Base.metadata.create_all(bind=engine)
    yield


# FastAPI app
app = FastAPI(title="ChatGPT Backend with Ollama", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Stream chat response from Ollama and save to database."""
    db = SessionLocal()
    
    try:
        # Get or create conversation
        if request.conversation_id:
            conversation = db.query(ConversationDB).filter(
                ConversationDB.id == request.conversation_id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = ConversationDB(
                id=str(uuid.uuid4()),
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        # Save user message
        user_message = MessageDB(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.commit()
        
        # Build context from conversation history
        messages = db.query(MessageDB).filter(
            MessageDB.conversation_id == conversation.id
        ).order_by(MessageDB.timestamp).all()
        
        context = "\n".join([
            f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content}"
            for msg in messages
        ])
        
        # Stream response from Ollama
        async def generate_and_save():
            full_response = []
            async for chunk in stream_ollama_response(context, request.model):
                full_response.append(chunk)
                # Send chunk with metadata
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'conversation_id': conversation.id})}\n\n"
            
            # Save assistant response
            assistant_message = MessageDB(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                role="assistant",
                content="".join(full_response)
            )
            db.add(assistant_message)
            
            # Update conversation timestamp
            conversation.updated = datetime.utcnow()
            db.commit()
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_message.id})}\n\n"
        
        return StreamingResponse(
            generate_and_save(),
            media_type="text/event-stream"
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/conversations", response_model=List[ConversationResponse])
async def get_conversations():
    """Get all conversations."""
    db = SessionLocal()
    try:
        conversations = db.query(ConversationDB).order_by(ConversationDB.updated.desc()).all()
        return [
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                created=conv.created.isoformat(),
                updated=conv.updated.isoformat(),
                message_count=len(conv.messages)
            )
            for conv in conversations
        ]
    finally:
        db.close()


@app.get("/api/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(conversation_id: str):
    """Get all messages in a conversation."""
    db = SessionLocal()
    try:
        messages = db.query(MessageDB).filter(
            MessageDB.conversation_id == conversation_id
        ).order_by(MessageDB.timestamp).all()
        
        return [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp.isoformat()
            )
            for msg in messages
        ]
    finally:
        db.close()


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    db = SessionLocal()
    try:
        conversation = db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        db.delete(conversation)
        db.commit()
        
        return {"status": "deleted", "conversation_id": conversation_id}
    finally:
        db.close()


@app.post("/api/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, title: str):
    """Update conversation title."""
    db = SessionLocal()
    try:
        conversation = db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation.title = title
        db.commit()
        
        return {"status": "updated", "conversation_id": conversation_id, "title": title}
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
