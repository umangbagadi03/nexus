import os

from dotenv import load_dotenv

load_dotenv()


# Folders
DATA_DIR = "data"
QDRANT_DIR = os.path.join(DATA_DIR, "qdrant")
WORKSPACES_FILE = os.path.join(DATA_DIR, "workspaces.json")
EVALS_DIR = "evals"


def workspace_dir(workspace_id):
    return os.path.join(DATA_DIR, "workspaces", workspace_id)


def raw_dir(workspace_id):
    return os.path.join(workspace_dir(workspace_id), "raw")


def uploads_dir(workspace_id, source_id):
    return os.path.join(workspace_dir(workspace_id), "uploads", source_id)


def index_dir(workspace_id):
    return os.path.join(workspace_dir(workspace_id), "index")


def eval_questions_file(workspace_id):
    return os.path.join(EVALS_DIR, workspace_id, "questions.jsonl")


def eval_results_dir(workspace_id):
    return os.path.join(EVALS_DIR, workspace_id, "results")


# Access tokens for connectors (optional, they raise the API rate limits)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")


# How PDFs are read: "pypdf" is light and fast, "docling" handles tables and scans
PDF_PARSER = os.getenv("PDF_PARSER", "pypdf").strip().lower()


# The agent checks its answer against its sources, which costs one more LLM call per answer.
# Set ANSWER_CHECK=false to turn it off, for example to stay within a free tier's limits.
ANSWER_CHECK = os.getenv("ANSWER_CHECK", "true").strip().lower() != "false"


# Indexing and retrieval
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
TOP_K = 5


# LLM providers. Leave LLM_PROVIDER empty to pick one from whichever API key is set.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Other models to try, in order, when GEMINI_MODEL is busy or out of quota. Limits are per model.
GEMINI_FALLBACK_MODELS = []
for fallback_model in os.getenv("GEMINI_FALLBACK_MODELS", "").split(","):
    if fallback_model.strip():
        GEMINI_FALLBACK_MODELS.append(fallback_model.strip())

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
