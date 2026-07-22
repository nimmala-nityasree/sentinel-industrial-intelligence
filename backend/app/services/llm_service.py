"""
LLM service (Gemini).

All agent calls to the LLM go through this service rather than importing
google.generativeai directly. Benefits: one place for retry/backoff logic,
one place to swap models, and one place to enforce "structured JSON out"
conventions used by the extraction and RCA agents.
"""
import json

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.exceptions import LLMGenerationError
from app.core.logging_config import logger

genai.configure(api_key=settings.gemini_api_key)


class LLMService:
    """Wraps Gemini text generation with retries and structured-output helpers."""

    def __init__(self) -> None:
        self._model = genai.GenerativeModel(settings.gemini_model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """Free-text generation with retry on transient API failures."""
        try:
            response = self._model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=temperature),
            )
            if not response.text:
                raise LLMGenerationError("Gemini returned an empty response")
            return response.text
        except LLMGenerationError:
            raise
        except Exception as exc:
            logger.error(f"Gemini generation failed: {exc}")
            raise LLMGenerationError(str(exc)) from exc

    def generate_json(self, prompt: str, temperature: float = 0.1) -> dict:
        """
        Generation with a strict instruction to return only JSON, used by the
        entity-extraction and RCA agents. Includes defensive parsing since
        LLMs occasionally wrap JSON in markdown fences despite instructions.
        """
        json_prompt = (
            f"{prompt}\n\n"
            "Respond with ONLY valid JSON. No markdown fences, no commentary, no preamble."
        )
        raw = self.generate(json_prompt, temperature=temperature)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse LLM JSON output: {cleaned[:300]}")
            raise LLMGenerationError(f"LLM did not return valid JSON: {exc}") from exc


llm_service = LLMService()
