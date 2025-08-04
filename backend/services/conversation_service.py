import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import os
from pathlib import Path

try:
    from backend.models.chat_models import ChatMessage, MessageRole
except ImportError:
    from models.chat_models import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation history and context"""

    def __init__(self):
        self.conversations_dir = Path("data/conversations")
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        self.max_conversation_length = 20
        self.conversation_ttl_hours = 24

    def _get_conversation_file(self, session_id: str) -> Path:
        """Get the file path for a conversation session"""
        return self.conversations_dir / f"{session_id}.json"

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Add a message to the conversation history"""
        try:
            conversation = await self.get_conversation(session_id)

            # Add the new message
            conversation.append({
                "role": message.role.value,
                "content": message.content,
                "timestamp": datetime.now().isoformat()
            })

            # Keep only the last N messages to prevent context overflow
            if len(conversation) > self.max_conversation_length:
                conversation = conversation[-self.max_conversation_length:]

            # Save the conversation
            await self._save_conversation(session_id, conversation)

            logger.info(f"Added message to conversation {session_id}")

        except Exception as e:
            logger.error(f"Error adding message to conversation: {str(e)}")
            raise

    async def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the conversation history for a session"""
        try:
            conversation_file = self._get_conversation_file(session_id)

            if not conversation_file.exists():
                return []

            # Check if conversation is expired
            if await self._is_conversation_expired(conversation_file):
                await self.delete_conversation(session_id)
                return []

            with open(conversation_file, 'r', encoding='utf-8') as f:
                conversation = json.load(f)

            return conversation

        except Exception as e:
            logger.error(f"Error getting conversation {session_id}: {str(e)}")
            return []

    async def get_conversation_context(self, session_id: str, max_messages: int = 10) -> str:
        """Get formatted conversation context for the AI prompt"""
        try:
            conversation = await self.get_conversation(session_id)

            if not conversation:
                return ""

            # Take the last N messages for context
            recent_messages = conversation[-max_messages:]

            context_lines = []
            for msg in recent_messages:
                role = msg["role"]
                content = msg["content"]
                context_lines.append(f"{role.capitalize()}: {content}")

            return "\n".join(context_lines)

        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return ""

    async def _save_conversation(self, session_id: str, conversation: List[Dict[str, Any]]) -> None:
        """Save conversation to file"""
        try:
            conversation_file = self._get_conversation_file(session_id)

            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            raise

    async def _is_conversation_expired(self, conversation_file: Path) -> bool:
        """Check if a conversation file has expired"""
        try:
            stat = conversation_file.stat()
            file_age = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
            return file_age > timedelta(hours=self.conversation_ttl_hours)
        except Exception:
            return False

    async def delete_conversation(self, session_id: str) -> None:
        """Delete a conversation session"""
        try:
            conversation_file = self._get_conversation_file(session_id)
            if conversation_file.exists():
                conversation_file.unlink()
                logger.info(f"Deleted conversation {session_id}")
        except Exception as e:
            logger.error(f"Error deleting conversation {session_id}: {str(e)}")

    async def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations and return count of deleted files"""
        try:
            deleted_count = 0

            for conversation_file in self.conversations_dir.glob("*.json"):
                if await self._is_conversation_expired(conversation_file):
                    conversation_file.unlink()
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} expired conversations")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired conversations: {str(e)}")
            return 0

    async def get_conversation_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics about a conversation"""
        try:
            conversation = await self.get_conversation(session_id)

            if not conversation:
                return {
                    "message_count": 0,
                    "user_messages": 0,
                    "assistant_messages": 0,
                    "first_message": None,
                    "last_message": None
                }

            user_messages = sum(
                1 for msg in conversation if msg["role"] == "user")
            assistant_messages = sum(
                1 for msg in conversation if msg["role"] == "assistant")

            return {
                "message_count": len(conversation),
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "first_message": conversation[0]["timestamp"] if conversation else None,
                "last_message": conversation[-1]["timestamp"] if conversation else None
            }

        except Exception as e:
            logger.error(f"Error getting conversation stats: {str(e)}")
            return {}
