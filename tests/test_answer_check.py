from nexus.agent.nodes import read_unsupported_claims


def test_no_unsupported_claims():
    assert read_unsupported_claims('{"unsupported": []}') == []


def test_json_inside_a_code_fence_is_read():
    reply = '```json\n{"unsupported": [{"claim": "Free dental", "reason": "Not in the sources"}]}\n```'
    assert read_unsupported_claims(reply) == [{"claim": "Free dental", "reason": "Not in the sources"}]


def test_invalid_entries_are_dropped():
    reply = '{"unsupported": ["just text", {"reason": "no claim"}, {"claim": "Real claim"}]}'
    assert read_unsupported_claims(reply) == [{"claim": "Real claim", "reason": ""}]


def test_unreadable_reply_gives_none():
    assert read_unsupported_claims("I cannot produce JSON") is None
    assert read_unsupported_claims('{"something": 1}') is None
