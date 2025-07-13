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
                        logger.info(f"Attempting to pull model {self.model}")
                        await self._pull_model(self.model)
                    else:
                        logger.info(f"Model {self.model} is available")
                else:
                    raise Exception(
                        f"Failed to check available models: {response.status}")
        except Exception as e:
            raise Exception(f"Error checking model availability: {str(e)}")

    async def _pull_model(self, model_name: str):
        """Pull a model from Ollama repository"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name}
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully pulled model {model_name}")
                else:
                    raise Exception(
                        f"Failed to pull model {model_name}: {response.status}")
        except Exception as e:
            raise Exception(f"Error pulling model {model_name}: {str(e)}")

    async def generate_response(self, query: str, context_chunks: List[ContextChunk] = None) -> str:
        """ Generate a response using Ollama with optional context from RAG """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Build prompt with context
            prompt = self._build_prompt(query, context_chunks)

            # Generate response
            response = await self._generate_text(prompt)

            return response

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

    def _build_prompt(self, query: str, context_chunks: List[ContextChunk] = None) -> str:
        """ Build a prompt with context for the AI model """
        if not context_chunks:
            return f"""Answer the following question:

Question: {query}

Answer:"""

        # Build context from chunks
        context_text = ""
        for chunk in context_chunks:
            context_text += f"Source: {chunk.source}\n"
            context_text += f"Content: {chunk.content}\n"
            context_text += f"Relevance: {chunk.similarity_score:.2f}\n\n"

        prompt = f"""You are an AI assistant helping users understand documents. Use the provided context to answer the question accurately and comprehensively.

Context:
{context_text}

Question: {query}

Instructions:
- Answer based primarily on the provided context
- If the context doesn't contain enough information, say so clearly
- Be specific and cite relevant parts of the context
- Keep your answer concise but complete

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
                timeout=aiohttp.ClientTimeout(total=90)  # 90 second timeout
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

    async def chat_with_history(self, messages: List[Dict[str, str]], context_chunks: List[ContextChunk] = None) -> str:
        """ Chat with conversation history """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Build conversation prompt
            conversation = ""
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                conversation += f"{role.capitalize()}: {content}\n"

            # Add context if available
            if context_chunks:
                context_text = "\n".join(
                    [f"Context: {chunk.content}" for chunk in context_chunks])
                conversation = f"{context_text}\n\nConversation:\n{conversation}"

            conversation += "Assistant:"

            # Generate response
            response = await self._generate_text(conversation)

            return response

        except Exception as e:
            logger.error(f"Error in chat with history: {str(e)}")
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

    async def switch_model(self, model_name: str):
        """ Switch to a different model """
        try:
            # Check if model is available
            available_models = await self.get_available_models()
            if model_name not in available_models:
                await self._pull_model(model_name)

            self.model = model_name
            logger.info(f"Switched to model: {model_name}")

        except Exception as e:
            logger.error(f"Error switching model: {str(e)}")
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
                    return {
                        "status": "healthy",
                        "current_model": self.model,
                        "available_models": [model['name'] for model in data.get('models', [])],
                        "ollama_host": self.base_url
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
