import json
import time
import os
import logging
from typing import TypeVar, Type
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from backend.models.report import LLMCallLog

load_dotenv()
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.search_model = os.getenv("OPENAI_SEARCH_MODEL", "gpt-4o")
        self.call_logs: list[LLMCallLog] = []

    async def research_completion(
        self,
        prompt: str,
        step_name: str,
    ) -> str:
        """Use OpenAI Responses API with web_search_preview to research a topic."""
        import asyncio
        return await asyncio.to_thread(
            self._research_completion_sync, prompt, step_name,
        )

    def _research_completion_sync(self, prompt: str, step_name: str) -> str:
        start = time.time()
        try:
            response = self.client.responses.create(
                model=self.search_model,
                tools=[{"type": "web_search_preview"}],
                input=prompt,
            )
            duration_ms = (time.time() - start) * 1000

            # Extract text from the response output items
            text_parts = []
            citations = []
            for item in response.output:
                if getattr(item, "type", None) == "message":
                    for content_block in getattr(item, "content", []):
                        if getattr(content_block, "type", None) == "output_text":
                            text_parts.append(content_block.text)
                            # Collect inline citations/annotations
                            for ann in getattr(content_block, "annotations", []):
                                if getattr(ann, "type", None) == "url_citation":
                                    citations.append({
                                        "title": getattr(ann, "title", ""),
                                        "url": getattr(ann, "url", ""),
                                    })

            content = "\n".join(text_parts) if text_parts else str(response.output)
            tokens = getattr(response.usage, "total_tokens", None) if response.usage else None

            # Append citation summary
            if citations:
                content += "\n\n--- Sources ---\n"
                for c in citations:
                    content += f"- {c['title']}: {c['url']}\n"

            logger.info(
                f"LLM research call [{step_name}]: model={self.search_model}, "
                f"tokens={tokens}, duration={duration_ms:.0f}ms, "
                f"sources={len(citations)}"
            )
            logger.info(f"LLM [{step_name}] research result: {content[:800]}...")

            self.call_logs.append(LLMCallLog(
                step_name=step_name,
                model=self.search_model,
                system_prompt="[web_search_preview tool]",
                user_prompt=prompt,
                response=content,
                tokens_used=tokens,
                duration_ms=duration_ms,
            ))

            return content

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.warning(
                f"Research API call failed [{step_name}] after {duration_ms:.0f}ms: {e}. "
                f"Falling back to standard completion."
            )
            # Fall back to standard chat completion (no search, but still works)
            return self._text_completion_sync(
                system_prompt=(
                    "You are a financial research analyst. Answer based on your knowledge. "
                    "Clearly state when you are estimating vs citing known data."
                ),
                user_prompt=prompt,
                step_name=f"{step_name}_fallback",
            )

    async def structured_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        step_name: str,
        max_retries: int = 2,
    ) -> T:
        """Call OpenAI with JSON mode and parse response into a Pydantic model."""
        import asyncio
        return await asyncio.to_thread(
            self._structured_completion_sync,
            system_prompt, user_prompt, response_model, step_name, max_retries,
        )

    def _structured_completion_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        step_name: str,
        max_retries: int,
    ) -> T:
        schema = response_model.model_json_schema()
        full_system = (
            f"{system_prompt}\n\n"
            f"Respond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        )

        last_error = None
        for attempt in range(max_retries + 1):
            start = time.time()
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": full_system},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                duration_ms = (time.time() - start) * 1000
                content = response.choices[0].message.content
                tokens = response.usage.total_tokens if response.usage else None

                logger.info(
                    f"LLM structured call [{step_name}]: model={self.model}, "
                    f"tokens={tokens}, duration={duration_ms:.0f}ms"
                )
                logger.info(f"LLM [{step_name}] response: {content[:500]}...")

                self.call_logs.append(LLMCallLog(
                    step_name=step_name,
                    model=self.model,
                    system_prompt=full_system,
                    user_prompt=user_prompt,
                    response=content,
                    tokens_used=tokens,
                    duration_ms=duration_ms,
                ))

                parsed = response_model.model_validate_json(content)
                return parsed

            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt + 1} failed for [{step_name}]: {e}")

        raise RuntimeError(f"LLM call failed after {max_retries + 1} attempts: {last_error}")

    async def text_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        step_name: str,
    ) -> str:
        """Call OpenAI for free-text response (e.g., narrative generation)."""
        import asyncio
        return await asyncio.to_thread(
            self._text_completion_sync, system_prompt, user_prompt, step_name,
        )

    def _text_completion_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        step_name: str,
    ) -> str:
        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        duration_ms = (time.time() - start) * 1000
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else None

        logger.info(
            f"LLM text call [{step_name}]: model={self.model}, "
            f"tokens={tokens}, duration={duration_ms:.0f}ms"
        )
        logger.info(f"LLM [{step_name}] response: {content[:500]}...")

        self.call_logs.append(LLMCallLog(
            step_name=step_name,
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=content,
            tokens_used=tokens,
            duration_ms=duration_ms,
        ))
        return content
