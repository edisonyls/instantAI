import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import aiofiles

try:
    from backend.config import settings
    from backend.models.api_models import (
        CreateKnowledgeBaseRequest,
        PublicChatRequest, PublicChatResponse,
        TestAPIKeyRequest,
        UpdateSystemSettingsRequest, UpdateSystemSettingsResponse,
        AgentSettingsModel, UpdateAgentSettingsRequest
    )
    from backend.models.chat_models import ChatMessage, MessageRole
    from backend.services.database_service import database_service
    from backend.services.api_key_service import api_key_service
    from backend.services.conversation_service import conversation_service
    from backend.services.rag_service import rag_service
    from backend.services.ollama_service import OllamaService
    from backend.services.document_processor import DocumentProcessor
    from backend.services.agent_settings_service import agent_settings_service
except ImportError:
    from config import settings
    from models.api_models import (
        CreateKnowledgeBaseRequest,
        PublicChatRequest, PublicChatResponse,
        TestAPIKeyRequest,
        UpdateSystemSettingsRequest, UpdateSystemSettingsResponse,
        AgentSettingsModel, UpdateAgentSettingsRequest
    )
    from models.chat_models import ChatMessage, MessageRole
    from services.database_service import database_service
    from services.api_key_service import api_key_service
    from services.conversation_service import conversation_service
    from services.rag_service import rag_service
    from services.ollama_service import OllamaService
    from services.document_processor import DocumentProcessor
    from services.agent_settings_service import agent_settings_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title=settings.PROJECT_NAME, version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ollama_service = OllamaService()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("Starting InstantAI backend...")
        await database_service.initialize()
        await database_service.create_tables()
        await rag_service.initialize()
        await ollama_service.initialize()

        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise


@app.get("/")
async def root():
    return {"message": "InstantAI Backend", "status": "running", "version": "2.0.0"}


async def validate_api_key_dependency(x_api_key: str = Header(None)):
    """Dependency to validate API key"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    result = await api_key_service.validate_api_key(x_api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")

    knowledge_base_id, api_key = result

    # Check rate limiting
    rate_limit_ok = await api_key_service.check_rate_limit(x_api_key)
    if not rate_limit_ok:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return knowledge_base_id, api_key


async def validate_api_key_from_body(api_key: str):
    """Helper function to validate API key from request body"""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    result = await api_key_service.validate_api_key(api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")

    knowledge_base_id, validated_api_key = result

    # Check rate limiting
    rate_limit_ok = await api_key_service.check_rate_limit(api_key)
    if not rate_limit_ok:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return knowledge_base_id, validated_api_key


# Knowledge Base Management
@app.post("/api/knowledge-bases")
async def create_knowledge_base(request: CreateKnowledgeBaseRequest):
    """Create a new knowledge base"""
    try:
        kb = await api_key_service.create_knowledge_base(
            name=request.name,
            description=request.description,
            agent_type=request.agent_type
        )

        # Create an API key for the knowledge base
        api_key = await api_key_service.create_api_key(
            knowledge_base_id=kb.id,
            name=f"Default key for {kb.name}"
        )

        return {
            "knowledge_base": kb.dict(),
            "api_key": api_key.dict(),
            "message": "Knowledge base created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating knowledge base: {str(e)}")


@app.get("/api/knowledge-bases")
async def list_knowledge_bases():
    """List all knowledge bases"""
    try:
        knowledge_bases = await api_key_service.list_knowledge_bases()
        return {"knowledge_bases": knowledge_bases}
    except Exception as e:
        logger.error(f"Error listing knowledge bases: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error listing knowledge bases: {str(e)}")


@app.get("/api/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: str):
    """Get a specific knowledge base"""
    try:
        kb = await api_key_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        documents = await rag_service.list_documents(kb_id)
        # Fetch per-agent settings if any
        agent_settings_row = await agent_settings_service.get_settings(kb_id)
        api_keys = await api_key_service.list_api_keys(kb_id)
        api_key = api_keys[0] if api_keys else None

        # Compose default per-agent config based on global settings for new agents
        default_config = {}
        if not agent_settings_row and kb.agent_type == "data_processing":
            default_config = {
                "chunk_size": settings.CHUNK_SIZE,
                "chunk_overlap": settings.CHUNK_OVERLAP,
                "max_retrieved_chunks": settings.MAX_RETRIEVED_CHUNKS,
                "similarity_threshold": settings.SIMILARITY_THRESHOLD,
            }

        return {
            **kb.dict(),
            "documents": documents,
            "api_key": api_key,
            "agent_settings": {
                "knowledge_base_id": kb.id,
                "agent_type": kb.agent_type,
                "config": agent_settings_row.config if agent_settings_row else default_config,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting knowledge base: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting knowledge base: {str(e)}")


@app.delete("/api/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """Delete a knowledge base and all associated data"""
    try:
        success = await api_key_service.delete_knowledge_base(kb_id)
        if not success:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        return {"message": "Knowledge base deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge base: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting knowledge base: {str(e)}")


# Document Management
@app.post("/api/knowledge-bases/{kb_id}/documents")
async def upload_documents(
    kb_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    validation_result: tuple = Depends(validate_api_key_dependency),
):
    """Upload and process multiple documents"""
    knowledge_base_id, api_key = validation_result

    # Verify the knowledge base ID matches the API key
    if knowledge_base_id != kb_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    uploaded_documents = []
    errors = []

    for file in files:
        if not file.filename:
            errors.append(
                {"filename": "unknown", "error": "Filename is required"})
            continue

        if file.size and file.size > settings.MAX_FILE_SIZE:
            errors.append({"filename": file.filename,
                          "error": "File too large"})
            continue

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_path = temp_file.name

            content = ""
            file_extension = Path(file.filename).suffix.lower()

            if file_extension == '.txt':
                async with aiofiles.open(temp_path, mode='r', encoding='utf-8') as f:
                    content = await f.read()
            elif file_extension == '.docx':
                doc_processor = DocumentProcessor()
                try:
                    content = doc_processor.extract_text(temp_path)
                except Exception as e:
                    errors.append(
                        {"filename": file.filename, "error": f"Error processing .docx file: {str(e)}"})
                    os.unlink(temp_path)
                    continue
            else:
                errors.append(
                    {"filename": file.filename, "error": "Unsupported file type. Only .txt and .docx files are supported."})
                os.unlink(temp_path)
                continue

            document_id = await rag_service.process_document(
                text=content,
                filename=file.filename,
                knowledge_base_id=knowledge_base_id,
                file_size=file.size,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            # Clean up temporary file
            os.unlink(temp_path)

            uploaded_documents.append({
                "document_id": document_id,
                "filename": file.filename,
                "status": "processed"
            })

        except Exception as e:
            logger.error(f"Error uploading document {file.filename}: {str(e)}")
            errors.append({"filename": file.filename, "error": str(e)})
            # Clean up temporary file on error
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass

    return {
        "uploaded_documents": uploaded_documents,
        "errors": errors,
        "total_uploaded": len(uploaded_documents),
        "total_errors": len(errors),
        "message": f"Processed {len(uploaded_documents)} documents successfully"
    }


@app.delete("/api/knowledge-bases/{kb_id}/documents/{document_id}")
async def delete_document(kb_id: str, document_id: str, validation_result: tuple = Depends(validate_api_key_dependency)):
    """Delete a document"""
    knowledge_base_id, api_key = validation_result

    # Verify the knowledge base ID matches the API key
    if knowledge_base_id != kb_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Verify document exists and belongs to the knowledge base
        document = await rag_service.get_document_info(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        if document.knowledge_base_id != knowledge_base_id:
            raise HTTPException(status_code=403, detail="Access denied")

        success = await rag_service.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting document: {str(e)}")


@app.post("/api/public/chat")
async def public_chat_api(request: PublicChatRequest):
    """Handle public chat requests with API key in body"""
    try:
        validation_result = await validate_api_key_from_body(request.api_key)
        knowledge_base_id, api_key = validation_result

        # Generate session_id if not provided
        session_id = request.session_id or str(uuid.uuid4())

        conversation_context = await conversation_service.get_conversation_context(
            session_id, max_messages=5
        )

        # Load per-agent retrieval overrides if any
        agent_settings = await agent_settings_service.get_settings(knowledge_base_id)
        max_chunks_override = None
        similarity_threshold_override = None
        if agent_settings and agent_settings.config:
            cfg = agent_settings.config
            if isinstance(cfg.get("max_retrieved_chunks"), int):
                max_chunks_override = cfg.get("max_retrieved_chunks")
            if isinstance(cfg.get("similarity_threshold"), (int, float)):
                similarity_threshold_override = float(cfg.get("similarity_threshold"))

        context_chunks = await rag_service.retrieve_context(
            query=request.message,
            knowledge_base_id=knowledge_base_id,
            max_chunks=max_chunks_override,
            similarity_threshold=similarity_threshold_override,
        )

        rag_context = "\n\n".join([chunk.content for chunk in context_chunks])

        system_prompt = f"""You are a helpful AI assistant. Use the following context to answer questions accurately and helpfully.

Context from documents:
{rag_context}

Previous conversation:
{conversation_context}

Answer the user's question based on the provided context. If the context doesn't contain relevant information, say so politely."""

        # Add user message to conversation
        user_message = ChatMessage(
            role=MessageRole.USER, content=request.message)
        await conversation_service.add_message(
            session_id, user_message, knowledge_base_id, api_key
        )

        # Generate response using Ollama
        response = await ollama_service.generate_response(
            query=request.message,
            context_chunks=context_chunks,
            conversation_context=conversation_context
        )

        # Add assistant response to conversation
        assistant_message = ChatMessage(
            role=MessageRole.ASSISTANT, content=response)
        await conversation_service.add_message(
            session_id, assistant_message, knowledge_base_id, api_key
        )

        return PublicChatResponse(
            response=response,
            session_id=session_id,
            usage={"messages": 1, "tokens": len(response)},
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in public chat: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing chat: {str(e)}")


@app.post("/api/public/test-key")
async def test_api_key(request: TestAPIKeyRequest):
    """Test API key validity without incrementing usage count"""
    try:
        if not request.api_key:
            raise HTTPException(status_code=401, detail="API key required")

        result = await api_key_service.test_api_key(request.api_key)
        if not result:
            raise HTTPException(status_code=401, detail="Invalid API key")

        knowledge_base_id, api_key = result
        
        return {
            "valid": True,
            "knowledge_base_id": knowledge_base_id,
            "message": "API key is valid"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing API key: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error testing API key: {str(e)}")


# Conversation Management

@app.get("/api/conversations/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation history for a session"""
    try:
        conversation = await conversation_service.get_conversation(session_id)
        return {"session_id": session_id, "messages": conversation}
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting conversation: {str(e)}")


@app.post("/api/conversations/cleanup")
async def cleanup_conversations():
    """Clean up expired conversations"""
    try:
        cleaned_count = await conversation_service.cleanup_expired_conversations()
        return {
            "message": f"Cleaned up {cleaned_count} expired conversations",
            "cleaned_count": cleaned_count
        }
    except Exception as e:
        logger.error(f"Error cleaning up conversations: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error cleaning up conversations: {str(e)}")


# System and Health Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database health
        db_healthy = await database_service.health_check()

        # Check Ollama service
        ollama_health = await ollama_service.health_check()
        ollama_healthy = ollama_health.get("status") == "healthy"

        status = "healthy" if (db_healthy and ollama_healthy) else "unhealthy"

        return {
            "status": status,
            "services": {
                "rag": "healthy" if db_healthy else "unhealthy",  # Frontend expects 'rag' service
                "ollama": "healthy" if ollama_healthy else ("model_downloading" if ollama_health.get("status") == "model_not_ready" else "unhealthy")
            },
            "ollama_details": ollama_health,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "services": {
                "rag": "unhealthy",  # Frontend expects 'rag' service
                "ollama": "unhealthy"
            },
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/system-info")
async def get_system_info():
    """Get system information and statistics"""
    try:
        # Get conversation stats
        conv_stats = await conversation_service.get_conversation_stats()

        # Get knowledge base stats
        knowledge_bases = await api_key_service.list_knowledge_bases()

        total_documents = sum(kb.total_documents for kb in knowledge_bases)
        total_chunks = sum(kb.total_chunks for kb in knowledge_bases)

        # Check Ollama status for AI configuration
        ollama_health = await ollama_service.health_check()

        # Format response for frontend expectations
        return {
            "ai_configuration": {
                "ollama_model": settings.OLLAMA_MODEL,
                "ollama_host": settings.OLLAMA_HOST,
                "max_context_length": 4096,  # Default context length for most models
                "similarity_threshold": settings.SIMILARITY_THRESHOLD,
                "max_retrieved_chunks": settings.MAX_RETRIEVED_CHUNKS,
                "embedding_model": settings.EMBEDDING_MODEL,
                "ollama_status": ollama_health.get("status", "unknown"),
                "model_ready": ollama_health.get("model_ready", False),
                "available_models": ollama_health.get("available_models", [])
            },
            "document_processing": {
                "chunk_size": settings.CHUNK_SIZE,
                "chunk_overlap": settings.CHUNK_OVERLAP,
                "max_file_size_mb": settings.MAX_FILE_SIZE // (1024 * 1024),
                "max_file_size_bytes": settings.MAX_FILE_SIZE
            },
            "storage": {
                "upload_directory": settings.UPLOAD_DIR,
                "temp_directory": settings.TEMP_DIR,
                "chroma_db_path": "PostgreSQL with pgvector",
                "vector_db_collection": f"{len(knowledge_bases)} knowledge bases"
            },
            "security": {
                "access_token_expire_minutes": 30,  # Default JWT token expiration
                "cors_origins": settings.BACKEND_CORS_ORIGINS
            },
            "logging": {
                "log_level": settings.LOG_LEVEL,
                "log_file": "stdout"
            }
        }
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting system info: {str(e)}")


@app.put("/api/system-settings")
async def update_system_settings(request: UpdateSystemSettingsRequest):
    """Update system settings"""
    try:
        updated_settings = {}

        # Update MAX_RETRIEVED_CHUNKS if provided
        if request.max_retrieved_chunks is not None:
            if not (1 <= request.max_retrieved_chunks <= 50):
                raise HTTPException(
                    status_code=400,
                    detail="max_retrieved_chunks must be between 1 and 50"
                )

            settings.MAX_RETRIEVED_CHUNKS = request.max_retrieved_chunks
            updated_settings["max_retrieved_chunks"] = request.max_retrieved_chunks

            logger.info(
                f"Updated MAX_RETRIEVED_CHUNKS to {request.max_retrieved_chunks}")

        if not updated_settings:
            raise HTTPException(
                status_code=400,
                detail="No valid settings provided to update"
            )

        return UpdateSystemSettingsResponse(
            message="Settings updated successfully",
            updated_settings=updated_settings
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating system settings: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating system settings: {str(e)}")


@app.get("/api/knowledge-bases/{kb_id}/settings")
async def get_agent_settings(kb_id: str):
    try:
        settings_row = await agent_settings_service.get_settings(kb_id)
        if not settings_row:
            # Return defaults based on knowledge base type
            kb = await api_key_service.get_knowledge_base(kb_id)
            if not kb:
                raise HTTPException(status_code=404, detail="Knowledge base not found")
            return {
                "knowledge_base_id": kb.id,
                "agent_type": kb.agent_type,
                "config": {}
            }
        return {
            "knowledge_base_id": str(settings_row.knowledge_base_id),
            "agent_type": settings_row.agent_type,
            "config": settings_row.config,
            "created_at": settings_row.created_at,
            "updated_at": settings_row.updated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching agent settings")


@app.put("/api/knowledge-bases/{kb_id}/settings")
async def update_agent_settings(kb_id: str, request: UpdateAgentSettingsRequest):
    try:
        kb = await api_key_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        # Enforce immutability of chunking settings after documents exist
        if kb.agent_type == "data_processing":
            cfg = request.config or {}
            # Determine if changing chunking parameters
            changing_chunking = any(key in cfg for key in ["chunk_size", "chunk_overlap"])
            if changing_chunking:
                # Load current KB to check document counts
                # Use rag_service.stats or KnowledgeBase totals
                stats = await rag_service.get_knowledge_base_stats(kb_id)
                if stats.get("total_documents", 0) > 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Chunk Size and Chunk Overlap cannot be changed after documents are uploaded."
                    )
        updated = await agent_settings_service.upsert_settings(kb_id, kb.agent_type, request.config or {})
        return {
            "knowledge_base_id": str(updated.knowledge_base_id),
            "agent_type": updated.agent_type,
            "config": updated.config,
            "created_at": updated.created_at,
            "updated_at": updated.updated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating agent settings")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
