# Nexus image: the full version (hybrid search with the embedding model and the reranker) for any Docker host.
# It starts with the demo workspaces already indexed. Set an API key (for example GEMINI_API_KEY) to give
# the server its own model; without one, visitors bring their own key in the sidebar or get search results only.
# It needs about 1 GB of memory.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    FASTEMBED_CACHE_PATH=/app/.cache/fastembed

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Unpack the demo workspaces and build their search index now, and download the reranker,
# so the first visitor does not wait for any of it
RUN python main.py load-snapshot \
 && python -c "from nexus.rag.reranker import get_model; get_model()"

# Run as a normal user (not root); it must be able to write data/ and evals/
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

EXPOSE 8000
CMD ["python", "main.py", "serve"]
