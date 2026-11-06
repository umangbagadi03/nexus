import json

from nexus.evaluation import judge


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply

    def generate(self, system_prompt, user_prompt):
        return self.reply


def run_judge(monkeypatch, reply):
    monkeypatch.setattr(judge, "get_llm", lambda: FakeLLM(reply))
    return judge.judge_answer("question", "reference", "answer")


def facts(*items):
    key_facts = []
    for core, present in items:
        key_facts.append({"fact": "a fact", "core": core, "present": present})
    return key_facts


def test_all_facts_present_is_correct(monkeypatch):
    reply = json.dumps({"key_facts": facts((True, True), (False, True)), "contradictions": [], "reason": "ok"})
    assert run_judge(monkeypatch, reply) == (True, "ok", 1.0)


def test_missing_supporting_fact_lowers_coverage_only(monkeypatch):
    reply = json.dumps({"key_facts": facts((True, True), (False, False)), "contradictions": [], "reason": "ok"})
    is_correct, reason, coverage = run_judge(monkeypatch, reply)
    assert is_correct is True
    assert coverage == 0.5


def test_missing_core_fact_is_incorrect(monkeypatch):
    reply = json.dumps({"key_facts": facts((True, False), (False, True)), "contradictions": [], "reason": "no"})
    assert run_judge(monkeypatch, reply)[0] is False


def test_contradiction_is_incorrect(monkeypatch):
    reply = json.dumps({"key_facts": facts((True, True)), "contradictions": ["says it was merged"], "reason": "no"})
    assert run_judge(monkeypatch, reply)[0] is False


def test_unreadable_reply_is_incorrect(monkeypatch):
    is_correct, reason, coverage = run_judge(monkeypatch, "CORRECT")
    assert is_correct is False
    assert coverage is None
