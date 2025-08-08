import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, update

try:
    from backend.models.database_models import AgentSettings, KnowledgeBase
    from backend.services.database_service import database_service
except ImportError:
    from models.database_models import AgentSettings, KnowledgeBase
    from services.database_service import database_service

logger = logging.getLogger(__name__)


class AgentSettingsService:
    """Service for per-agent settings management"""

    async def get_settings(self, knowledge_base_id: str) -> Optional[AgentSettings]:
        async with database_service.get_session() as session:
            result = await session.execute(
                select(AgentSettings).where(AgentSettings.knowledge_base_id == knowledge_base_id)
            )
            return result.scalar_one_or_none()

    async def upsert_settings(self, knowledge_base_id: str, agent_type: str, config: Dict[str, Any]) -> AgentSettings:
        async with database_service.get_session() as session:
            # Ensure KB exists
            kb_result = await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
            )
            kb = kb_result.scalar_one_or_none()
            if not kb:
                raise ValueError("Knowledge base not found")

            result = await session.execute(
                select(AgentSettings).where(AgentSettings.knowledge_base_id == knowledge_base_id)
            )
            settings_row = result.scalar_one_or_none()

            if settings_row:
                await session.execute(
                    update(AgentSettings)
                    .where(AgentSettings.id == settings_row.id)
                    .values(
                        agent_type=agent_type,
                        config=config,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                await session.flush()
                settings_row.agent_type = agent_type
                settings_row.config = config
                return settings_row
            else:
                new_row = AgentSettings(
                    knowledge_base_id=knowledge_base_id,
                    agent_type=agent_type,
                    config=config,
                )
                session.add(new_row)
                await session.flush()
                return new_row


agent_settings_service = AgentSettingsService()


