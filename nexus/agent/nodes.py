from langgraph.config import get_stream_writer

from nexus import config
from nexus.agent.prompts import CHECK_SYSTEM_PROMPT, GRADER_SYSTEM_PROMPT, build_check_prompt, build_grader_prompt
from nexus.graph.link_graph import get_neighbors
from nexus.indexing import hybrid_store
from nexus.llm.provider import get_llm
from nexus.rag.answer_builder import stream_answer_text
from nexus.rag.hybrid_retriever import limit_per_document, retrieve_sections
from nexus.rag.retriever import group_by_document
from nexus.utils.json_reply import parse_json_reply

# Follow links from the top few results only, and add a few linked documents at most
LINKS_FROM_TOP = 3
MAX_LINKED_SECTIONS = 4
MAX_SECTIONS_IN_ANSWER = 6

VERDICT_TEXT = {
    "enough": "enough to answer",
    "partial": "part of the answer is still missing",
    "none": "nothing relevant yet",
}


def add_step(state, kind, text):
    steps = list(state["steps"])
    steps.append({"kind": kind, "text": text})
    return steps


def short_name(section):
    if section["kind"] == "issue":
        return "issue #" + str(section["number"])
    if section["kind"] == "pr":
        return "PR #" + str(section["number"])
    return "\"" + section["title"] + "\""


def count_text(count, one, many):
    if count == 1:
        return "1 " + one
    return str(count) + " " + many


def show_status(text):
    get_stream_writer()({"type": "status", "text": text})


def retrieve_node(state):
    show_status("Searching")
    sections = retrieve_sections(state["workspace_id"], state["query"])

    text = "Searched for \"" + state["query"] + "\" and found " + str(len(sections)) + " sections"
    return {
        "candidates": sections,
        "attempt": state["attempt"] + 1,
        "steps": add_step(state, "search", text),
    }


def expand_links_node(state):
    """Use the link graph: an issue leads to the PR that fixed it, a page to the pages it links to."""
    workspace_id = state["workspace_id"]
    candidates = list(state["candidates"])

    seen_documents = set()
    for section in candidates + state["kept"]:
        seen_documents.add(section["document_id"])

    linked_sections = []
    followed = []

    for section in candidates[:LINKS_FROM_TOP]:
        for neighbor in get_neighbors(workspace_id, section["document_id"]):
            if len(linked_sections) >= MAX_LINKED_SECTIONS:
                break
            if neighbor["document_id"] in seen_documents:
                continue

            linked = hybrid_store.get_first_parent_of_document(workspace_id, neighbor["document_id"])
            if linked is None:
                continue

            linked = dict(linked)
            linked["score"] = 0
            linked["via"] = "Linked from " + short_name(section)
            linked_sections.append(linked)
            seen_documents.add(neighbor["document_id"])
            followed.append(short_name(section) + " to " + short_name(linked))

    if len(linked_sections) == 0:
        return {}

    if len(followed) == 1:
        text = "Followed a link from " + followed[0]
    else:
        text = "Followed " + str(len(followed)) + " links between documents, like " + followed[0]
    return {
        "candidates": candidates + linked_sections,
        "steps": add_step(state, "links", text),
    }


def grade_node(state):
    show_status("Grading the sources")
    candidates = state["candidates"]
    prompt = build_grader_prompt(state["question"], candidates)
    reply = get_llm().generate(GRADER_SYSTEM_PROMPT, prompt)
    grade = parse_json_reply(reply)

    # If the grader reply is broken, keep everything and answer, rather than looping
    if grade is None:
        return {
            "kept": state["kept"] + candidates,
            "verdict": "enough",
            "better_query": "",
            "steps": add_step(state, "grade", "Could not read the relevance check, so kept all sources"),
        }

    kept = list(state["kept"])
    kept_ids = set()
    for section in kept:
        kept_ids.add(section["parent_id"])

    newly_kept = 0
    for value in grade.get("relevant", []):
        # Some models send numbers as strings
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number < 1 or number > len(candidates):
            continue

        section = candidates[number - 1]
        if section["parent_id"] not in kept_ids:
            kept.append(section)
            kept_ids.add(section["parent_id"])
            newly_kept += 1

    verdict = grade.get("verdict", "partial")
    if verdict not in VERDICT_TEXT:
        verdict = "partial"

    text = "Kept " + str(newly_kept) + " of " + str(len(candidates)) + " sources, " + VERDICT_TEXT[verdict]
    return {
        "kept": kept,
        "verdict": verdict,
        "better_query": (grade.get("better_query") or "").strip(),
        "steps": add_step(state, "grade", text),
    }


def rewrite_node(state):
    return {
        "query": state["better_query"],
        "steps": add_step(state, "rewrite", "Searched again with a more specific query"),
    }


def generate_node(state):
    show_status("Writing the answer")
    write_event = get_stream_writer()
    sections = state["kept"]

    # Nothing passed the check: answer from the best candidates, the prompt
    # tells the model to say clearly what it could not find
    if len(sections) == 0:
        sections = state["candidates"][:3]

    sections = limit_per_document(sections, MAX_SECTIONS_IN_ANSWER)
    documents = group_by_document(sections)

    answer = ""
    for text in stream_answer_text(state["workspace_id"], state["question"], documents):
        answer += text
        write_event({"type": "token", "text": text})

    return {
        "answer": answer,
        "documents": documents,
        "steps": add_step(state, "answer", "Wrote the answer from " + count_text(len(documents), "source", "sources")),
    }


def read_unsupported_claims(reply):
    """Return the list of unsupported claims, or None if the reply cannot be read."""
    data = parse_json_reply(reply)
    if data is None or not isinstance(data.get("unsupported"), list):
        return None

    claims = []
    for item in data["unsupported"]:
        if isinstance(item, dict) and item.get("claim"):
            claims.append({"claim": str(item["claim"]), "reason": str(item.get("reason") or "")})
    return claims


def verify_node(state):
    """Check the finished answer against its sources. This only flags problems, it never changes the answer."""
    if not config.ANSWER_CHECK or len(state["documents"]) == 0:
        return {"check": None}

    show_status("Checking the answer against its sources")
    prompt = build_check_prompt(state["documents"], state["answer"])

    # The answer is already written, so a failed check must not lose it
    try:
        claims = read_unsupported_claims(get_llm().generate(CHECK_SYSTEM_PROMPT, prompt))
    except Exception as error:
        print("  answer check failed:", error)
        claims = None

    if claims is None:
        return {
            "check": {"status": "unknown", "unsupported": []},
            "steps": add_step(state, "check", "Could not check the answer"),
        }
    if len(claims) == 0:
        return {
            "check": {"status": "passed", "unsupported": []},
            "steps": add_step(state, "check", "Checked the answer: every claim is supported"),
        }
    return {
        "check": {"status": "flagged", "unsupported": claims},
        "steps": add_step(state, "flag", "Checked the answer: " + count_text(len(claims), "claim", "claims") + " may not be supported"),
    }
