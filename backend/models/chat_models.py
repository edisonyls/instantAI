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

class DocumentInfo(BaseModel):
    """Model for document information"""
    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    knowledge_base_id: str = Field(..., description="Knowledge base ID")
    chunk_count: int = Field(..., description="Number of chunks created")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    text_length: Optional[int] = Field(None, description="Text length in characters")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

class ContextChunk(BaseModel):
    """Model for context chunks used in RAG"""
    content: str = Field(..., description="The chunk content")
    document_id: str = Field(..., description="Document ID")
    chunk_index: int = Field(..., description="Chunk index within document")
    similarity_score: float = Field(..., description="Similarity score to the query")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata") 