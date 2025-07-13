from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    """Message roles in the conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    """Model for incoming chat messages"""
    content: str = Field(..., description="The message content")
    role: MessageRole = Field(default=MessageRole.USER, description="The role of the message sender")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    document_id: Optional[str] = Field(None, description="ID of the document to query against")

class ChatResponse(BaseModel):
    """Model for chat responses"""
    response: str = Field(..., description="The AI agent's response")
    context_used: bool = Field(default=False, description="Whether context from documents was used")
    sources: Optional[List[str]] = Field(default=None, description="Sources used for the response")
    confidence: Optional[float] = Field(default=None, description="Confidence score of the response")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")

class DocumentInfo(BaseModel):
    """Model for document information"""
    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    text_length: int = Field(..., description="Length of extracted text")
    chunk_count: int = Field(..., description="Number of chunks created")
    upload_timestamp: datetime = Field(default_factory=datetime.now, description="Upload timestamp")
    processing_status: str = Field(default="completed", description="Processing status")

class DocumentUploadResponse(BaseModel):
    """Model for document upload responses"""
    message: str = Field(..., description="Success message")
    document_id: str = Field(..., description="Generated document ID")
    filename: str = Field(..., description="Original filename")
    text_length: int = Field(..., description="Length of extracted text")
    chunk_count: int = Field(..., description="Number of chunks created")

class ContextChunk(BaseModel):
    """Model for context chunks used in RAG"""
    content: str = Field(..., description="The chunk content")
    similarity_score: float = Field(..., description="Similarity score to the query")
    source: str = Field(..., description="Source document")
    chunk_id: str = Field(..., description="Unique chunk identifier")

class HealthStatus(BaseModel):
    """Model for health check responses"""
    status: str = Field(..., description="Overall health status")
    services: Dict[str, Any] = Field(default_factory=dict, description="Status of individual services")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")

class ErrorResponse(BaseModel):
    """Model for error responses"""
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking") 