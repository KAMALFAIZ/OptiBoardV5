"""
Service d'abstraction multi-fournisseur d'IA pour OptiBoard.
Supporte: OpenAI (GPT-4o), Anthropic (Claude), Ollama (local).
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Optional
import httpx
import json
import logging

logger = logging.getLogger(__name__)


class AIMessage:
    """Representation d'un message dans une conversation IA."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class AIProviderError(Exception):
    """Exception levee par un fournisseur IA."""
    pass


class BaseAIProvider(ABC):
    """Interface commune pour tous les fournisseurs IA."""

    @abstractmethod
    async def chat(self, messages: List[AIMessage], stream: bool = False) -> str:
        ...

    @abstractmethod
    async def chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        ...


class OpenAIProvider(BaseAIProvider):
    """Fournisseur OpenAI (GPT-4o, GPT-4-turbo, etc.)"""

    def __init__(self, api_key: str, model: str, max_tokens: int, temperature: float):
        self.api_key = api_key
        self.model = model or "gpt-4o"
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = "https://api.openai.com/v1"

    async def chat(self, messages: List[AIMessage], stream: bool = False) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            if response.status_code != 200:
                raise AIProviderError(
                    f"OpenAI API error {response.status_code}: {response.text}"
                )
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

    def get_provider_name(self) -> str:
        return f"OpenAI ({self.model})"


class AnthropicProvider(BaseAIProvider):
    """Fournisseur Anthropic (Claude Opus, Sonnet, Haiku)"""

    def __init__(self, api_key: str, model: str, max_tokens: int, temperature: float):
        self.api_key = api_key
        self.model = model or "claude-sonnet-4-5-20250929"
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = "https://api.anthropic.com/v1"

    def _split_system(self, messages: List[AIMessage]):
        """Separe le system prompt des messages user/assistant."""
        system = None
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                chat_messages.append(m.to_dict())
        return system, chat_messages

    async def chat(self, messages: List[AIMessage], stream: bool = False) -> str:
        system, chat_messages = self._split_system(messages)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": chat_messages
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            )
            if response.status_code != 200:
                raise AIProviderError(
                    f"Anthropic API error {response.status_code}: {response.text}"
                )
            data = response.json()
            return data["content"][0]["text"]

    async def chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        system, chat_messages = self._split_system(messages)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": chat_messages,
            "stream": True
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {}).get("text", "")
                                if delta:
                                    yield delta
                        except (json.JSONDecodeError, KeyError):
                            pass

    def get_provider_name(self) -> str:
        return f"Anthropic ({self.model})"


class OllamaProvider(BaseAIProvider):
    """Fournisseur Ollama (local, llama3.2, mistral, etc.)"""

    def __init__(self, base_url: str, model: str, max_tokens: int, temperature: float):
        self.base_url = base_url.rstrip("/")
        self.model = model or "llama3.2"
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def chat(self, messages: List[AIMessage], stream: bool = False) -> str:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            if response.status_code != 200:
                raise AIProviderError(
                    f"Ollama API error {response.status_code}: {response.text}"
                )
            data = response.json()
            return data["message"]["content"]

    async def chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass

    def get_provider_name(self) -> str:
        return f"Ollama ({self.model})"


def get_ai_provider() -> Optional[BaseAIProvider]:
    """
    Fabrique retournant le fournisseur IA configure dans les settings.
    Retourne None si l'IA n'est pas configuree ou desactivee.
    """
    from ..config import reload_settings
    settings = reload_settings()  # Toujours relire le .env pour avoir la config a jour

    if not settings.AI_ENABLED or not settings.AI_PROVIDER:
        return None

    provider = settings.AI_PROVIDER.lower()

    if provider == "openai":
        if not settings.AI_API_KEY:
            raise AIProviderError("Cle API OpenAI non configuree")
        return OpenAIProvider(
            api_key=settings.AI_API_KEY,
            model=settings.AI_MODEL,
            max_tokens=settings.AI_MAX_TOKENS,
            temperature=settings.AI_TEMPERATURE
        )
    elif provider == "anthropic":
        if not settings.AI_API_KEY:
            raise AIProviderError("Cle API Anthropic non configuree")
        return AnthropicProvider(
            api_key=settings.AI_API_KEY,
            model=settings.AI_MODEL,
            max_tokens=settings.AI_MAX_TOKENS,
            temperature=settings.AI_TEMPERATURE
        )
    elif provider == "ollama":
        return OllamaProvider(
            base_url=settings.AI_OLLAMA_URL,
            model=settings.AI_MODEL,
            max_tokens=settings.AI_MAX_TOKENS,
            temperature=settings.AI_TEMPERATURE
        )
    else:
        raise AIProviderError(f"Fournisseur IA inconnu: {provider}")
