# app/ai/llm.py
"""LLM provider abstraction layer."""

from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMConnectionError

logger = get_logger(__name__)

# Thread pool for sync LLM calls
_executor = ThreadPoolExecutor(max_workers=4)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""
    
    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """Get the LangChain chat model."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass


class GroqProvider(LLMProvider):
    """Groq LLM provider."""
    
    def __init__(self):
        self._model: Optional[BaseChatModel] = None
    
    def get_name(self) -> str:
        return "groq"
    
    def get_model(self) -> BaseChatModel:
        if self._model is None:
            try:
                from langchain_groq import ChatGroq
                self._model = ChatGroq(
                    model_name=settings.GROQ_MODEL,
                    api_key=settings.GROQ_API_KEY,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS
                )
                logger.info(f"Initialized Groq LLM: {settings.GROQ_MODEL}")
            except Exception as e:
                raise LLMConnectionError("groq", str(e))
        return self._model


class GoogleProvider(LLMProvider):
    """Google Gemini LLM provider."""
    
    def __init__(self):
        self._model: Optional[BaseChatModel] = None
    
    def get_name(self) -> str:
        return "google"
    
    def get_model(self) -> BaseChatModel:
        if self._model is None:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._model = ChatGoogleGenerativeAI(
                    model=settings.GOOGLE_MODEL,
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=settings.LLM_TEMPERATURE,
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                    convert_system_message_to_human=True
                )
                logger.info(f"Initialized Google LLM: {settings.GOOGLE_MODEL}")
            except Exception as e:
                raise LLMConnectionError("google", str(e))
        return self._model


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(self, model_name: str = "llama3.2"):
        self._model: Optional[BaseChatModel] = None
        self.model_name = model_name
    
    def get_name(self) -> str:
        return "ollama"
    
    def get_model(self) -> BaseChatModel:
        if self._model is None:
            try:
                from langchain_ollama import ChatOllama
                self._model = ChatOllama(
                    model=self.model_name,
                    temperature=settings.LLM_TEMPERATURE
                )
                logger.info(f"Initialized Ollama LLM: {self.model_name}")
            except Exception as e:
                raise LLMConnectionError("ollama", str(e))
        return self._model


class LLMService:
    """
    Unified LLM service with provider abstraction.
    Handles retries, fallbacks, and async execution.
    """
    
    def __init__(self):
        self._provider: Optional[LLMProvider] = None
        self._fallback_provider: Optional[LLMProvider] = None
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize LLM providers based on config."""
        provider_name = settings.LLM_PROVIDER.lower()
        
        if provider_name == "groq":
            self._provider = GroqProvider()
            if settings.GOOGLE_API_KEY:
                self._fallback_provider = GoogleProvider()
        elif provider_name == "google":
            self._provider = GoogleProvider()
            if settings.GROQ_API_KEY:
                self._fallback_provider = GroqProvider()
        elif provider_name == "ollama":
            self._provider = OllamaProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
        
        logger.info(f"LLM Service initialized with provider: {provider_name}")
    
    @property
    def model(self) -> BaseChatModel:
        """Get the current LLM model."""
        return self._provider.get_model()
    
    @property
    def provider_name(self) -> str:
        """Get current provider name."""
        return self._provider.get_name()
    
    def invoke_sync(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Synchronous LLM invocation."""
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = self.model.invoke(messages, **kwargs)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            
            # Try fallback provider
            if self._fallback_provider:
                logger.info(f"Trying fallback provider: {self._fallback_provider.get_name()}")
                try:
                    response = self._fallback_provider.get_model().invoke(messages, **kwargs)
                    return response.content if hasattr(response, 'content') else str(response)
                except Exception as fe:
                    logger.error(f"Fallback also failed: {fe}")
            
            raise
    
    async def invoke(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Asynchronous LLM invocation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.invoke_sync(prompt, system_prompt, **kwargs)
        )
    
    def invoke_with_json(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invoke and parse JSON response."""
        import json
        
        # Add JSON instruction to prompt
        json_prompt = f"{prompt}\n\nRespond with valid JSON only. No markdown, no explanation."
        
        response = self.invoke_sync(json_prompt, system_prompt)
        
        # Clean response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
    
    async def invoke_with_json_async(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Async invoke and parse JSON response."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.invoke_with_json(prompt, system_prompt)
        )


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service