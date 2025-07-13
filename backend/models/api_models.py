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
    knowledge_base: KnowledgeBase = Field(..., description="Created knowledge base")
    api_key: APIKey = Field(..., description="Generated API key")
    message: str = Field(..., description="Success message")


class UploadDocumentsRequest(BaseModel):
    """Request model for uploading documents to a knowledge base"""
    knowledge_base_id: str = Field(..., description="Target knowledge base ID")


class UploadDocumentsResponse(BaseModel):
    """Response model for document upload"""
    knowledge_base_id: str = Field(..., description="Knowledge base ID")
    uploaded_documents: List[Dict[str, Any]] = Field(..., description="List of uploaded document info")
    total_documents: int = Field(..., description="Total documents in knowledge base")
    message: str = Field(..., description="Success message")


class PublicChatRequest(BaseModel):
    """Request model for public chat API"""
    message: str = Field(..., description="User's message")
    api_key: str = Field(..., description="API key for authentication")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")


class PublicChatResponse(BaseModel):
    """Response model for public chat API"""
    response: str = Field(..., description="AI agent's response")
    session_id: str = Field(..., description="Session ID for conversation tracking")
    usage: Dict[str, int] = Field(..., description="Usage statistics")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class KnowledgeBaseStats(BaseModel):
    """Model for knowledge base statistics"""
    knowledge_base_id: str = Field(..., description="Knowledge base ID")
    total_documents: int = Field(..., description="Total number of documents")
    total_chunks: int = Field(..., description="Total number of chunks")
    total_text_length: int = Field(..., description="Total text length in characters")
    api_calls_today: int = Field(..., description="API calls made today")
    api_calls_total: int = Field(..., description="Total API calls")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp") 