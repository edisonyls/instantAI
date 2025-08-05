from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class KnowledgeBase(BaseModel):
    """Model for a knowledge base containing multiple documents"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique knowledge base ID")
    name: str = Field(..., description="Name of the knowledge base")
    description: Optional[str] = Field(None, description="Description of the knowledge base")
    document_ids: List[str] = Field(default_factory=list, description="List of document IDs in this knowledge base")
    total_documents: int = Field(default=0, description="Total number of documents")
    total_chunks: int = Field(default=0, description="Total number of chunks across all documents")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class APIKey(BaseModel):
    """Model for API key management"""
    key: str = Field(..., description="The API key")
    knowledge_base_id: str = Field(..., description="Associated knowledge base ID")
    name: str = Field(..., description="Name/label for the API key")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    usage_count: int = Field(default=0, description="Number of times used")
    is_active: bool = Field(default=True, description="Whether the key is active")
    rate_limit: Optional[int] = Field(default=100, description="Requests per hour limit")


class CreateKnowledgeBaseRequest(BaseModel):
    """Request model for creating a knowledge base"""
    name: str = Field(..., description="Name of the knowledge base")
    description: Optional[str] = Field(None, description="Description of the knowledge base")


class CreateKnowledgeBaseResponse(BaseModel):
    """Response model for creating a knowledge base"""
    knowledge_base_id: str = Field(..., description="Created knowledge base ID")
    name: str = Field(..., description="Knowledge base name")
    description: Optional[str] = Field(None, description="Knowledge base description")
    api_key: str = Field(..., description="Generated API key")


class DocumentUploadResponse(BaseModel):
    """Response model for document upload"""
    document_id: str = Field(..., description="Generated document ID")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Success message")


class PublicChatRequest(BaseModel):
    """Request model for public chat API"""
    message: str = Field(..., description="User's message")
    api_key: str = Field(..., description="API key for authentication")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    model: Optional[str] = Field(default="gemma2:2b", description="AI model to use")


class PublicChatResponse(BaseModel):
    """Response model for public chat API"""
    response: str = Field(..., description="AI agent's response")
    session_id: str = Field(..., description="Session ID for conversation tracking")
    usage: Dict[str, int] = Field(..., description="Usage statistics")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp") 