import secrets
import string
import json
import os
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
import time

try:
    from backend.models.api_models import APIKey, KnowledgeBase
    from backend.config import settings
except ImportError:
    from models.api_models import APIKey, KnowledgeBase
    from config import settings

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for managing API keys and knowledge bases"""

    def __init__(self):
        self.storage_path = "data/api_keys.json"
        self.kb_storage_path = "data/knowledge_bases.json"
        self._ensure_storage_files()

        # Cache for API key validation to improve performance
        self._api_key_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._last_cache_update = 0

    def _ensure_storage_files(self):
        """Ensure storage files exist"""
        os.makedirs("data", exist_ok=True)

        if not os.path.exists(self.storage_path):
            with open(self.storage_path, 'w') as f:
                json.dump({}, f)

        if not os.path.exists(self.kb_storage_path):
            with open(self.kb_storage_path, 'w') as f:
                json.dump({}, f)

    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        alphabet = string.ascii_letters + string.digits
        key = 'iai_' + ''.join(secrets.choice(alphabet) for _ in range(32))
        return key

    async def create_knowledge_base(self, name: str, description: Optional[str] = None) -> Tuple[KnowledgeBase, APIKey]:
        """Create a new knowledge base and generate an API key"""
        try:
            kb = KnowledgeBase(
                name=name,
                description=description
            )

            api_key = APIKey(
                key=self.generate_api_key(),
                knowledge_base_id=kb.id,
                name=f"Default key for {name}"
            )

            # Save to storage
            await self._save_knowledge_base(kb)
            await self._save_api_key(api_key)

            logger.info(f"Created knowledge base {kb.id} with API key")
            return kb, api_key

        except Exception as e:
            logger.error(f"Error creating knowledge base: {str(e)}")
            raise

    def _should_refresh_cache(self) -> bool:
        """Check if cache should be refreshed"""
        return time.time() - self._last_cache_update > self._cache_ttl

    def _refresh_cache(self):
        """Refresh the API key cache"""
        try:
            with open(self.storage_path, 'r') as f:
                api_keys = json.load(f)

            self._api_key_cache = api_keys.copy()
            self._last_cache_update = time.time()

        except Exception as e:
            logger.error(f"Error refreshing cache: {str(e)}")

    async def validate_api_key(self, api_key: str, count_usage: bool = True) -> Optional[APIKey]:
        """Validate an API key and return its details"""
        try:
            if not count_usage:
                if self._should_refresh_cache():
                    self._refresh_cache()

                if api_key in self._api_key_cache:
                    key_data = self._api_key_cache[api_key]
                    if key_data.get('is_active', True):
                        return APIKey(**key_data)
                return None

            with open(self.storage_path, 'r') as f:
                api_keys = json.load(f)

            if api_key in api_keys:
                key_data = api_keys[api_key]

                # Check if key is active
                if not key_data.get('is_active', True):
                    return None

                key_data['last_used'] = datetime.now().isoformat()
                key_data['usage_count'] = key_data.get('usage_count', 0) + 1

                # Save updated data
                with open(self.storage_path, 'w') as f:
                    json.dump(api_keys, f, indent=2)

                # Update cache
                self._api_key_cache[api_key] = key_data

                return APIKey(**key_data)

            return None

        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return None

    async def test_api_key(self, api_key: str) -> bool:
        """Test if an API key is valid without counting usage"""
        try:
            # Use cache for faster validation
            if self._should_refresh_cache():
                self._refresh_cache()

            if api_key in self._api_key_cache:
                key_data = self._api_key_cache[api_key]
                return key_data.get('is_active', True)

            return False

        except Exception as e:
            logger.error(f"Error testing API key: {str(e)}")
            return False

    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Get a knowledge base by ID"""
        try:
            with open(self.kb_storage_path, 'r') as f:
                knowledge_bases = json.load(f)

            if kb_id in knowledge_bases:
                return KnowledgeBase(**knowledge_bases[kb_id])

            return None

        except Exception as e:
            logger.error(f"Error getting knowledge base: {str(e)}")
            return None

    async def update_knowledge_base_stats(self, kb_id: str, document_ids: List[str], total_chunks: int):
        """Update knowledge base statistics"""
        try:
            with open(self.kb_storage_path, 'r') as f:
                knowledge_bases = json.load(f)

            if kb_id in knowledge_bases:
                kb_data = knowledge_bases[kb_id]
                kb_data['document_ids'] = document_ids
                kb_data['total_documents'] = len(document_ids)
                kb_data['total_chunks'] = total_chunks
                kb_data['updated_at'] = datetime.now().isoformat()

                with open(self.kb_storage_path, 'w') as f:
                    json.dump(knowledge_bases, f, indent=2)

                logger.info(f"Updated knowledge base {kb_id} stats")

        except Exception as e:
            logger.error(f"Error updating knowledge base stats: {str(e)}")
            raise

    async def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key has exceeded rate limit"""
        try:
            # TODO: Implement rate limiting logic
            return True

        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False

    async def list_api_keys(self, knowledge_base_id: Optional[str] = None) -> List[APIKey]:
        """List all API keys, optionally filtered by knowledge base"""
        try:
            with open(self.storage_path, 'r') as f:
                api_keys = json.load(f)

            keys = []
            for key_data in api_keys.values():
                if knowledge_base_id is None or key_data.get('knowledge_base_id') == knowledge_base_id:
                    keys.append(APIKey(**key_data))

            return keys

        except Exception as e:
            logger.error(f"Error listing API keys: {str(e)}")
            return []

    async def list_knowledge_bases(self) -> List[KnowledgeBase]:
        """List all knowledge bases"""
        try:
            with open(self.kb_storage_path, 'r') as f:
                knowledge_bases = json.load(f)

            return [KnowledgeBase(**kb_data) for kb_data in knowledge_bases.values()]

        except Exception as e:
            logger.error(f"Error listing knowledge bases: {str(e)}")
            return []

    async def deactivate_api_key(self, api_key: str):
        """Deactivate an API key"""
        try:
            with open(self.storage_path, 'r') as f:
                api_keys = json.load(f)

            if api_key in api_keys:
                api_keys[api_key]['is_active'] = False

                with open(self.storage_path, 'w') as f:
                    json.dump(api_keys, f, indent=2)

                logger.info(f"Deactivated API key {api_key}")

        except Exception as e:
            logger.error(f"Error deactivating API key: {str(e)}")
            raise

    async def _save_api_key(self, api_key: APIKey):
        """Save an API key to storage"""
        try:
            with open(self.storage_path, 'r') as f:
                api_keys = json.load(f)

            api_keys[api_key.key] = api_key.model_dump(mode='json')

            with open(self.storage_path, 'w') as f:
                json.dump(api_keys, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving API key: {str(e)}")
            raise

    async def _save_knowledge_base(self, kb: KnowledgeBase):
        """Save a knowledge base to storage"""
        try:
            with open(self.kb_storage_path, 'r') as f:
                knowledge_bases = json.load(f)

            knowledge_bases[kb.id] = kb.model_dump(mode='json')

            with open(self.kb_storage_path, 'w') as f:
                json.dump(knowledge_bases, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving knowledge base: {str(e)}")
            raise

    async def get_api_key_by_kb_id(self, kb_id: str) -> Optional[APIKey]:
        """Get the first active API key for a knowledge base"""
        try:
            keys = await self.list_api_keys(kb_id)
            for key in keys:
                if key.is_active:
                    return key
            return None
        except Exception as e:
            logger.error(
                f"Error getting API key by knowledge base ID: {str(e)}")
            return None
