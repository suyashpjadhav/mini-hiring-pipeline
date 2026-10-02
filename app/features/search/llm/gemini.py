"""Gemini interpreter implementation for search query fallback (SYSTEM_DESIGN §12)."""

import asyncio
import os
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from google import genai
from google.genai import errors, types

from app.core.config import get_settings
from app.features.search.llm.dto import LLMQuery
from app.features.search.llm.interpreter import LLMResult, QueryInterpreter


class GeminiInterpreter(QueryInterpreter):
    """Google Gemini implementation of QueryInterpreter protocol."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._prompt_template: str | None = None

    def _load_prompt_template(self) -> str:
        if self._prompt_template is None:
            prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "query_parser.v1.md")
            with open(prompt_path, encoding="utf-8") as f:
                self._prompt_template = f.read()
        return self._prompt_template

    async def interpret(self, q: str, today: date, tz: str) -> LLMResult:
        """Interpret search query using Gemini structured output with timeout & 1 retry on 5xx."""
        if not self.settings.llm_enabled or not self.settings.gemini_api_key:
            return LLMResult(
                ast=None,
                outcome="error",
                latency_ms=0.0,
                tokens_in=0,
                tokens_out=0,
            )

        api_key_val = self.settings.gemini_api_key.get_secret_value()
        client = genai.Client(api_key=api_key_val)

        template = self._load_prompt_template()
        today_iso = today.isoformat()
        weekday = today.strftime("%A")

        prompt = (
            template.replace("{today_iso}", today_iso)
            .replace("{weekday}", weekday)
            .replace("{tz}", tz)
        )
        contents = f"{prompt}\n\nQuery: <user_query>{q}</user_query>"

        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_schema=LLMQuery,
            thinking_config=types.ThinkingConfig(thinking_budget=self.settings.llm_thinking_budget),
        )

        start_time = time.perf_counter()
        attempt = 0
        response = None

        while attempt < 2:
            attempt += 1
            try:
                # Execute async call with timeout guard
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=self.settings.gemini_model,
                        contents=contents,
                        config=config,
                    ),
                    timeout=self.settings.llm_timeout_s + 0.5,
                )
                break
            except TimeoutError:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                return LLMResult(
                    ast=None,
                    outcome="timeout",
                    latency_ms=latency_ms,
                    tokens_in=0,
                    tokens_out=0,
                )
            except errors.ServerError:
                if attempt < 2:
                    await asyncio.sleep(0.5)
                    continue
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                return LLMResult(
                    ast=None,
                    outcome="error",
                    latency_ms=latency_ms,
                    tokens_in=0,
                    tokens_out=0,
                )
            except errors.ClientError as err:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                if getattr(err, "code", None) == 429 or "429" in str(err):
                    return LLMResult(
                        ast=None,
                        outcome="over_budget",
                        latency_ms=latency_ms,
                        tokens_in=0,
                        tokens_out=0,
                    )
                return LLMResult(
                    ast=None,
                    outcome="error",
                    latency_ms=latency_ms,
                    tokens_in=0,
                    tokens_out=0,
                )
            except Exception:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                return LLMResult(
                    ast=None,
                    outcome="error",
                    latency_ms=latency_ms,
                    tokens_in=0,
                    tokens_out=0,
                )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if response is None:
            return LLMResult(
                ast=None,
                outcome="error",
                latency_ms=latency_ms,
                tokens_in=0,
                tokens_out=0,
            )

        tokens_in = 0
        tokens_out = 0
        if response.usage_metadata:
            tokens_in = response.usage_metadata.prompt_token_count or 0
            tokens_out = (
                getattr(response.usage_metadata, "candidates_token_count", None)
                or getattr(response.usage_metadata, "total_token_count", None)
                or 0
            )

        dto: LLMQuery | None = None
        if isinstance(response.parsed, LLMQuery):
            dto = response.parsed
        elif response.text:
            try:
                dto = LLMQuery.model_validate_json(response.text)
            except Exception:
                dto = None

        if dto is None:
            return LLMResult(
                ast=None,
                outcome="invalid",
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

        tz_info = ZoneInfo(tz) if tz else ZoneInfo("Asia/Kolkata")
        now_dt = datetime.combine(today, datetime.min.time(), tzinfo=tz_info)
        ast, outcome = dto.to_ast(q, now_dt, tz_info)

        return LLMResult(
            ast=ast,
            outcome=outcome,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
