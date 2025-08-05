import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload

try:
    from backend.models.chat_models import ChatMessage, MessageRole
    from backend.models.database_models import Conversation, ConversationMessage
    from backend.services.database_service import database_service
except ImportError:
    from models.chat_models import ChatMessage, MessageRole
    from models.database_models import Conversation, ConversationMessage
    from services.database_service import database_service

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation history and context using PostgreSQL"""

    def __init__(self):
        self.max_conversation_length = 20
        self.conversation_ttl_hours = 24

    async def add_message(self, session_id: str, message: ChatMessage,
                          knowledge_base_id: Optional[str] = None,
                          api_key: Optional[str] = None) -> None:
        """Add a message to the conversation history"""
        try:
            async with database_service.get_session() as session:
                conversation = await self._get_or_create_conversation(
                    session, session_id, knowledge_base_id, api_key
                )

                new_message = ConversationMessage(
                    conversation_id=conversation.id,
                    role=message.role.value,
                    content=message.content
                )
                session.add(new_message)

                await self._cleanup_conversation_messages(session, conversation.id)

                conversation.updated_at = datetime.now(timezone.utc)

                logger.info(f"Added message to conversation {session_id}")

        except Exception as e:
            logger.error(f"Error adding message to conversation: {str(e)}")
            raise

    async def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(Conversation)
                    .options(selectinload(Conversation.messages))
                    .where(Conversation.session_id == session_id)
                )
                conversation = result.scalar_one_or_none()

                if not conversation:
                    return []

                # Check if conversation has expired
                if self._is_conversation_expired(conversation):
                    await self.delete_conversation(session_id)
                    return []

                messages = []
                for msg in sorted(conversation.messages, key=lambda x: x.created_at):
                    messages.append({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat()
                    })

                return messages

        except Exception as e:
            logger.error(f"Error getting conversation {session_id}: {str(e)}")
            return []

    async def get_conversation_context(self, session_id: str, max_messages: int = 10) -> str:
        """Get formatted conversation context for RAG"""
        try:
            messages = await self.get_conversation(session_id)

            if not messages:
                return ""

            recent_messages = messages[-max_messages:] if len(
                messages) > max_messages else messages
            context_parts = []
            for msg in recent_messages:
                role = "Human" if msg["role"] == "user" else "Assistant"
                context_parts.append(f"{role}: {msg['content']}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return ""

    async def delete_conversation(self, session_id: str) -> None:
        """Delete a conversation session"""
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(Conversation).where(
                        Conversation.session_id == session_id)
                )
                conversation = result.scalar_one_or_none()

                if conversation:
                    # Cascading delete will remove messages
                    await session.delete(conversation)
                    logger.info(f"Deleted conversation {session_id}")

        except Exception as e:
            logger.error(f"Error deleting conversation {session_id}: {str(e)}")

    async def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations and return count of deleted conversations"""
        try:
            expired_threshold = datetime.now(timezone.utc) - timedelta(hours=self.conversation_ttl_hours)

            async with database_service.get_session() as session:
                # Find expired conversations
                result = await session.execute(
                    select(Conversation).where(
                        Conversation.expires_at < datetime.now(timezone.utc)
                    )
                )
                expired_conversations = result.scalars().all()

                count = len(expired_conversations)

                if count > 0:
                    await session.execute(
                        delete(Conversation).where(
                            Conversation.expires_at < datetime.now(timezone.utc)
                        )
                    )
                    logger.info(f"Cleaned up {count} expired conversations")

                return count

        except Exception as e:
            logger.error(f"Error cleaning up conversations: {str(e)}")
            return 0

    async def get_conversation_stats(self) -> Dict[str, int]:
        """Get conversation statistics"""
        try:
            async with database_service.get_session() as session:
                conv_result = await session.execute(
                    select(Conversation.id)
                )
                total_conversations = len(conv_result.scalars().all())

                msg_result = await session.execute(
                    select(ConversationMessage.id)
                )
                total_messages = len(msg_result.scalars().all())

                active_result = await session.execute(
                    select(Conversation.id).where(
                        Conversation.expires_at > datetime.now(timezone.utc)
                    )
                )
                active_conversations = len(active_result.scalars().all())

                return {
                    "total_conversations": total_conversations,
                    "active_conversations": active_conversations,
                    "total_messages": total_messages
                }

        except Exception as e:
            logger.error(f"Error getting conversation stats: {str(e)}")
            return {"total_conversations": 0, "active_conversations": 0, "total_messages": 0}

    async def _get_or_create_conversation(self, session, session_id: str,
                                          knowledge_base_id: Optional[str] = None,
                                          api_key: Optional[str] = None) -> Conversation:
        """Get existing conversation or create new one"""
        result = await session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conversation = result.scalar_one_or_none()

        if conversation:
            return conversation

        conversation = Conversation(
            session_id=session_id,
            knowledge_base_id=knowledge_base_id,
            api_key=api_key,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=self.conversation_ttl_hours)
        )
        session.add(conversation)
        await session.flush()
        return conversation

    async def _cleanup_conversation_messages(self, session, conversation_id: str) -> None:
        """Remove old messages if conversation exceeds max length"""
        result = await session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
        )
        messages = result.scalars().all()

        if len(messages) > self.max_conversation_length:
            messages_to_delete = messages[self.max_conversation_length:]
            for msg in messages_to_delete:
                await session.delete(msg)

    def _is_conversation_expired(self, conversation: Conversation) -> bool:
        """Check if a conversation has expired"""
        return datetime.now(timezone.utc) > conversation.expires_at


conversation_service = ConversationService()
