from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime
from typing import Optional, List

Base = declarative_base()


class KnowledgeBase(Base):
    """Knowledge base model"""
    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    agent_type = Column(String(50), nullable=False, default="data_processing")
    total_documents = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    documents = relationship(
        "Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    document_chunks = relationship(
        "DocumentChunk", back_populates="knowledge_base", cascade="all, delete-orphan")
    api_keys = relationship(
        "APIKey", back_populates="knowledge_base", cascade="all, delete-orphan")


class Document(Base):
    """Document model"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey(
        "knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    file_size = Column(Integer)
    text_length = Column(Integer)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Document chunk model for RAG with embeddings"""
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey(
        "documents.id", ondelete="CASCADE"), nullable=False)
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey(
        "knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384))
    chunk_metadata = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")
    knowledge_base = relationship(
        "KnowledgeBase", back_populates="document_chunks")


class APIKey(Base):
    """API key model"""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey(
        "knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    rate_limit = Column(Integer, default=100)
    last_used = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="api_keys")
    conversations = relationship("Conversation", back_populates="api_key_obj")


class Conversation(Base):
    """Conversation model for tracking chat sessions"""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey(
        "knowledge_bases.id", ondelete="CASCADE"))
    api_key = Column(String(255), ForeignKey(
        "api_keys.key", ondelete="CASCADE"))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    api_key_obj = relationship("APIKey", back_populates="conversations")
    messages = relationship(
        "ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base):
    """Conversation message model"""
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey(
        "conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Add constraint for role values
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')", name='valid_role'),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
