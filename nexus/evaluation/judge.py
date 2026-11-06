from nexus.llm.provider import get_llm
from nexus.utils.json_reply import parse_json_reply

JUDGE_SYSTEM_PROMPT = """You grade answers to questions about a company's internal knowledge.
You get a question, a reference answer written by a person, and an answer to grade.

List the facts of the reference answer. For each one, decide:
- core: true if the person asking would be misled, or would not get what they asked for, without this fact.
  false if it is a supporting detail the question did not ask about.
- present: true if the answer states it. Wording does not matter, but the meaning must be there.

Also list anything in the answer that contradicts the reference. Extra details that do not contradict it are fine.

Reply with JSON only, in this format:
{"key_facts": [{"fact": "...", "core": true, "present": true}], "contradictions": ["..."], "reason": "one sentence"}"""


def judge_answer(question, reference_answer, answer):
    """Returns (is_correct, reason, coverage). Correct means every core fact is there and nothing contradicts
    the reference. Coverage is the share of all facts that are there, so missing details still show up."""
    prompt = "Question: " + question + "\n\n"
    prompt += "Reference answer: " + reference_answer + "\n\n"
    prompt += "Answer to grade: " + answer

    reply = get_llm().generate(JUDGE_SYSTEM_PROMPT, prompt)
    data = parse_json_reply(reply)

    if data is None or not isinstance(data.get("key_facts"), list) or len(data["key_facts"]) == 0:
        return False, "Could not read the judge reply: " + reply[:200], None

    is_correct = len(data.get("contradictions") or []) == 0
    present_count = 0
    for item in data["key_facts"]:
        is_present = isinstance(item, dict) and item.get("present") is True
        if is_present:
            present_count += 1
        elif not isinstance(item, dict) or item.get("core") is not False:
            is_correct = False

    return is_correct, str(data.get("reason") or ""), present_count / len(data["key_facts"])
