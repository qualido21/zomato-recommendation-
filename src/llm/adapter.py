"""
src/llm/adapter.py
──────────────────
LLM Adapter abstraction — swap providers without touching the rest of the pipeline.

Supported providers (configured via LLM_PROVIDER in .env):
  groq    — Groq inference API (primary, OpenAI-compatible)
  openai  — OpenAI API
  gemini  — Google Gemini
  ollama  — Local Ollama REST API
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import httpx
from dotenv import load_dotenv

load_dotenv()


class LLMAdapter(ABC):
    """Base class for all LLM backends."""

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Send a system + user prompt and return the raw text response."""


# ── Groq (primary) ────────────────────────────────────────────────────────────

class GroqAdapter(LLMAdapter):
    """
    Groq inference API — OpenAI-compatible REST endpoint.
    Uses httpx directly to avoid an extra dependency; Groq's API mirrors
    the OpenAI /chat/completions schema exactly.
    """

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ["GROQ_API_KEY"]
        self._model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self._timeout = timeout

    async def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self.BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAIAdapter(LLMAdapter):
    """OpenAI chat completions via the official async client."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError("Install 'openai' to use OpenAIAdapter.") from exc

        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = AsyncOpenAI(
            api_key=api_key or os.environ["OPENAI_API_KEY"],
            timeout=timeout,
        )

    async def complete(self, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content


# ── Gemini ────────────────────────────────────────────────────────────────────

class GeminiAdapter(LLMAdapter):
    """Google Gemini via google-generativeai."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError("Install 'google-generativeai' to use GeminiAdapter.") from exc

        key = api_key or os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=key)
        model_name = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self._model = genai.GenerativeModel(model_name)

    async def complete(self, system: str, user: str) -> str:
        import asyncio

        prompt = f"{system}\n\n{user}"
        loop = asyncio.get_event_loop()
        # google-generativeai doesn't expose a native async API; run in executor
        response = await loop.run_in_executor(
            None, lambda: self._model.generate_content(prompt)
        )
        return response.text


# ── Ollama ────────────────────────────────────────────────────────────────────

class OllamaAdapter(LLMAdapter):
    """Local Ollama REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._model = model or os.getenv("OLLAMA_MODEL", "llama3")
        self._timeout = timeout

    async def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]


# ── Factory ───────────────────────────────────────────────────────────────────

def build_adapter(provider: str | None = None) -> LLMAdapter:
    """
    Instantiate the correct LLMAdapter based on the LLM_PROVIDER env var
    (or the explicit *provider* argument).

    Raises ValueError for unknown providers.
    """
    name = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()
    if name == "groq":
        return GroqAdapter()
    if name == "openai":
        return OpenAIAdapter()
    if name == "gemini":
        return GeminiAdapter()
    if name == "ollama":
        return OllamaAdapter()
    raise ValueError(
        f"Unknown LLM_PROVIDER '{name}'. Choose from: groq, openai, gemini, ollama."
    )
