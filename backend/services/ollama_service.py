import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional, Any
import json
from datetime import datetime

try:
    from backend.config import settings
    from backend.models.chat_models import ContextChunk
except ImportError:
    from config import settings
    from models.chat_models import ContextChunk

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for interacting with Ollama local AI models"""

    def __init__(self):
        self.base_url = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL
        self.is_initialized = False
        self.session = None
        self.pull_tasks: Dict[str, asyncio.Task] = {}
        self.pull_status: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize the Ollama service"""
        try:
            self.session = aiohttp.ClientSession()

            await self._check_ollama_connection()

            # Check if model is available
            await self._ensure_model_available()

            self.is_initialized = True
            logger.info(f"Ollama service initialized with model: {self.model}")

        except Exception as e:
            logger.error(f"Error initializing Ollama service: {str(e)}")
            raise

    async def _check_ollama_connection(self):
        """Check if Ollama server is running"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    logger.info("Ollama server is running")
                else:
                    raise Exception(
                        f"Ollama server returned status {response.status}")
        except Exception as e:
            raise Exception(
                f"Cannot connect to Ollama server at {self.base_url}: {str(e)}")

    async def _ensure_model_available(self):
        """Ensure the specified model is available"""
        try:
            # Check if model exists
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    available_models = [model['name']
                                        for model in data.get('models', [])]

                    if self.model not in available_models:
                        logger.info(
                            f"Model {self.model} not found. Available models: {available_models}")
                        logger.info(
                            f"Attempting to pull model {self.model} in background")
                        # Start background pull without blocking
                        await self.start_pull_in_background(self.model)
                    else:
                        logger.info(f"Model {self.model} is available")
                else:
                    raise Exception(
                        f"Failed to check available models: {response.status}")
        except Exception as e:
            raise Exception(f"Error checking model availability: {str(e)}")

    async def start_pull_in_background(self, model_name: str) -> Dict[str, Any]:
        """Start pulling a model in the background and track progress/state."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            installed = await self.get_available_models()
            if model_name in installed:
                status = {
                    "model": model_name,
                    "state": "completed",
                    "message": "Already installed",
                    "percent": 100,
                    "completed": 1,
                    "total": 1,
                }
                self.pull_status[model_name] = status
                return status
        except Exception:
            pass

        # If a task exists and is running, return current status
        task = self.pull_tasks.get(model_name)
        if task and not task.done():
            return self.pull_status.get(model_name, {"model": model_name, "state": "starting"})

        self.pull_status[model_name] = {
            "model": model_name,
            "state": "starting",
            "message": "Starting...",
            "percent": 0,
            "completed": 0,
            "total": None,
        }

        async def _pull_and_track():
            try:
                async with self.session.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                    timeout=aiohttp.ClientTimeout(total=None),
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        self.pull_status[model_name] = {
                            "model": model_name,
                            "state": "error",
                            "message": f"Failed to start pull: {response.status} {text}",
                        }
                        return

                    buffer = b""
                    async for chunk in response.content.iter_chunked(1024):
                        buffer += chunk
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line.decode("utf-8"))
                                status_text = event.get(
                                    "status") or event.get("message") or ""
                                completed = event.get("completed")
                                total = event.get("total")
                                percent = None
                                if isinstance(completed, int) and isinstance(total, int) and total > 0:
                                    percent = int((completed / total) * 100)
                                self.pull_status[model_name] = {
                                    "model": model_name,
                                    "state": "downloading",
                                    "message": status_text,
                                    "completed": completed,
                                    "total": total,
                                    "percent": percent,
                                }
                            except Exception:
                                self.pull_status[model_name] = {
                                    "model": model_name,
                                    "state": "downloading",
                                    "message": line.decode("utf-8", errors="ignore"),
                                }

                    try:
                        models = await self.get_available_models()
                        if model_name in models:
                            self.pull_status[model_name] = {
                                "model": model_name,
                                "state": "completed",
                                "message": "Completed",
                                "percent": 100,
                                "completed": 1,
                                "total": 1,
                            }
                        else:
                            self.pull_status[model_name] = {
                                "model": model_name,
                                "state": "error",
                                "message": "Pull finished but model not listed",
                            }
                    except Exception as e:
                        self.pull_status[model_name] = {
                            "model": model_name,
                            "state": "error",
                            "message": f"Verification error: {str(e)}",
                        }
            except Exception as e:
                self.pull_status[model_name] = {
                    "model": model_name,
                    "state": "error",
                    "message": str(e),
                }

        self.pull_tasks[model_name] = asyncio.create_task(_pull_and_track())
        return self.pull_status[model_name]

    def get_pull_status(self, model_name: str) -> Dict[str, Any]:
        """Return current status for a model pull if tracked."""
        status = self.pull_status.get(model_name)
        if not status:
            return {"model": model_name, "state": "idle"}
        task = self.pull_tasks.get(model_name)
        if task and task.done():
            return status
        return status

    def list_active_pulls(self) -> Dict[str, Dict[str, Any]]:
        """Return all pulls that are not completed or errored."""
        active: Dict[str, Dict[str, Any]] = {}
        for model, status in self.pull_status.items():
            state = status.get("state")
            if state not in ("completed", "error", "idle"):
                active[model] = status
        return active

    async def generate_response(self, query: str, context_chunks: List[ContextChunk] = None, conversation_context: str = "") -> str:
        """ Generate a response using Ollama with optional context from RAG and conversation history """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Build prompt with context
            prompt = self._build_prompt(
                query, context_chunks, conversation_context)

            # Generate response
            response = await self._generate_text(prompt)

            return response

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

    def _build_prompt(self, query: str, context_chunks: List[ContextChunk] = None, conversation_context: str = "") -> str:
        """ Build a prompt with context for the AI model """

        system_instructions = """You are an AI assistant helping users understand documents. Use the provided context to answer questions accurately and comprehensively. If there's conversation history, use it to provide more contextual and relevant responses."""

        # Add conversation context if available
        conversation_section = ""
        if conversation_context:
            conversation_section = f"""Previous Conversation:
{conversation_context}

Current Question: {query}

"""
        else:
            conversation_section = f"Question: {query}\n\n"

        # Add document context if available
        if not context_chunks:
            prompt = f"""{system_instructions}

{conversation_section}Instructions:
- Answer the question based on your general knowledge
- If you don't have enough information, say so clearly
- Keep your answer concise but complete
- If there's conversation history, maintain context and refer to previous exchanges when relevant

Answer:"""
        else:
            # Build context from chunks
            context_text = ""
            for chunk in context_chunks:
                source = chunk.metadata.get(
                    'filename', 'Unknown') if chunk.metadata else 'Unknown'
                context_text += f"Source: {source}\n"
                context_text += f"Content: {chunk.content}\n"
                context_text += f"Relevance: {chunk.similarity_score:.2f}\n\n"

            prompt = f"""{system_instructions}

Document Context:
{context_text}

{conversation_section}Instructions:
- Answer based primarily on the provided document context
- If the context doesn't contain enough information, say so clearly
- Be specific and cite relevant parts of the context
- Keep your answer concise but complete
- If there's conversation history, maintain context and refer to previous exchanges when relevant

Answer:"""

        return prompt

    async def _generate_text(self, prompt: str) -> str:
        """
        Generate text using Ollama API

        Args:
            prompt: Input prompt

        Returns:
            Generated text
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 512,
                    "num_ctx": 2048,
                    "num_thread": 8
                }
            }

            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=90)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('response', '').strip()
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"Ollama API error {response.status}: {error_text}")

        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            raise

    async def get_available_models(self) -> List[str]:
        """ Get list of available models """
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return [model['name'] for model in data.get('models', [])]
                else:
                    raise Exception(f"Failed to get models: {response.status}")
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """ Perform health check on the Ollama service """
        try:
            if not self.is_initialized:
                return {"status": "not_initialized", "error": "Service not initialized"}

            # Check connection
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    available_models = [model['name']
                                        for model in data.get('models', [])]

                    # Check if the configured model is available
                    if self.model in available_models:
                        return {
                            "status": "healthy",
                            "current_model": self.model,
                            "available_models": available_models,
                            "ollama_host": self.base_url,
                            "model_ready": True
                        }
                    else:
                        return {
                            "status": "model_not_ready",
                            "current_model": self.model,
                            "available_models": available_models,
                            "ollama_host": self.base_url,
                            "model_ready": False,
                            "error": f"Model {self.model} is not available. Available models: {available_models}"
                        }
                else:
                    return {"status": "unhealthy", "error": f"Server returned status {response.status}"}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
