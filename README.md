# Nexus

Nexus is a knowledge assistant for companies. Connect the places where knowledge lives (handbooks, docs, uploaded files, GitHub issues and pull requests, or anything a script can send) and people can ask questions in plain language. Every answer cites the documents it came from, and shows the steps the agent took to find them.

Since a portfolio project has no company data of its own, it ships with three sample workspaces, two built from public data:

- **GitLab Handbook.** GitLab publishes its internal company handbook. The workspace uses about 120 pages: people policies, time off, benefits, communication and incident management.
- **LangGraph.** An engineering team's knowledge: the LangGraph docs plus 300 recent GitHub issues and pull requests, which link to each other.
- **Acme Benefits.** One small sample PDF for a fictional company, with tables and a scanned page, to show file uploads.

Everything runs on a laptop. Embeddings, keyword search, the reranker and the vector database run locally. The LLM can be Gemini, Claude, OpenAI or a local Ollama model, chosen by whichever API key is set.

## Connecting data

Every source is a connector that returns documents in one shared format. After that, chunking, embedding, the link graph and search are the same for every source.

| Connector | What it reads |
|---|---|
| Uploaded files | PDF (read with pypdf or Docling), Word, Markdown and text files, uploaded in the web app |
| Markdown repository | Docs, wikis and handbooks kept as markdown in a GitHub or GitLab repository |
| GitHub issues | Issues and pull requests with their comments |
| Push API | Anything another system sends to `POST /api/workspaces/{id}/documents` |

Push API example:

```bash
curl -X POST http://127.0.0.1:8000/api/workspaces/gitlab-handbook/documents \
  -H "Content-Type: application/json" \
  -d '{"source_name": "Confluence export", "documents": [{"id": "onboarding", "title": "Onboarding guide", "text": "## First week\n..."}]}'
```

To add a pull-based source such as Confluence, Notion or Google Drive, subclass `Connector` in `nexus/connectors/base.py`, implement `fetch()`, and register it in `nexus/connectors/registry.py`.

**Syncing is incremental.** Each document gets a fingerprint. A sync only embeds documents that are new or changed, removes documents that disappeared from the source, and skips the rest.

### Reading PDFs

`PDF_PARSER` in `.env` chooses how PDFs are read. Both keep one section per page, so citations and the rest of the pipeline stay the same.

| | `pypdf` (default) | `docling` (optional) |
|---|---|---|
| Install | Included | `pip install -r requirements-docling.txt` (adds PyTorch and AI models) |
| Tables | Cells come out one per line | Kept as Markdown tables, with merged headers resolved |
| Scanned pages | Skipped | Read with OCR |
| Sample PDF, 3 pages | Under 1 second | About 30 to 60 seconds on an 8 GB laptop, about 1.1 GB of memory |

Tested on the Acme sample PDF with the `hybrid` pipeline, answer accuracy was 80% with pypdf and 100% with Docling. The whole gap came from the two questions on the scanned page. The LLM could still read pypdf's flattened tables, though on 11 checks that a table row or scanned fact was extracted intact, pypdf passed 2 and Docling passed 11. The PDF is generated and has clean tables, so real documents may score differently.

## How answers are found

There are three pipelines. Each one adds to the previous one, so the evaluation shows what every step is worth.

| Pipeline | Retrieval | Answering |
|---|---|---|
| `baseline` | Small chunks, vector search only. No keyword search, reranker or parent sections | One LLM call |
| `hybrid` | Section-aware parent and child chunks, dense + BM25 search merged with Reciprocal Rank Fusion, cross-encoder reranker | One LLM call |
| `agentic` | Everything in `hybrid`, plus link-graph expansion | LangGraph agent that grades relevance, rewrites the query and searches again when needed, then checks its answer against the sources |

### Indexing

- **Parent and child chunks.** Pages are split at their headings, PDFs at their pages and issue threads at each comment. These sections are the parents. Each parent is split into children of about 700 characters. Children are searched because small pieces match precisely, and their parent section is what the LLM reads.
- **Two vectors per child.** A dense vector (`bge-small-en-v1.5`) for meaning, and a BM25 sparse vector for exact terms like policy names, error codes or `#9547`.
- **Link graph.** Links between documents are extracted from the text: `Fixes #123` in a pull request, issue mentions, and links between pages. They are stored as a directed graph with networkx.

### The agent

```
question -> retrieve -> expand_links -> grade --enough--> generate -> verify
               ^                          |
               |                       missing
               +-------- rewrite <--------+
```

1. **retrieve**: hybrid search, rerank the top 30 children, return their parent sections.
2. **expand_links**: for the top results, add linked documents from the graph, such as a pull request linked to an issue or a page the policy refers to.
3. **grade**: one LLM call that marks which sources are relevant and decides whether they are enough. If not, it suggests a better search query.
4. **rewrite**: search again with that query. At most three searches in total.
5. **generate**: answer only from the kept sources, with citations. The answer streams to the browser as it is written.
6. **verify**: one more LLM call checks each claim against its sources. It only flags problems and never changes the answer, and a failed check keeps the answer. Set `ANSWER_CHECK=false` to turn it off. It flagged few real mistakes in the evals, so "passed" does not mean "true".

### Streaming

Every pipeline yields events: `status`, `step` (a finished agent step), `token` (the next piece of the answer) and `result`. `POST /api/workspaces/{id}/ask/stream` sends them as one JSON object per line, and an `error` event if the LLM fails after the response has started. `POST /api/workspaces/{id}/ask` still returns the finished answer in one reply.

## Evaluation

Each workspace has its own question set in `evals/<workspace>/questions.jsonl`. Every question has a reference answer written by hand from the source pages, and the URLs of the pages that contain the answer. Some questions need two linked documents to answer.

- **Source recall**: how many of the expected sources were in what the pipeline used. This needs no LLM, so it can be run after every change.
- **Answer accuracy**: an LLM judge lists the facts in the reference answer and marks each one as core or supporting. An answer is correct if every core fact is there and nothing contradicts the reference.
- **Fact coverage**: the share of all facts the answer contains.

Evals save progress after every question, so a run that stops at a quota limit continues where it left off.

`python main.py compare <workspace>` prints the latest results of each pipeline. The Evaluations page in the web app shows the same table.

### Results

All pipelines and the judge ran on one model, `gemini-3.1-flash-lite`.

| Workspace | Pipeline | Source recall | Answer accuracy | Fact coverage | Avg time |
|---|---|---|---|---|---|
| GitLab Handbook (12 questions) | `baseline` | 83.3% | 50.0% | 74.5% | 6.5 s |
| | `hybrid` | 87.5% | 41.7% | 73.5% | 7.0 s |
| | `agentic` | 95.8% | 58.3% | 77.2% | 27.9 s |
| LangGraph (14 questions) | `baseline` | 75.0% | 71.4% | 82.6% | 7.2 s |
| | `hybrid` | 100% | 78.6% | 87.3% | 4.7 s |
| | `agentic` | 96.4% | 78.6% | 94.9% | 17.3 s |

What this shows:

- **Retrieval clearly improved.** Source recall rose on both workspaces from `baseline` to `hybrid`.
- **Answers improved only a little.** Across 26 questions, `baseline` and `hybrid` each got 16 correct, and `agentic` got 18. That gap is small enough to be noise.
- **The agent costs more.** It had the highest fact coverage, but it took about 4 times as long as `hybrid`. Those times include waiting on rate limits and overloads.
- **The search-again loop rarely runs.** It ran on 1 of 36 questions, counting the sample PDF. That one was a real win: `hybrid` missed the right page for "How many vacation days do I get?", and the agent searched again and got it. The link graph's own benefit has not been measured separately.
- **The answer check is a weak signal.** It flagged 1 of the agent's 8 wrong answers on these 26 questions, with 3 false alarms. Most mistakes were missing facts, and it only looks for unsupported claims.

The evals also caught a real bug: the model read a pull request marked closed as fixed. The prompt now says closed means not merged, though `hybrid` still got one such question wrong.

The sets are small and the judge is imperfect. It agreed with a hand-checked verdict on 8 of 11 hard test cases, so one or two questions either way could be noise.

## Setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

To read PDF tables and scanned pages, also run `pip install -r requirements-docling.txt` and set `PDF_PARSER=docling` in `.env`.

Add one API key to `.env`. Gemini's free tier is enough for trying it out, but its daily limits differ a lot by model. On the key used here, `gemini-2.5-flash` allowed 20 requests a day and `gemini-3.5-flash-lite` allowed 500, which is why that is the default. A full eval run needs about 300 requests. With no key, Nexus uses Ollama (`ollama pull llama3.2:3b`).

Then create the sample workspaces. This downloads the data and builds the indexes, which takes a while the first time:

```bash
python main.py setup-demo
python main.py serve        # http://127.0.0.1:8000
```

## Commands

```bash
python main.py workspaces                              # list workspaces and sources
python main.py sync gitlab-handbook                    # fetch and index what changed
python main.py ask gitlab-handbook "How many vacation days do I get?"
python main.py eval gitlab-handbook --pipeline hybrid --retrieval-only
python main.py eval gitlab-handbook --pipeline agentic
python main.py compare gitlab-handbook
```

Qdrant runs in local mode, which allows one process at a time to open `data/qdrant`. Stop the web server before running `sync`, `ask` or `eval` from the terminal, or do those from the web app.

## Tests

The tests cover plain logic, so they need no API key or internet:

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

## Project layout

```
main.py                      command line entry point
nexus/
  config.py                  settings, read from .env
  workspaces/                workspaces and their sources, the sample workspaces
  connectors/                one file per connector, plus file parsers and markdown cleanup
  ingestion/                 sync pipeline: fetch, store, index what changed, rebuild links
  indexing/                  chunking, dense and sparse embeddings, Qdrant, incremental indexer
  graph/                     link graph between documents
  rag/                       retrievers, reranker, prompts, baseline and hybrid pipelines
  agent/                     LangGraph agent: state, nodes, graph wiring
  llm/                       one client per provider, picked from the API keys in .env
  evaluation/                eval runner, LLM judge, metrics, comparison table
  api/                       FastAPI routes for workspaces, sources, uploads, push API, evals
web/                         the web app: HTML, CSS and JavaScript modules, no build step
evals/<workspace>/           question sets and saved eval runs
demo_data/                   the sample PDF for the Acme Benefits workspace
tests/                       unit tests for chunking, links, the judge, the answer check and model routing
```

## Design choices

- **No Neo4j or Elasticsearch.** Qdrant does dense and BM25 search in one collection, and the link graph is small enough for networkx. Nothing needs Docker.
- **LangGraph only for the agent.** The nodes call small provider clients written for this project instead of LangChain model wrappers, which keeps switching between Gemini, Claude, OpenAI and Ollama to one file per provider.
- **Gemini model routing.** Free tier limits are per model, so `GEMINI_FALLBACK_MODELS` lists models to try when one is out of quota or overloaded. Leave it empty for evals, so every pipeline is compared on the same model.
- **Streaming over plain HTTP.** The browser sends one request and gets many pieces back, so JSON lines over `fetch` are enough. No WebSockets or queue.
- **Grading in one call.** The grader judges all sources in a single request instead of one request per source, which matters on rate-limited free tiers.
- **Local embeddings and reranker.** Indexing and retrieval cost nothing and can be rerun freely, so retrieval experiments do not need an API key.
- **Per-workspace collections.** Each workspace has its own Qdrant collections, parent sections and link graph, so workspaces never see each other's documents.

## Limitations

- There is no user login or per-document permissions yet. Everyone who can open the app can search every workspace.
- With the default `pypdf` parser, scanned PDFs are skipped and table rows are flattened. Docling fixes both, but it is much slower and needs more memory.
- Every question starts fresh. Follow-up questions are not supported yet.
- The answer check is a weak signal, so "passed" does not mean "true".
- The LLM judge is noisy and uses the same model as the pipeline. A stronger, separate judge model would be more reliable.
- Issue states in the reference answers reflect the time the data was fetched.
