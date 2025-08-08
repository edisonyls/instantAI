import secrets
import string
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

try:
    from backend.models.api_models import APIKey as APIKeyModel, KnowledgeBase as KnowledgeBaseModel
    from backend.models.database_models import APIKey, KnowledgeBase
    from backend.services.database_service import database_service
    from backend.config import settings
except ImportError:
    from models.api_models import APIKey as APIKeyModel, KnowledgeBase as KnowledgeBaseModel
    from models.database_models import APIKey, KnowledgeBase
    from services.database_service import database_service
    from config import settings

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for managing API keys and knowledge bases using PostgreSQL"""

    def __init__(self):
        # Cache for API key validation to improve performance
        self._api_key_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._last_cache_update = 0

    def _generate_api_key(self) -> str:
        """Generate a new API key"""
        # Generate a strong random key
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(32))
        return f"iai_{key}"

    async def create_api_key(self, knowledge_base_id: str, name: str) -> APIKeyModel:
        """Create a new API key for a knowledge base"""
        try:
            async with database_service.get_session() as session:
                # Verify knowledge base exists
                kb_result = await session.execute(
                    select(KnowledgeBase).where(
                        KnowledgeBase.id == knowledge_base_id)
                )
                kb = kb_result.scalar_one_or_none()
                if not kb:
                    raise ValueError(
                        f"Knowledge base {knowledge_base_id} not found")

                # Generate unique API key
                key = self._generate_api_key()

                # Ensure key is unique
                while True:
                    existing_result = await session.execute(
                        select(APIKey).where(APIKey.key == key)
                    )
                    if not existing_result.scalar_one_or_none():
                        break
                    key = self._generate_api_key()

                # Create new API key
                api_key = APIKey(
                    key=key,
                    knowledge_base_id=knowledge_base_id,
                    name=name,
                    is_active=True,
                    usage_count=0,
                    rate_limit=100
                )
                session.add(api_key)
                await session.flush()

                # Convert to Pydantic model
                api_key_model = APIKeyModel(
                    key=api_key.key,
                    knowledge_base_id=str(api_key.knowledge_base_id),
                    name=api_key.name,
                    created_at=api_key.created_at,
                    last_used=api_key.last_used,
                    usage_count=api_key.usage_count,
                    is_active=api_key.is_active
                )

                logger.info(
                    f"Created API key {key} for knowledge base {knowledge_base_id}")
                return api_key_model

        except Exception as e:
            logger.error(f"Error creating API key: {str(e)}")
            raise

    async def create_knowledge_base(self, name: str, description: Optional[str] = None, agent_type: str = "data_processing") -> KnowledgeBaseModel:
        """Create a new knowledge base"""
        try:
            async with database_service.get_session() as session:
                kb = KnowledgeBase(
                    name=name,
                    description=description,
                    agent_type=agent_type,
                    total_documents=0,
                    total_chunks=0
                )
                session.add(kb)
                await session.flush()

                # Convert to Pydantic model
                kb_model = KnowledgeBaseModel(
                    id=str(kb.id),
                    name=kb.name,
                    description=kb.description,
                    agent_type=kb.agent_type,
                    document_ids=[],
                    total_documents=kb.total_documents,
                    total_chunks=kb.total_chunks,
                    created_at=kb.created_at,
                    updated_at=kb.updated_at
                )

                logger.info(f"Created knowledge base {kb.id}")
                return kb_model

        except Exception as e:
            logger.error(f"Error creating knowledge base: {str(e)}")
            raise

    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBaseModel]:
        """Get a knowledge base by ID"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(KnowledgeBase)
                    .options(selectinload(KnowledgeBase.documents))
                    .where(KnowledgeBase.id == kb_id)
                )
                kb = result.scalar_one_or_none()

                if not kb:
                    return None

                # Get document IDs
                document_ids = [str(doc.id) for doc in kb.documents]

                return KnowledgeBaseModel(
                    id=str(kb.id),
                    name=kb.name,
                    description=kb.description,
                    agent_type=kb.agent_type,
                    document_ids=document_ids,
                    total_documents=kb.total_documents,
                    total_chunks=kb.total_chunks,
                    created_at=kb.created_at,
                    updated_at=kb.updated_at
                )

        except Exception as e:
            logger.error(f"Error getting knowledge base: {str(e)}")
            return None

    async def validate_api_key(self, api_key: str) -> Optional[Tuple[str, str]]:
        """Validate an API key and return (knowledge_base_id, api_key) if valid"""
        try:
            # Check cache first
            current_time = datetime.now().timestamp()
            if (api_key in self._api_key_cache and
                    current_time - self._last_cache_update < self._cache_ttl):
                cached_data = self._api_key_cache[api_key]
                if cached_data and cached_data.get('is_active', False):
                    return cached_data['knowledge_base_id'], api_key

            async with database_service.get_session() as session:
                result = await session.execute(
                    select(APIKey).where(
                        and_(APIKey.key == api_key, APIKey.is_active == True)
                    )
                )
                key_obj = result.scalar_one_or_none()

                if not key_obj:
                    # Cache negative result
                    self._api_key_cache[api_key] = None
                    return None

                # Update last used timestamp and usage count
                await session.execute(
                    update(APIKey)
                    .where(APIKey.key == api_key)
                    .values(
                        last_used=datetime.now(timezone.utc),
                        usage_count=APIKey.usage_count + 1
                    )
                )

                # Cache positive result
                self._api_key_cache[api_key] = {
                    'knowledge_base_id': str(key_obj.knowledge_base_id),
                    'is_active': key_obj.is_active
                }
                self._last_cache_update = current_time

                return str(key_obj.knowledge_base_id), api_key

        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return None

    async def test_api_key(self, api_key: str) -> Optional[Tuple[str, str]]:
        """Test an API key without incrementing usage count"""
        try:
            # Check cache first
            current_time = datetime.now().timestamp()
            if (api_key in self._api_key_cache and
                    current_time - self._last_cache_update < self._cache_ttl):
                cached_data = self._api_key_cache[api_key]
                if cached_data and cached_data.get('is_active', False):
                    return cached_data['knowledge_base_id'], api_key

            async with database_service.get_session() as session:
                result = await session.execute(
                    select(APIKey).where(
                        and_(APIKey.key == api_key, APIKey.is_active == True)
                    )
                )
                key_obj = result.scalar_one_or_none()

                if not key_obj:
                    # Cache negative result
                    self._api_key_cache[api_key] = None
                    return None

                # Cache positive result but don't update usage
                self._api_key_cache[api_key] = {
                    'knowledge_base_id': str(key_obj.knowledge_base_id),
                    'is_active': key_obj.is_active
                }
                self._last_cache_update = current_time

                return str(key_obj.knowledge_base_id), api_key

        except Exception as e:
            logger.error(f"Error testing API key: {str(e)}")
            return None

    async def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key is within rate limits"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(APIKey).where(APIKey.key == api_key)
                )
                key_obj = result.scalar_one_or_none()

                if not key_obj:
                    return False

                # Simple rate limiting based on usage count
                # In production, you might want more sophisticated rate limiting
                return key_obj.usage_count < key_obj.rate_limit

        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False

    async def list_api_keys(self, knowledge_base_id: Optional[str] = None) -> List[APIKeyModel]:
        """List all API keys, optionally filtered by knowledge base"""
        try:
            async with database_service.get_session() as session:
                query = select(APIKey)
                if knowledge_base_id:
                    query = query.where(
                        APIKey.knowledge_base_id == knowledge_base_id)

                result = await session.execute(query)
                api_keys = result.scalars().all()

                return [
                    APIKeyModel(
                        key=key.key,
                        knowledge_base_id=str(key.knowledge_base_id),
                        name=key.name,
                        created_at=key.created_at,
                        last_used=key.last_used,
                        usage_count=key.usage_count,
                        is_active=key.is_active
                    )
                    for key in api_keys
                ]

        except Exception as e:
            logger.error(f"Error listing API keys: {str(e)}")
            return []

    async def list_knowledge_bases(self) -> List[KnowledgeBaseModel]:
        """List all knowledge bases"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(KnowledgeBase).options(
                        selectinload(KnowledgeBase.documents))
                )
                kbs = result.scalars().all()

                return [
                    KnowledgeBaseModel(
                        id=str(kb.id),
                        name=kb.name,
                        description=kb.description,
                        agent_type=kb.agent_type,
                        document_ids=[str(doc.id) for doc in kb.documents],
                        total_documents=kb.total_documents,
                        total_chunks=kb.total_chunks,
                        created_at=kb.created_at,
                        updated_at=kb.updated_at
                    )
                    for kb in kbs
                ]

        except Exception as e:
            logger.error(f"Error listing knowledge bases: {str(e)}")
            return []

    async def delete_api_key(self, api_key: str) -> bool:
        """Delete an API key"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(APIKey).where(APIKey.key == api_key)
                )
                key_obj = result.scalar_one_or_none()

                if not key_obj:
                    return False

                await session.delete(key_obj)

                # Remove from cache
                self._api_key_cache.pop(api_key, None)

                logger.info(f"Deleted API key {api_key}")
                return True

        except Exception as e:
            logger.error(f"Error deleting API key: {str(e)}")
            return False

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """Delete a knowledge base and all associated data"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
                )
                kb = result.scalar_one_or_none()

                if not kb:
                    return False

                # Cascading deletes will handle related records
                await session.delete(kb)

                logger.info(f"Deleted knowledge base {kb_id}")
                return True

        except Exception as e:
            logger.error(f"Error deleting knowledge base: {str(e)}")
            return False


api_key_service = APIKeyService()
