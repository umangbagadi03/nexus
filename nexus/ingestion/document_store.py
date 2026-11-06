import os

from nexus import config
from nexus.utils.jsonl import read_jsonl, write_jsonl

# The latest documents of every source, one JSONL file per source.
# The link graph and the evals read from here.


def source_file(workspace_id, source_id):
    return os.path.join(config.raw_dir(workspace_id), source_id + ".jsonl")


def save_source_documents(workspace_id, source_id, documents):
    write_jsonl(source_file(workspace_id, source_id), documents)


def delete_source_documents(workspace_id, source_id):
    path = source_file(workspace_id, source_id)
    if os.path.exists(path):
        os.remove(path)


def load_all_documents(workspace_id):
    folder = config.raw_dir(workspace_id)
    if not os.path.exists(folder):
        return []

    documents = []
    for file_name in sorted(os.listdir(folder)):
        if file_name.endswith(".jsonl"):
            documents.extend(read_jsonl(os.path.join(folder, file_name)))
    return documents


def count_by_kind(workspace_id):
    counts = {}
    for document in load_all_documents(workspace_id):
        kind = document["kind"]
        counts[kind] = counts.get(kind, 0) + 1
    return counts
