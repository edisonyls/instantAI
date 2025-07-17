import os
import uuid
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import numpy as np

try:
    from backend.config import settings
    from backend.models.chat_models import ContextChunk, DocumentInfo
    from backend.services.document_processor import DocumentProcessor
except ImportError:
    from config import settings
    from models.chat_models import ContextChunk, DocumentInfo
    from services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation using vector embeddings"""

    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.document_processor = DocumentProcessor()
        self.is_initialized = False

    async def initialize(self):
        """Initialize the RAG service with ChromaDB and embedding model"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH,
                settings=ChromaSettings(anonymized_telemetry=False)
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=settings.VECTOR_DB_COLLECTION,
                metadata={"hnsw:space": "cosine"}
            )

            # Initialize embedding model
            self.embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL)

            self.is_initialized = True
            logger.info("RAG service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing RAG service: {str(e)}")
            raise

    async def process_document(self, text: str, filename: str, knowledge_base_id: Optional[str] = None) -> str:
        """ Process a document: chunk it, create embeddings, and store in vector database """
        if not self.is_initialized:
            await self.initialize()

        try:
            document_id = str(uuid.uuid4())

            # Preprocess text
            processed_text = self.document_processor.preprocess_text(text)

            # Chunk the text
            chunks = self.document_processor.chunk_text(processed_text)

            # Create embeddings for each chunk
            chunk_texts = [chunk['text'] for chunk in chunks]
            embeddings = self.embedding_model.encode(chunk_texts)

            # Prepare data for ChromaDB
            ids = [f"{document_id}_{chunk['id']}" for chunk in chunks]
            metadatas = []

            for i, chunk in enumerate(chunks):
                metadata = {
                    'document_id': document_id,
                    'filename': filename,
                    'chunk_index': chunk['chunk_index'],
                    'start_char': chunk['start_char'],
                    'end_char': chunk['end_char'],
                    'length': chunk['length'],
                    'created_at': datetime.now().isoformat()
                }

                if knowledge_base_id:
                    metadata['knowledge_base_id'] = knowledge_base_id
                metadatas.append(metadata)

            # Add to ChromaDB
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=chunk_texts,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(
                f"Successfully processed document {filename} with {len(chunks)} chunks")
            return document_id

        except Exception as e:
            logger.error(f"Error processing document {filename}: {str(e)}")
            raise

    async def retrieve_context(self, query: str, document_id: Optional[str] = None, knowledge_base_id: Optional[str] = None) -> List[ContextChunk]:
        """ Retrieve relevant context chunks for a query """
        if not self.is_initialized:
            await self.initialize()

        try:
            logger.info(
                f"Retrieving context for query: '{query}', document_id: {document_id}, knowledge_base_id: {knowledge_base_id}")

            # Create query embedding
            query_embedding = self.embedding_model.encode([query])

            # Prepare where clause for filtering
            where_clause = None
            if document_id:
                where_clause = {"document_id": document_id}
                logger.info(f"Filtering by document_id: {document_id}")
            elif knowledge_base_id:
                where_clause = {"knowledge_base_id": knowledge_base_id}
                logger.info(
                    f"Filtering by knowledge_base_id: {knowledge_base_id}")

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=settings.MAX_RETRIEVED_CHUNKS,
                where=where_clause
            )

            logger.info(
                f"ChromaDB query results: {len(results.get('documents', [[]])[0])} documents found")

            # Convert results to ContextChunk objects
            context_chunks = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    similarity_score = 1 - distance

                    if similarity_score >= settings.SIMILARITY_THRESHOLD:
                        context_chunks.append(ContextChunk(
                            content=doc,
                            similarity_score=similarity_score,
                            source=metadata['filename'],
                            chunk_id=results['ids'][0][i]
                        ))

            logger.info(
                f"Retrieved {len(context_chunks)} context chunks for query")
            if len(context_chunks) == 0:
                logger.warning(
                    f"No context chunks found for query: '{query}' with filters")
            return context_chunks

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            raise

    async def list_documents(self) -> List[DocumentInfo]:
        """ List all processed documents """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Get all documents from collection
            results = self.collection.get()

            # Group by document_id
            documents_dict = {}
            for i, metadata in enumerate(results['metadatas']):
                doc_id = metadata['document_id']
                if doc_id not in documents_dict:
                    documents_dict[doc_id] = {
                        'id': doc_id,
                        'filename': metadata['filename'],
                        'chunks': 0,
                        'total_length': 0,
                        'created_at': metadata['created_at']
                    }
                documents_dict[doc_id]['chunks'] += 1
                documents_dict[doc_id]['total_length'] += metadata['length']

            # Convert to DocumentInfo objects
            documents = []
            for doc_data in documents_dict.values():
                documents.append(DocumentInfo(
                    id=doc_data['id'],
                    filename=doc_data['filename'],
                    text_length=doc_data['total_length'],
                    chunk_count=doc_data['chunks'],
                    upload_timestamp=datetime.fromisoformat(
                        doc_data['created_at'])
                ))

            return documents

        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise

    async def delete_document(self, document_id: str):
        """ Delete a document and all its chunks from the vector database """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Get all chunks for this document
            results = self.collection.get(where={"document_id": document_id})

            if results['ids']:
                # Delete all chunks
                self.collection.delete(ids=results['ids'])
                logger.info(
                    f"Deleted document {document_id} with {len(results['ids'])} chunks")
            else:
                logger.warning(f"Document {document_id} not found")

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            raise

    async def get_documents_by_knowledge_base(self, knowledge_base_id: str) -> List[DocumentInfo]:
        """ Get all documents associated with a knowledge base """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Get all documents from collection with this knowledge base ID
            results = self.collection.get(
                where={"knowledge_base_id": knowledge_base_id})

            # Group by document_id
            documents_dict = {}
            for i, metadata in enumerate(results['metadatas']):
                doc_id = metadata['document_id']
                if doc_id not in documents_dict:
                    documents_dict[doc_id] = {
                        'id': doc_id,
                        'filename': metadata['filename'],
                        'chunks': 0,
                        'total_length': 0,
                        'created_at': metadata['created_at']
                    }
                documents_dict[doc_id]['chunks'] += 1
                documents_dict[doc_id]['total_length'] += metadata['length']

            # Convert to DocumentInfo objects
            documents = []
            for doc_data in documents_dict.values():
                documents.append(DocumentInfo(
                    id=doc_data['id'],
                    filename=doc_data['filename'],
                    text_length=doc_data['total_length'],
                    chunk_count=doc_data['chunks'],
                    upload_timestamp=datetime.fromisoformat(
                        doc_data['created_at'])
                ))

            return documents

        except Exception as e:
            logger.error(
                f"Error getting documents by knowledge base: {str(e)}")
            raise

    async def get_knowledge_base_stats(self, knowledge_base_id: str) -> Dict[str, Any]:
        """ Get statistics for a knowledge base """
        if not self.is_initialized:
            await self.initialize()

        try:
            results = self.collection.get(
                where={"knowledge_base_id": knowledge_base_id})

            if not results['ids']:
                return {
                    'knowledge_base_id': knowledge_base_id,
                    'total_documents': 0,
                    'total_chunks': 0,
                    'total_length': 0,
                    'document_ids': []
                }

            # Get unique document IDs
            document_ids = list(
                set(metadata['document_id'] for metadata in results['metadatas']))
            total_length = sum(metadata['length']
                               for metadata in results['metadatas'])

            return {
                'knowledge_base_id': knowledge_base_id,
                'total_documents': len(document_ids),
                'total_chunks': len(results['ids']),
                'total_length': total_length,
                'document_ids': document_ids
            }

        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """ Perform health check on the RAG service """
        try:
            if not self.is_initialized:
                return {"status": "not_initialized", "error": "Service not initialized"}

            collection_count = self.collection.count()

            # Check embedding model
            test_embedding = self.embedding_model.encode(["test"])

            return {
                "status": "healthy",
                "collection_count": collection_count,
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dimension": len(test_embedding)
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
