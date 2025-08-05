import logging
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from sentence_transformers import SentenceTransformer
import numpy as np
from sqlalchemy import select, text, update, and_
from sqlalchemy.orm import selectinload

try:
    from backend.config import settings
    from backend.models.chat_models import ContextChunk, DocumentInfo
    from backend.models.database_models import (
        Document, DocumentChunk, KnowledgeBase
    )
    from backend.services.document_processor import DocumentProcessor
    from backend.services.database_service import database_service
except ImportError:
    from config import settings
    from models.chat_models import ContextChunk, DocumentInfo
    from models.database_models import (
        Document, DocumentChunk, KnowledgeBase
    )
    from services.document_processor import DocumentProcessor
    from services.database_service import database_service

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation using PostgreSQL and pgvector"""

    def __init__(self):
        self.embedding_model = None
        self.document_processor = DocumentProcessor()
        self.is_initialized = False

    async def initialize(self):
        """Initialize the RAG service with embedding model"""
        try:
            self.embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL)

            await database_service.initialize()

            self.is_initialized = True
            logger.info("PostgreSQL RAG service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing RAG service: {str(e)}")
            raise

    async def process_document(self, text: str, filename: str, knowledge_base_id: str, file_size: Optional[int] = None) -> str:
        """Process a document by creating embeddings and storing in PostgreSQL"""
        if not self.is_initialized:
            await self.initialize()

        try:
            async with database_service.get_session() as session:
                document = Document(
                    knowledge_base_id=knowledge_base_id,
                    filename=filename,
                    file_size=file_size,
                    text_length=len(text)
                )
                session.add(document)
                await session.flush()

                document_id = str(document.id)

                # Preprocess text
                processed_text = self.document_processor.preprocess_text(text)

                # Chunk the text
                chunks = self.document_processor.chunk_text(processed_text)

                # Create embeddings for each chunk
                chunk_texts = [chunk['text'] for chunk in chunks]
                embeddings = self.embedding_model.encode(chunk_texts)

                # Store chunks with embeddings
                chunk_count = 0
                for i, chunk in enumerate(chunks):
                    # Prepare metadata
                    metadata = {
                        'filename': filename,
                        'start_char': chunk['start_char'],
                        'end_char': chunk['end_char'],
                        'length': chunk['length']
                    }
                    
                    chunk_record = DocumentChunk(
                        document_id=document.id,
                        knowledge_base_id=knowledge_base_id,
                        chunk_index=chunk['chunk_index'],
                        content=chunk['text'],
                        embedding=embeddings[i].tolist(),
                        chunk_metadata=str(metadata)
                    )
                    session.add(chunk_record)
                    chunk_count += 1

                document.chunk_count = chunk_count

                await session.execute(
                    update(KnowledgeBase)
                    .where(KnowledgeBase.id == knowledge_base_id)
                    .values(
                        total_documents=KnowledgeBase.total_documents + 1,
                        total_chunks=KnowledgeBase.total_chunks + chunk_count,
                        updated_at=datetime.now(timezone.utc)
                    )
                )

                logger.info(
                    f"Successfully processed document {filename} with {len(chunks)} chunks")
                return document_id

        except Exception as e:
            logger.error(f"Error processing document {filename}: {str(e)}")
            raise

    async def retrieve_context(self, query: str, knowledge_base_id: str,
                               document_id: Optional[str] = None,
                               max_chunks: int = None) -> List[ContextChunk]:
        """Retrieve relevant context chunks using vector similarity search"""
        if not self.is_initialized:
            await self.initialize()

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]

            max_chunks = max_chunks or settings.MAX_RETRIEVED_CHUNKS
            similarity_threshold = settings.SIMILARITY_THRESHOLD

            async with database_service.get_session() as session:
                # Convert embedding to proper format for PostgreSQL vector
                embedding_list = query_embedding.tolist()
                
                # Use a simpler approach with direct SQL execution
                # First, let's convert the list to a proper vector format string
                vector_str = '[' + ','.join(map(str, embedding_list)) + ']'
                
                # Build the query using string formatting (less ideal but working approach)
                base_query = f"""
                SELECT dc.id, dc.document_id, dc.knowledge_base_id, dc.chunk_index, 
                       dc.content, dc.chunk_metadata, dc.created_at,
                       d.filename,
                       1 - (dc.embedding <=> '{vector_str}'::vector) as similarity
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.knowledge_base_id = '{knowledge_base_id}'
                """

                if document_id:
                    base_query += f" AND dc.document_id = '{document_id}'"

                # Add similarity threshold and ordering
                base_query += f"""
                AND (1 - (dc.embedding <=> '{vector_str}'::vector)) > {similarity_threshold}
                ORDER BY similarity DESC
                LIMIT {max_chunks}
                """

                # Execute the query
                result = await session.execute(text(base_query))
                rows = result.fetchall()

                context_chunks = []
                for row in rows:
                    # Parse metadata if available
                    metadata = {'filename': row.filename}
                    if row.chunk_metadata:
                        try:
                            import ast
                            parsed_metadata = ast.literal_eval(row.chunk_metadata)
                            metadata.update(parsed_metadata)
                        except:
                            pass
                    
                    context_chunk = ContextChunk(
                        content=row.content,
                        document_id=str(row.document_id),
                        chunk_index=row.chunk_index,
                        similarity_score=float(row.similarity),
                        metadata=metadata
                    )
                    context_chunks.append(context_chunk)

                logger.info(
                    f"Retrieved {len(context_chunks)} relevant chunks for query")
                return context_chunks

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(Document).where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()

                if not document:
                    return False

                knowledge_base_id = document.knowledge_base_id
                chunk_count = document.chunk_count

                await session.delete(document)

                await session.execute(
                    update(KnowledgeBase)
                    .where(KnowledgeBase.id == knowledge_base_id)
                    .values(
                        total_documents=KnowledgeBase.total_documents - 1,
                        total_chunks=KnowledgeBase.total_chunks - chunk_count,
                        updated_at=datetime.now(timezone.utc)
                    )
                )

                logger.info(f"Deleted document {document_id}")
                return True

        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False

    async def get_document_info(self, document_id: str) -> Optional[DocumentInfo]:
        """Get document information"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(Document)
                    .options(selectinload(Document.chunks))
                    .where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()

                if not document:
                    return None

                return DocumentInfo(
                    id=str(document.id),
                    filename=document.filename,
                    knowledge_base_id=str(document.knowledge_base_id),
                    chunk_count=document.chunk_count,
                    file_size=document.file_size,
                    text_length=document.text_length,
                    created_at=document.created_at,
                    updated_at=document.updated_at
                )

        except Exception as e:
            logger.error(f"Error getting document info: {str(e)}")
            return None

    async def list_documents(self, knowledge_base_id: str) -> List[DocumentInfo]:
        """List all documents in a knowledge base"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(Document).where(
                        Document.knowledge_base_id == knowledge_base_id)
                )
                documents = result.scalars().all()

                return [
                    DocumentInfo(
                        id=str(doc.id),
                        filename=doc.filename,
                        knowledge_base_id=str(doc.knowledge_base_id),
                        chunk_count=doc.chunk_count,
                        file_size=doc.file_size,
                        text_length=doc.text_length,
                        created_at=doc.created_at,
                        updated_at=doc.updated_at
                    )
                    for doc in documents
                ]

        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []

    async def get_knowledge_base_stats(self, knowledge_base_id: str) -> Dict[str, int]:
        """Get statistics for a knowledge base"""
        try:
            async with database_service.get_session() as session:
                kb_result = await session.execute(
                    select(KnowledgeBase).where(
                        KnowledgeBase.id == knowledge_base_id)
                )
                kb = kb_result.scalar_one_or_none()

                if not kb:
                    return {"total_documents": 0, "total_chunks": 0}

                return {
                    "total_documents": kb.total_documents,
                    "total_chunks": kb.total_chunks
                }

        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {str(e)}")
            return {"total_documents": 0, "total_chunks": 0}

    async def cleanup_knowledge_base(self, knowledge_base_id: str) -> bool:
        """Remove all documents and chunks from a knowledge base"""
        try:
            async with database_service.get_session() as session:
                documents_result = await session.execute(
                    select(Document).where(
                        Document.knowledge_base_id == knowledge_base_id)
                )
                documents = documents_result.scalars().all()

                for document in documents:
                    await session.delete(document)

                await session.execute(
                    update(KnowledgeBase)
                    .where(KnowledgeBase.id == knowledge_base_id)
                    .values(
                        total_documents=0,
                        total_chunks=0,
                        updated_at=datetime.now(timezone.utc)
                    )
                )

                logger.info(f"Cleaned up knowledge base {knowledge_base_id}")
                return True

        except Exception as e:
            logger.error(f"Error cleaning up knowledge base: {str(e)}")
            return False


rag_service = RAGService()
