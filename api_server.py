#!/usr/bin/env python3
"""
FastAPI server for Miras Backend - serves the chat frontend.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from contextlib import asynccontextmanager

from config import settings
from validation import GeminiValidator
from ingestion.processor import PDFProcessor
from ingestion.uploader import ContextualUploader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================
class SearchRequest(BaseModel):
    query: str
    mode: str = "hybrid"
    stream: bool = True
    session_id: Optional[str] = None

class Session(BaseModel):
    id: str
    title: str
    started_at: str
    last_message_at: str
    message_count: int
    is_active: bool

class SessionMessage(BaseModel):
    id: str
    query: str
    enhanced_query: Optional[str]
    response: str
    created_at: str

class DocumentInfo(BaseModel):
    id: str
    name: str
    type: str
    size: int
    size_formatted: str
    status: str
    created_at: str
    updated_at: str

# ==================== IN-MEMORY STORAGE ====================
# In production, use a database
sessions_store: Dict[str, Session] = {}
messages_store: Dict[str, List[SessionMessage]] = {}
documents_store: Dict[str, DocumentInfo] = {}

# ==================== LIFESPAN ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Miras API Server")
    yield
    # Shutdown
    logger.info("Shutting down Miras API Server")

# ==================== APP ====================
app = FastAPI(
    title="Miras Backend API",
    description="Document Intelligence System with Gemini and Contextual AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== CONTEXTUAL CLIENT ====================
class ContextualClient:
    """Client for Contextual AI streaming."""
    
    def __init__(self):
        self.api_key = settings.CONTEXTUAL_API_KEY
        self.agent_id = settings.CONTEXTUAL_AGENT_ID
        self.base_url = settings.CONTEXTUAL_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.validator = GeminiValidator()
    
    async def stream_query(self, query: str, conversation_id: Optional[str] = None):
        """Stream query to Contextual and yield SSE events."""
        url = f"{self.base_url}/agents/{self.agent_id}/query"
        
        payload = {
            "messages": [{"role": "user", "content": query}],
            "stream": True
        }
        
        # Don't send conversation_id on first request - let Contextual create it
        # Only send it if we have a valid existing conversation
        if conversation_id and conversation_id != "null" and len(conversation_id) > 10:
            payload["conversation_id"] = conversation_id
        
        full_response = ""
        retrievals = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Yield search phase
                yield f"data: {json.dumps({'phase': 'search', 'content': 'Searching documents...'})}\n\n"
                
                async with client.stream("POST", url, headers=self.headers, json=payload) as response:
                    response.raise_for_status()
                    
                    # Yield synthesis phase
                    yield f"data: {json.dumps({'phase': 'synthesis', 'content': 'Analyzing results...'})}\n\n"
                    
                    line_count = 0
                    async for line in response.aiter_lines():
                        line_count += 1
                        logger.info(f"Line {line_count}: {line[:100] if line else 'empty'}")
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("event", "")
                                event_data = data.get("data", {})
                                
                                # Debug logging
                                if event_type == "message_delta":
                                    logger.debug(f"Message delta: {event_data.get('delta', '')[:50]}")
                                
                                # Handle conversation ID
                                if event_type == "metadata" and "conversation_id" in event_data:
                                    conv_id = event_data["conversation_id"]
                                    if not conversation_id:
                                        yield f"data: {json.dumps({'phase': 'session_created', 'session_id': conv_id})}\n\n"
                                    else:
                                        yield f"data: {json.dumps({'phase': 'session_continued', 'session_id': conv_id})}\n\n"
                                
                                # Stream answer chunks
                                if event_type == "message_delta" and "delta" in event_data:
                                    chunk = event_data["delta"]
                                    full_response += chunk
                                    # Stream the chunk as-is without cleaning
                                    yield f"data: {json.dumps({'phase': 'answer', 'content': chunk})}\n\n"
                                
                                # Capture retrievals for validation
                                if event_type == "retrievals" and "contents" in event_data:
                                    retrievals = event_data["contents"]
                                    
                            except json.JSONDecodeError:
                                continue
                
                # Extract citations from the response
                import re
                # Match citations like .[1]() or .[1]()()
                citation_pattern = r'\.\[(\d+)\]\(\)'
                citations_found = re.findall(citation_pattern, full_response)
                
                # Send citations if found
                if citations_found and retrievals:
                    citation_list = []
                    for cite_num in set(citations_found):
                        try:
                            idx = int(cite_num) - 1
                            if 0 <= idx < len(retrievals):
                                ret = retrievals[idx]
                                citation_list.append({
                                    "number": cite_num,
                                    "doc_name": ret.get("doc_name", "Unknown"),
                                    "page": ret.get("page", "N/A")
                                })
                        except (ValueError, IndexError):
                            continue
                    
                    if citation_list:
                        yield f"data: {json.dumps({'phase': 'citations', 'citations': citation_list})}\n\n"
                
                # Run validation if we have a response
                if full_response and settings.ENABLE_VALIDATION:
                    yield f"data: {json.dumps({'phase': 'validation_start', 'content': 'Starting validation...'})}\n\n"
                    
                    # Stream validation thinking and results
                    for event_type, content in self.validator.validate_response_stream(query, full_response, retrievals):
                        if event_type == "thought":
                            # Stream thinking process, remove asterisks
                            clean_content = content.replace('**', '')
                            yield f"data: {json.dumps({'phase': 'validation_thinking', 'content': clean_content})}\n\n"
                        elif event_type == "result":
                            # Send validation results
                            yield f"data: {json.dumps({'phase': 'validation_complete', 'validation': content})}\n\n"
                
                # Mark as complete
                yield f"data: {json.dumps({'phase': 'complete'})}\n\n"
                    
            except httpx.HTTPStatusError as e:
                yield f"data: {json.dumps({'phase': 'error', 'error': f'API Error: {e.response.status_code}'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'phase': 'error', 'error': str(e)})}\n\n"

# ==================== ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "miras-backend"}

@app.post("/api/search")
async def search(request: SearchRequest):
    """
    Stream search results from Contextual AI.
    Returns Server-Sent Events stream.
    """
    client = ContextualClient()
    
    # Create or get session
    session_id = request.session_id or str(uuid.uuid4())
    
    if session_id not in sessions_store:
        sessions_store[session_id] = Session(
            id=session_id,
            title=request.query[:50],  # First 50 chars as title
            started_at=datetime.now().isoformat(),
            last_message_at=datetime.now().isoformat(),
            message_count=1,
            is_active=True
        )
        messages_store[session_id] = []
    else:
        # Update existing session
        sessions_store[session_id].last_message_at = datetime.now().isoformat()
        sessions_store[session_id].message_count += 1
    
    # Store message
    message = SessionMessage(
        id=str(uuid.uuid4()),
        query=request.query,
        enhanced_query=None,
        response="",  # Will be filled as streaming completes
        created_at=datetime.now().isoformat()
    )
    messages_store[session_id].append(message)
    
    async def generate():
        # Don't pass session_id on first query - let Contextual create its conversation_id
        contextual_conv_id = None if session_id not in sessions_store or sessions_store[session_id].message_count <= 1 else session_id
        async for event in client.stream_query(request.query, contextual_conv_id):
            yield event
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/conversation/sessions")
async def get_sessions(
    limit: int = Query(20, description="Number of sessions to return"),
    active_only: bool = Query(False, description="Return only active sessions")
):
    """Get conversation sessions."""
    sessions = list(sessions_store.values())
    
    if active_only:
        sessions = [s for s in sessions if s.is_active]
    
    # Sort by last message time
    sessions.sort(key=lambda x: x.last_message_at, reverse=True)
    
    return {
        "sessions": sessions[:limit]
    }

@app.get("/api/conversation/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get messages for a specific session."""
    if session_id not in messages_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return messages_store[session_id]

@app.delete("/api/conversation/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions_store[session_id]
    if session_id in messages_store:
        del messages_store[session_id]
    
    return {"success": True, "message": "Session deleted"}

@app.get("/api/documents")
async def get_documents(
    limit: int = Query(1000, description="Maximum number of documents to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor")
):
    """Get list of documents from Contextual datastore."""
    datastore_id = settings.CONTEXTUAL_DATASTORE_ID
    
    if not datastore_id:
        # Fallback to in-memory store if no datastore ID
        documents = list(documents_store.values())
        return {
            "success": True,
            "documents": documents,
            "total": len(documents),
            "error": None
        }
    
    # Fetch from Contextual API
    url = f"{settings.CONTEXTUAL_BASE_URL}/datastores/{datastore_id}/documents"
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    
    headers = {
        "Authorization": f"Bearer {settings.CONTEXTUAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Transform Contextual documents to our format
            documents = []
            for doc in data.get("documents", []):
                documents.append(DocumentInfo(
                    id=doc.get("id", ""),
                    name=doc.get("name", "Unknown"),
                    type=doc.get("type", "document"),
                    size=doc.get("size", 0),
                    size_formatted=f"{doc.get('size', 0) / 1024:.1f} KB" if doc.get('size') else "Unknown",
                    status=doc.get("ingestion_status", "completed"),
                    created_at=doc.get("created_at", datetime.now().isoformat()),
                    updated_at=doc.get("updated_at", datetime.now().isoformat())
                ))
            
            return {
                "success": True,
                "documents": [doc.dict() for doc in documents],
                "total": data.get("total_count", len(documents)),
                "error": None,
                "next_cursor": data.get("next_cursor")
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Contextual API error: {e.response.status_code}")
            return {
                "success": False,
                "documents": [],
                "total": 0,
                "error": f"API Error: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"Error fetching documents: {e}")
            return {
                "success": False,
                "documents": [],
                "total": 0,
                "error": str(e)
            }

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document."""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    del documents_store[doc_id]
    
    return {"success": True, "message": "Document deleted"}

@app.post("/api/ingest/contextual/batch")
async def ingest_documents(
    files: List[UploadFile] = File(...),
    user_instructions: Optional[str] = Form(None)
):
    """
    Ingest documents into Contextual AI.
    Returns SSE stream with progress updates.
    """
    async def generate():
        processor = PDFProcessor()
        uploader = ContextualUploader()
        
        for i, file in enumerate(files):
            try:
                # Yield progress
                yield f"data: {json.dumps({'phase': 'processing', 'file': file.filename, 'progress': i/len(files)})}\n\n"
                
                # Save file temporarily
                temp_path = Path(f"/tmp/{file.filename}")
                content = await file.read()
                temp_path.write_bytes(content)
                
                # Process based on file type
                if file.filename.endswith('.pdf'):
                    # Extract with Gemini
                    yield f"data: {json.dumps({'phase': 'extracting', 'file': file.filename})}\n\n"
                    result = processor.process_pdf(str(temp_path))
                    
                    if result["success"]:
                        # Upload to Contextual
                        yield f"data: {json.dumps({'phase': 'uploading', 'file': file.filename})}\n\n"
                        upload_result = uploader.upload_document(
                            content=result["extracted_text"],
                            filename=file.filename,
                            metadata=result["metadata"]
                        )
                        
                        if upload_result["success"]:
                            # Store document info
                            doc_id = str(uuid.uuid4())
                            documents_store[doc_id] = DocumentInfo(
                                id=doc_id,
                                name=file.filename,
                                type="pdf",
                                size=len(content),
                                size_formatted=f"{len(content) / 1024:.1f} KB",
                                status="completed",
                                created_at=datetime.now().isoformat(),
                                updated_at=datetime.now().isoformat()
                            )
                            yield f"data: {json.dumps({'phase': 'completed', 'file': file.filename, 'doc_id': doc_id})}\n\n"
                        else:
                            yield f"data: {json.dumps({'phase': 'error', 'file': file.filename, 'error': upload_result['error']})}\n\n"
                    else:
                        yield f"data: {json.dumps({'phase': 'error', 'file': file.filename, 'error': result['error']})}\n\n"
                else:
                    # For non-PDF files, direct upload
                    yield f"data: {json.dumps({'phase': 'uploading', 'file': file.filename})}\n\n"
                    upload_result = uploader.upload_document(
                        content=content.decode('utf-8', errors='ignore'),
                        filename=file.filename,
                        metadata={"type": file.content_type}
                    )
                    
                    if upload_result["success"]:
                        doc_id = str(uuid.uuid4())
                        documents_store[doc_id] = DocumentInfo(
                            id=doc_id,
                            name=file.filename,
                            type=file.content_type or "unknown",
                            size=len(content),
                            size_formatted=f"{len(content) / 1024:.1f} KB",
                            status="completed",
                            created_at=datetime.now().isoformat(),
                            updated_at=datetime.now().isoformat()
                        )
                        yield f"data: {json.dumps({'phase': 'completed', 'file': file.filename, 'doc_id': doc_id})}\n\n"
                
                # Clean up
                temp_path.unlink(missing_ok=True)
                
            except Exception as e:
                yield f"data: {json.dumps({'phase': 'error', 'file': file.filename, 'error': str(e)})}\n\n"
        
        yield f"data: {json.dumps({'phase': 'batch_complete', 'total': len(files)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)