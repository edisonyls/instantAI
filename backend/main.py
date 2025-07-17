from config import settings
from models.api_models import (
    CreateKnowledgeBaseRequest, CreateKnowledgeBaseResponse,
    UploadDocumentsResponse, PublicChatRequest, PublicChatResponse,
    KnowledgeBaseStats
)
from models.chat_models import ChatMessage, ChatResponse
from services.api_key_service import APIKeyService
from services.ollama_service import OllamaService
from services.rag_service import RAGService
from services.document_processor import DocumentProcessor
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Optional
import os
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Use direct imports for Docker container (flat structure)

app = FastAPI(
    title="InstantAI Backend",
    description="AI Document Processing and Chat API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
document_processor = DocumentProcessor()
rag_service = RAGService()
ollama_service = OllamaService()
api_key_service = APIKeyService()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await rag_service.initialize()
    await ollama_service.initialize()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "InstantAI Backend is running", "timestamp": datetime.now()}


@app.post("/api/knowledge-bases", response_model=CreateKnowledgeBaseResponse)
async def create_knowledge_base(request: CreateKnowledgeBaseRequest):
    """
    Create a new knowledge base and generate an API key
    """
    try:
        # Create knowledge base and API key
        kb, api_key = await api_key_service.create_knowledge_base(
            name=request.name,
            description=request.description
        )

        return CreateKnowledgeBaseResponse(
            knowledge_base=kb,
            api_key=api_key,
            message="Knowledge base created successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating knowledge base: {str(e)}")


@app.post("/api/knowledge-bases/{kb_id}/documents", response_model=UploadDocumentsResponse)
async def upload_documents(kb_id: str, files: List[UploadFile] = File(...)):
    """
    Upload multiple documents to a knowledge base
    """
    try:
        logger.info(f"Starting document upload for knowledge base: {kb_id}")

        # Validate knowledge base exists
        kb = await api_key_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        logger.info(f"Knowledge base found: {kb}")

        # Validate total file size
        total_size = 0
        for file in files:
            content = await file.read()
            total_size += len(content)
            await file.seek(0)  # Reset file position

        logger.info(f"Total file size: {total_size} bytes")

        if total_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Total file size exceeds limit of {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        uploaded_documents = []

        for file in files:
            logger.info(f"Processing file: {file.filename}")

            # Validate file type
            if not file.filename.endswith('.docx'):
                logger.warning(f"Skipping non-docx file: {file.filename}")
                continue

            # Save uploaded file temporarily
            file_path = f"temp/{file.filename}"
            os.makedirs("temp", exist_ok=True)

            logger.info(f"Saving file to: {file_path}")

            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            logger.info(f"File saved, validating and extracting text...")

            # Validate document before processing
            validation_result = document_processor.validate_document(file_path)
            if not validation_result['valid']:
                logger.error(f"Document validation failed for {file.filename}: {validation_result['errors']}")
                os.remove(file_path)  # Clean up invalid file
                continue

            # Process document
            extracted_text = document_processor.extract_text(file_path)

            logger.info(f"Text extracted, length: {len(extracted_text)}")

            # Create embeddings and store in vector database
            document_id = await rag_service.process_document(
                extracted_text,
                file.filename,
                knowledge_base_id=kb_id
            )

            logger.info(f"Document processed with ID: {document_id}")

            uploaded_documents.append({
                "document_id": document_id,
                "filename": file.filename,
                "text_length": len(extracted_text)
            })

            # Clean up temporary file
            os.remove(file_path)
            logger.info(f"Temporary file cleaned up: {file_path}")

        logger.info(f"All files processed, updating knowledge base stats...")

        # Update knowledge base stats
        kb_stats = await rag_service.get_knowledge_base_stats(kb_id)
        await api_key_service.update_knowledge_base_stats(
            kb_id,
            kb_stats['document_ids'],
            kb_stats['total_chunks']
        )

        logger.info(
            f"Upload completed successfully. {len(uploaded_documents)} documents uploaded")

        return UploadDocumentsResponse(
            knowledge_base_id=kb_id,
            uploaded_documents=uploaded_documents,
            total_documents=len(kb_stats['document_ids']),
            message=f"Successfully uploaded {len(uploaded_documents)} documents"
        )

    except Exception as e:
        logger.error(f"Error uploading documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error uploading documents: {str(e)}")


@app.get("/api/knowledge-bases")
async def list_knowledge_bases():
    """
    List all knowledge bases
    """
    try:
        knowledge_bases = await api_key_service.list_knowledge_bases()
        return {"knowledge_bases": knowledge_bases}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing knowledge bases: {str(e)}")


@app.get("/api/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: str):
    """
    Get details of a specific knowledge base
    """
    try:
        kb = await api_key_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        # Get documents and stats
        documents = await rag_service.get_documents_by_knowledge_base(kb_id)
        stats = await rag_service.get_knowledge_base_stats(kb_id)

        # Get API key
        api_key = await api_key_service.get_api_key_by_kb_id(kb_id)

        return {
            "knowledge_base": kb,
            "documents": documents,
            "stats": stats,
            "api_key": api_key
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting knowledge base: {str(e)}")


@app.post("/api/public/chat", response_model=PublicChatResponse)
async def public_chat(request: PublicChatRequest):
    """
    Public API endpoint for customers to chat with the AI agent
    """
    import time
    start_time = time.time()

    try:
        # Validate API key (don't count usage yet)
        api_key = await api_key_service.validate_api_key(request.api_key, count_usage=False)
        if not api_key:
            raise HTTPException(
                status_code=401, detail="Invalid or inactive API key")

        # Check rate limit
        if not await api_key_service.check_rate_limit(request.api_key):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Get knowledge base
        kb = await api_key_service.get_knowledge_base(api_key.knowledge_base_id)
        if not kb:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        # Retrieve relevant context from vector database
        rag_start = time.time()
        context = await rag_service.retrieve_context(
            request.message,
            knowledge_base_id=api_key.knowledge_base_id
        )
        rag_time = time.time() - rag_start

        # Generate response using Ollama
        ollama_start = time.time()
        response = await ollama_service.generate_response(request.message, context)
        ollama_time = time.time() - ollama_start

        # Now count the usage since we successfully processed the request
        await api_key_service.validate_api_key(request.api_key, count_usage=True)

        total_time = time.time() - start_time

        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        return PublicChatResponse(
            response=response,
            session_id=session_id,
            usage={
                "tokens_used": len(response.split()),  # Simple approximation
                "context_chunks": len(context),
                "processing_time_ms": int(total_time * 1000)
            },
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing request")


@app.delete("/api/knowledge-bases/{kb_id}/documents/{document_id}")
async def delete_document(kb_id: str, document_id: str):
    """
    Delete a document from a knowledge base
    """
    try:
        # Validate knowledge base exists
        kb = await api_key_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found")

        # Delete document
        await rag_service.delete_document(document_id)

        # Update knowledge base stats
        kb_stats = await rag_service.get_knowledge_base_stats(kb_id)
        await api_key_service.update_knowledge_base_stats(
            kb_id,
            kb_stats['document_ids'],
            kb_stats['total_chunks']
        )

        return {"message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting document: {str(e)}")


@app.post("/api/public/test-key")
async def test_api_key(request: dict):
    """
    Test API key endpoint that doesn't count as usage
    """
    try:
        api_key = request.get("api_key")
        if not api_key:
            raise HTTPException(status_code=400, detail="API key is required")

        # Test the API key without counting usage
        is_valid = await api_key_service.test_api_key(api_key)

        if not is_valid:
            raise HTTPException(
                status_code=401, detail="Invalid or inactive API key")

        return {"valid": True, "message": "API key is valid"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test API key error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error testing API key")


@app.get("/health")
async def health_check():
    """
    Comprehensive health check
    """
    try:
        rag_status = await rag_service.health_check()
        ollama_status = await ollama_service.health_check()

        return {
            "status": "healthy",
            "services": {
                "rag": rag_status,
                "ollama": ollama_status
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/system-info")
async def get_system_info():
    """
    Get current system configuration information
    """
    return {
        "ai_configuration": {
            "ollama_model": settings.OLLAMA_MODEL,
            "ollama_host": settings.OLLAMA_HOST,
            "max_context_length": settings.MAX_CONTEXT_LENGTH,
            "similarity_threshold": settings.SIMILARITY_THRESHOLD,
            "max_retrieved_chunks": settings.MAX_RETRIEVED_CHUNKS,
            "embedding_model": settings.EMBEDDING_MODEL
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
            "chroma_db_path": settings.CHROMA_DB_PATH,
            "vector_db_collection": settings.VECTOR_DB_COLLECTION
        },
        "security": {
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "cors_origins": settings.BACKEND_CORS_ORIGINS
        },
        "logging": {
            "log_level": settings.LOG_LEVEL,
            "log_file": settings.LOG_FILE
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
