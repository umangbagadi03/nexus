from nexus.agent import pipeline as agentic
from nexus.rag import baseline, hybrid

# Each pipeline adds on top of the previous one, so the evals show what each step is worth.
# Every pipeline is called as answer_question(workspace_id, question).
PIPELINES = {
    "baseline": baseline.answer_question,
    "hybrid": hybrid.answer_question,
    "agentic": agentic.answer_question,
}

# The same pipelines, sending their progress while they work
STREAMING_PIPELINES = {
    "baseline": baseline.stream_answer,
    "hybrid": hybrid.stream_answer,
    "agentic": agentic.stream_answer,
}

DEFAULT_PIPELINE = "agentic"


def check_pipeline_name(name):
    if name not in PIPELINES:
        names = ", ".join(PIPELINES.keys())
        raise ValueError("Unknown pipeline '" + name + "'. Use one of: " + names)


def get_pipeline(name):
    check_pipeline_name(name)
    return PIPELINES[name]


def get_streaming_pipeline(name):
    check_pipeline_name(name)
    return STREAMING_PIPELINES[name]
