import json
import os

from nexus import config
from nexus.evaluation.runner import format_percent
from nexus.pipelines import PIPELINES


def load_latest_runs(workspace_id, mode):
    """The newest saved run of each pipeline. File names start with a timestamp, so sorting works."""
    latest = {}
    folder = config.eval_results_dir(workspace_id)
    if not os.path.exists(folder):
        return latest

    for file_name in sorted(os.listdir(folder)):
        if not file_name.endswith("_" + mode + ".json"):
            continue

        with open(os.path.join(folder, file_name), "r", encoding="utf-8") as file:
            run = json.load(file)
        latest[run["pipeline"]] = run

    return latest


def comparison_rows(workspace_id, mode):
    """One row per pipeline, in the order baseline, hybrid, agentic, so it reads as a progression."""
    runs = load_latest_runs(workspace_id, mode)

    rows = []
    for pipeline_name in PIPELINES:
        if pipeline_name not in runs:
            continue
        run = runs[pipeline_name]
        row = dict(run["summary"])
        row["pipeline"] = pipeline_name
        row["model"] = run.get("model", "")
        row["created_at"] = run["created_at"]
        rows.append(row)
    return rows


def print_comparison(workspace_id, mode):
    rows = comparison_rows(workspace_id, mode)
    if len(rows) == 0:
        print("No saved " + mode + " runs yet for " + workspace_id + ". Run `python main.py eval` first.")
        return

    if mode == "full":
        print("| Pipeline | Source recall | Accuracy | Fact coverage | Single-hop | Multi-hop | Avg seconds |")
        print("|---|---|---|---|---|---|---|")
    else:
        print("| Pipeline | Source recall |")
        print("|---|---|")

    for row in rows:
        line = "| " + row["pipeline"] + " | " + format_percent(row["recall"])
        if mode == "full":
            line += " | " + format_percent(row["accuracy"])
            line += " | " + format_percent(row.get("coverage"))
            line += " | " + format_percent(row["single_hop_accuracy"])
            line += " | " + format_percent(row["multi_hop_accuracy"])
            line += " | " + str(round(row["average_seconds"], 1))
        line += " |"
        print(line)
