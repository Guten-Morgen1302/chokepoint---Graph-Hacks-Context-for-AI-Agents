"""LLM providers behind one tiny interface, so the agent loop is provider-free.

    adapter.start(system, user_text, tools)   tools: [{name, description, input_schema}]
    step = adapter.step()                      -> Step(texts, calls, stop, error)
    adapter.add_results([(call, payload, is_error), ...])

Providers: gemini (default, google-genai SDK) and anthropic. Tests use StubLLM.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from .config import settings


@dataclass
class Call:
    id: str
    name: str
    args: dict
    provider_id: str | None = None   # Gemini's own call id, echoed back when present


@dataclass
class Step:
    texts: list[str] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    stop: str = "end"        # "tool" | "end" | "refusal" | "error"
    error: str | None = None


class LLMUnavailable(Exception):
    pass


# ── Gemini ───────────────────────────────────────────────────────────────────

GEMINI_REFUSALS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION",
                   "IMAGE_SAFETY", "IMAGE_PROHIBITED_CONTENT"}
GEMINI_429_WAIT_S = 40.0   # total per step; the agent's own 60 s deadline still applies


class GeminiLLM:
    def __init__(self, api_key: str, model: str):
        from google import genai
        from google.genai import types
        self.types = types
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30_000))
        self.model = model
        self.history: list = []
        self.config = None

    def start(self, system: str, user: str, tools: list[dict]) -> None:
        t = self.types
        decls = [t.FunctionDeclaration(name=x["name"], description=x["description"],
                                       parameters_json_schema=x["input_schema"]) for x in tools]
        self.config = t.GenerateContentConfig(
            system_instruction=system,
            tools=[t.Tool(function_declarations=decls)],
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.0,
            max_output_tokens=8192,
        )
        self.history = [t.Content(role="user", parts=[t.Part(text=user)])]

    def _generate(self):
        """Free-tier keys hit the per-minute limit mid-run and busy models answer 503:
        wait (bounded) and retry. A per-day quota is not retried."""
        from google.genai import errors
        waited = 0.0
        while True:
            try:
                return self.client.models.generate_content(model=self.model, contents=self.history,
                                                           config=self.config)
            except errors.APIError as e:
                code, msg = getattr(e, "code", None), str(e)
                if code not in (429, 503) or "per day" in msg.lower() or "PerDay" in msg:
                    raise
                m = re.search(r"retryDelay'?\"?:\s*'?\"?(\d+(?:\.\d+)?)s", msg)
                delay = min(float(m.group(1)) + 1 if m else (10.0 if code == 429 else 4.0),
                            GEMINI_429_WAIT_S - waited)
                if delay <= 0:
                    raise
                time.sleep(delay)
                waited += delay

    def step(self) -> Step:
        from google.genai import errors
        try:
            resp = self._generate()
        except errors.APIError as e:
            if getattr(e, "code", None) == 429 and "PerDay" in str(e):
                return Step(stop="error", error="daily Gemini quota used up (free tier: 20 requests per model per day)")
            return Step(stop="error", error=f"gemini {getattr(e, 'code', '')}: {str(e)[:200]}")
        except Exception as e:  # network
            return Step(stop="error", error=f"gemini unreachable: {type(e).__name__}")
        if resp.prompt_feedback is not None and getattr(resp.prompt_feedback, "block_reason", None):
            return Step(stop="refusal")
        if not resp.candidates:
            return Step(stop="refusal")
        cand = resp.candidates[0]
        reason = cand.finish_reason.name if cand.finish_reason is not None else "STOP"
        if reason in GEMINI_REFUSALS:
            return Step(stop="refusal")
        if cand.content is not None:
            self.history.append(cand.content)        # keeps thought signatures intact
        parts = (cand.content.parts if cand.content and cand.content.parts else [])
        texts = [p.text for p in parts if p.text and not p.thought]
        calls = []
        for i, p in enumerate(parts):
            fc = p.function_call
            if fc is not None:
                calls.append(Call(id=fc.id or f"call_{len(self.history)}_{i}", name=fc.name,
                                  args=dict(fc.args or {}), provider_id=fc.id))
        if reason == "MALFORMED_FUNCTION_CALL" and not calls:
            return Step(texts=texts, stop="error", error="malformed tool call")
        return Step(texts=texts, calls=calls, stop="tool" if calls else "end")

    def add_results(self, results: list[tuple[Call, dict, bool]]) -> None:
        t = self.types
        parts = []
        for call, payload, is_error in results:
            resp = {"error": payload} if is_error else {"result": payload}
            body = json.loads(json.dumps(resp, default=str))
            parts.append(t.Part(function_response=t.FunctionResponse(id=call.provider_id, name=call.name, response=body)))
        self.history.append(t.Content(role="user", parts=parts))


# ── Anthropic (optional) ─────────────────────────────────────────────────────

class AnthropicLLM:
    def __init__(self, api_key: str, model: str):
        import anthropic
        self.anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, timeout=55.0, max_retries=1)
        self.model = model
        self.messages: list = []

    def start(self, system: str, user: str, tools: list[dict]) -> None:
        self.system, self.tools = system, tools
        self.messages = [{"role": "user", "content": user}]

    def step(self) -> Step:
        a = self.anthropic
        try:
            resp = self.client.messages.create(model=self.model, max_tokens=8000, system=self.system,
                                               tools=self.tools, messages=self.messages)
        except a.APIStatusError as e:
            return Step(stop="error", error=f"anthropic {e.status_code}")
        except a.APIConnectionError:
            return Step(stop="error", error="anthropic unreachable")
        if resp.stop_reason == "refusal":
            return Step(stop="refusal")
        self.messages.append({"role": "assistant", "content": resp.content})
        texts = [b.text for b in resp.content if b.type == "text" and b.text.strip()]
        calls = [Call(b.id, b.name, b.input if isinstance(b.input, dict) else {}) for b in resp.content if b.type == "tool_use"]
        return Step(texts=texts, calls=calls, stop="tool" if calls else "end")

    def add_results(self, results: list[tuple[Call, dict, bool]]) -> None:
        self.messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": c.id, "is_error": err,
             "content": json.dumps(p, default=str)[:20000]} for c, p, err in results]})


# ── test stub ────────────────────────────────────────────────────────────────

class StubLLM:
    """Plays back scripted steps (CI never calls a real model)."""

    def __init__(self, steps: list[Step]):
        self.steps = list(steps)
        self.results: list = []

    def start(self, system, user, tools):
        self.user = user

    def step(self) -> Step:
        return self.steps.pop(0) if self.steps else Step(stop="end")

    def add_results(self, results):
        self.results.append(results)


def provider_ready() -> bool:
    if settings.llm_provider == "anthropic":
        return bool(settings.anthropic_api_key)
    return bool(settings.gemini_api_key)


def make_llm():
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMUnavailable("no ANTHROPIC_API_KEY")
        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
    if not settings.gemini_api_key:
        raise LLMUnavailable("no GEMINI_API_KEY")
    return GeminiLLM(settings.gemini_api_key, settings.gemini_model)


def complete_json(system: str, user: str) -> str:
    """One-shot JSON completion (used by ingest_knowledge)."""
    if settings.llm_provider == "anthropic":
        llm = make_llm()
        r = llm.client.messages.create(model=llm.model, max_tokens=2048, system=system,
                                       messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in r.content if b.type == "text")
    from google import genai
    from google.genai import types
    if not settings.gemini_api_key:
        raise LLMUnavailable("no GEMINI_API_KEY")
    client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=60_000))
    r = client.models.generate_content(
        model=settings.gemini_model, contents=user,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.0,
                                           response_mime_type="application/json", max_output_tokens=2048))
    return r.text or "[]"
