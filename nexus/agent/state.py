from typing import TypedDict


class AgentState(TypedDict):
    workspace_id: str
    question: str
    query: str              # what we search for, can be rewritten
    attempt: int            # how many searches we have done
    candidates: list        # sections found in the latest search
    kept: list              # sections the grader marked relevant, across all searches
    verdict: str            # "enough", "partial" or "none"
    better_query: str       # the grader's suggestion for the next search
    answer: str
    documents: list         # the numbered documents the answer cites
    check: dict             # whether the answer's claims are supported by its sources
    steps: list             # what the agent did, shown in the UI
