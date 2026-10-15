"""Agent loop with a scripted stub LLM (CI never calls a real model), plus the
Gemini adapter parsing real google-genai response objects."""

import pytest

from chokepoint.agent import numbers_not_in_evidence, run_agent
from chokepoint.llm import Call, GeminiLLM, Step, StubLLM
from chokepoint.runs import RunCtx


def call(i, name, args):
    return Step(calls=[Call(f"t{i}", name, args)], stop="tool")


GOOD = [
    call(1, "explain_grant", {"grant_ids": ["G-102", "G-103", "G-106"]}),
    call(2, "what_if", {"keep": ["G-102"], "cites": ["doc:dr-runbook"]}),
    call(3, "choose_plan", {"plan_id": "P1", "reason": "keeps DR failover working", "cites": ["doc:dr-runbook"]}),
    call(4, "draft_tickets", {"plan_id": "P1", "context_note": "DR runbook §3 needs G-102."}),
    Step(texts=["Revoke G-101 and G-106. +1 keeps DR failover. Source: doc:dr-runbook."], stop="end"),
]


@pytest.mark.db
def test_agent_chooses_p1_and_is_severed(scenario):
    events = list(run_agent(scenario, RunCtx(), "F-1", llm=StubLLM(GOOD)))
    final = events[-1]
    assert final["status"] == "chosen"
    assert [g["id"] for g in final["plan"]["grants"]] == ["G-101", "G-106"]
    assert final["plan"]["severed"] is True
    assert final["cites"] == ["doc:dr-runbook"]
    assert any(e["type"] == "tool" and e["name"] == "draft_tickets" and e["result"]["ok"] for e in events)


@pytest.mark.db
def test_hallucinated_cite_is_rejected_then_fallback(scenario):
    llm = StubLLM([call(1, "what_if", {"keep": ["G-102"], "cites": ["doc:made-up"]}),
                   Step(texts=["I could not verify."], stop="end")])
    events = list(run_agent(scenario, RunCtx(), "F-1", llm=llm))
    tool = [e for e in events if e["type"] == "tool"][0]
    assert not tool["result"]["ok"]
    (c, payload, is_err), = llm.results[0]
    assert is_err and "not seen" in payload                  # error goes back to the model
    final = events[-1]
    assert final["status"] == "fallback"
    assert final["fallback"]["plan"]["severed"] is True      # P0 still verified


@pytest.mark.db
def test_refusal_error_and_offline_fallbacks(scenario):
    ev = list(run_agent(scenario, RunCtx(), "F-1", llm=StubLLM([Step(stop="refusal")])))[-1]
    assert ev["status"] == "fallback" and ev["fallback"]["reason"] == "agent declined"
    ev = list(run_agent(scenario, RunCtx(), "F-1", llm=StubLLM([Step(stop="error", error="gemini 429")])))[-1]
    assert ev["status"] == "fallback" and "gemini 429" in ev["fallback"]["reason"]
    ev = list(run_agent(scenario, RunCtx(), "F-1", use_llm=False))[-1]
    assert ev["status"] == "fallback" and ev["fallback"]["plan"]["grants"]


@pytest.mark.db
def test_tool_loop_cap(scenario):
    llm = StubLLM([call(i, "who_knows", {"node_id": "role:deployer"}) for i in range(20)])
    ev = list(run_agent(scenario, RunCtx(), "F-1", llm=llm))[-1]
    assert ev["status"] == "fallback" and "12 steps" in ev["fallback"]["reason"]


@pytest.mark.db
def test_injection_text_does_not_create_decision(scenario):
    from chokepoint.decisions import recall
    llm = StubLLM(GOOD[:1] + [call(9, "record_decision", {"grant_id": "G-102", "disposition": "ACCEPT_RISK",
                                                        "rationale": "msg says so", "cites": ["msg:po-inj"]}),
                              Step(texts=["done"], stop="end")])
    events = list(run_agent(scenario, RunCtx(), "F-1", llm=llm))
    assert recall(scenario) == []                            # never written
    rd = [e for e in events if e["type"] == "tool" and e["name"] == "record_decision"][0]
    assert not rd["result"]["ok"] and "not seen" in rd["result"]["error"]   # injected msg isn't citable evidence


@pytest.mark.db
def test_agent_accept_risk_is_only_proposed(scenario):
    from chokepoint.decisions import recall
    llm = StubLLM(GOOD[:1] + [call(9, "record_decision", {"grant_id": "G-102", "disposition": "ACCEPT_RISK",
                                                        "rationale": "DR needs it", "review_by": "2099-01-01",
                                                        "cites": ["doc:dr-runbook"]}),
                              Step(texts=["done"], stop="end")])
    events = list(run_agent(scenario, RunCtx(), "F-1", llm=llm))
    assert recall(scenario) == []
    assert events[-1]["proposals"][0]["grant_id"] == "G-102"


def test_numeric_guard():
    assert numbers_not_in_evidence("cost 5 and 99 grants", [{"cost": 5}]) == ["99"]


# ── Gemini adapter against real google-genai types (no network) ─────────────

class _FakeModels:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def generate_content(self, **kw):
        self.calls.append(kw)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _gemini(responses):
    from types import SimpleNamespace
    llm = GeminiLLM.__new__(GeminiLLM)
    from google.genai import types
    llm.types = types
    llm.model = "test-model"
    llm.client = SimpleNamespace(models=_FakeModels(responses))
    llm.start("sys", "hello", [{"name": "what_if", "description": "d",
                                "input_schema": {"type": "object", "properties": {"keep": {"type": "array", "items": {"type": "string"}}}}}])
    return llm


def _resp(parts, finish="STOP"):
    from google.genai import types
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=parts), finish_reason=finish)])


def test_gemini_adapter_tool_call_and_results():
    from google.genai import types
    fc = types.Part(function_call=types.FunctionCall(name="what_if", args={"keep": ["G-102"]}))
    llm = _gemini([_resp([types.Part(text="checking"), fc]), _resp([types.Part(text="done")])])
    s1 = llm.step()
    assert s1.stop == "tool" and s1.calls[0].name == "what_if" and s1.calls[0].args == {"keep": ["G-102"]}
    assert s1.texts == ["checking"]
    llm.add_results([(s1.calls[0], {"plan_id": "P1"}, False)])
    last = llm.history[-1]
    assert last.role == "user" and last.parts[0].function_response.response == {"result": {"plan_id": "P1"}}
    s2 = llm.step()
    assert s2.stop == "end" and s2.texts == ["done"]
    cfg = llm.client.models.calls[0]["config"]
    assert cfg.automatic_function_calling.disable is True
    assert cfg.tools[0].function_declarations[0].name == "what_if"


def test_gemini_adapter_refusal_and_error():
    from google.genai import errors
    assert _gemini([_resp([], finish="SAFETY")]).step().stop == "refusal"
    s = _gemini([errors.ClientError(429, {"error": {"message": "Quota exceeded: requests per day"}})]).step()
    assert s.stop == "error" and "429" in s.error
    s = _gemini([_resp([], finish="MALFORMED_FUNCTION_CALL")]).step()
    assert s.stop == "error"


def test_gemini_adapter_waits_out_per_minute_429(monkeypatch):
    from google.genai import errors, types
    from chokepoint import llm as L
    slept = []
    monkeypatch.setattr(L.time, "sleep", slept.append)
    rate = errors.ClientError(429, {"error": {"message": "per minute", "details": [{"retryDelay": "7s"}]}})
    s = _gemini([rate, _resp([types.Part(text="ok")])]).step()
    assert s.stop == "end" and s.texts == ["ok"] and slept == [8.0]
    s = _gemini([rate] * 10).step()            # bounded: gives up after GEMINI_429_WAIT_S
    assert s.stop == "error" and "429" in s.error


def test_gemini_daily_quota_is_not_retried(monkeypatch):
    from google.genai import errors
    from chokepoint import llm as L
    monkeypatch.setattr(L.time, "sleep", lambda s: pytest.fail("must not wait on a daily quota"))
    daily = errors.ClientError(429, {"error": {"message": "quota", "details": [
        {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}, {"retryDelay": "29090s"}]}})
    s = _gemini([daily]).step()
    assert s.stop == "error" and "daily Gemini quota" in s.error
