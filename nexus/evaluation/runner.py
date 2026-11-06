import json
import os
from datetime import datetime

from nexus import config
from nexus.evaluation.judge import judge_answer
from nexus.evaluation.metrics import average, retrieval_recall
from nexus.pipelines import get_pipeline
from nexus.rag.hybrid_retriever import retrieve_sections
from nexus.rag.retriever import retrieve
from nexus.utils.jsonl import read_jsonl


def load_questions(workspace_id):
    return read_jsonl(config.eval_questions_file(workspace_id))


def retrieve_urls_only(workspace_id, pipeline_name, question):
    """Retrieval without any LLM call. Free to run as often as you like."""
    if pipeline_name == "baseline":
        results = retrieve(workspace_id, question, config.TOP_K)
    elif pipeline_name == "hybrid":
        results = retrieve_sections(workspace_id, question)
    else:
        raise ValueError("The agentic pipeline needs the LLM to pick sources, run it without retrieval-only")

    urls = []
    for result in results:
        if result["url"] not in urls:
            urls.append(result["url"])
    return urls


def evaluate_retrieval_only(workspace_id, pipeline_name, item):
    retrieved_urls = retrieve_urls_only(workspace_id, pipeline_name, item["question"])
    return {
        "id": item["id"],
        "question": item["question"],
        "type": item.get("type", ""),
        "recall": retrieval_recall(item["expected_sources"], retrieved_urls),
        "retrieved": retrieved_urls,
    }


def evaluate_full(workspace_id, pipeline_name, item):
    answer_question = get_pipeline(pipeline_name)
    result = answer_question(workspace_id, item["question"])

    retrieved_urls = []
    for source in result["sources"]:
        retrieved_urls.append(source["url"])

    is_correct, reason, coverage = judge_answer(item["question"], item["reference_answer"], result["answer"])

    return {
        "id": item["id"],
        "question": item["question"],
        "type": item.get("type", ""),
        "recall": retrieval_recall(item["expected_sources"], retrieved_urls),
        "correct": is_correct,
        "coverage": coverage,
        "judge_reason": reason,
        "seconds": result["seconds"],
        "steps": len(result["steps"]),
        "check": result["check"],
        "answer": result["answer"],
        "retrieved": retrieved_urls,
    }


def accuracy_for_type(results, question_type):
    total = 0
    correct = 0
    for result in results:
        if result["type"] == question_type:
            total += 1
            if result["correct"]:
                correct += 1

    if total == 0:
        return None
    return correct / total


def summarize(results, retrieval_only):
    recalls = []
    for result in results:
        recalls.append(result["recall"])

    summary = {
        "questions": len(results),
        "recall": average(recalls),
    }

    if not retrieval_only:
        correct_count = 0
        seconds = []
        coverages = []
        for result in results:
            if result["correct"]:
                correct_count += 1
            seconds.append(result["seconds"])
            coverages.append(result["coverage"])

        summary["accuracy"] = correct_count / len(results)
        summary["coverage"] = average(coverages)
        summary["single_hop_accuracy"] = accuracy_for_type(results, "single_hop")
        summary["multi_hop_accuracy"] = accuracy_for_type(results, "multi_hop")
        summary["average_seconds"] = average(seconds)

    return summary


def save_run(workspace_id, pipeline_name, model_name, summary, results, retrieval_only):
    folder = config.eval_results_dir(workspace_id)
    os.makedirs(folder, exist_ok=True)

    mode = "retrieval" if retrieval_only else "full"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(folder, timestamp + "_" + pipeline_name + "_" + mode + ".json")

    run = {
        "workspace": workspace_id,
        "pipeline": pipeline_name,
        "mode": mode,
        "model": model_name,
        "created_at": timestamp,
        "summary": summary,
        "results": results,
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(run, file, indent=2, ensure_ascii=False)
    return path


# Answers from a run that has not finished yet, one per line. If a run stops,
# for example at a daily quota limit, the next run continues from here.
def progress_file(workspace_id, pipeline_name, mode):
    return os.path.join(config.eval_results_dir(workspace_id), "unfinished_" + pipeline_name + "_" + mode + ".jsonl")


def format_percent(value):
    if value is None:
        return "n/a"
    return str(round(value * 100, 1)) + "%"


def print_summary(summary):
    print()
    print("Questions:          ", summary["questions"])
    print("Source recall:      ", format_percent(summary["recall"]))
    if "accuracy" in summary:
        print("Answer accuracy:    ", format_percent(summary["accuracy"]))
        print("Fact coverage:      ", format_percent(summary["coverage"]))
        print("  single-hop:       ", format_percent(summary["single_hop_accuracy"]))
        print("  multi-hop:        ", format_percent(summary["multi_hop_accuracy"]))
        print("Average seconds:    ", round(summary["average_seconds"], 2))


def run_eval(workspace_id, pipeline_name, limit=None, retrieval_only=False, report_progress=print):
    questions = load_questions(workspace_id)
    if len(questions) == 0:
        raise ValueError("No questions found in " + config.eval_questions_file(workspace_id))
    if limit:
        questions = questions[:limit]

    model_name = ""
    if not retrieval_only:
        from nexus.llm.provider import get_llm
        model_name = get_llm().name

    mode = "retrieval" if retrieval_only else "full"
    unfinished_path = progress_file(workspace_id, pipeline_name, mode)
    os.makedirs(os.path.dirname(unfinished_path), exist_ok=True)

    results_by_id = {}
    for result in read_jsonl(unfinished_path):
        results_by_id[result["id"]] = result

    with open(unfinished_path, "a", encoding="utf-8") as unfinished_file:
        for number, item in enumerate(questions, start=1):
            if item["id"] in results_by_id:
                continue
            report_progress("Question " + str(number) + " of " + str(len(questions)) + ": " + item["question"][:70])

            if retrieval_only:
                result = evaluate_retrieval_only(workspace_id, pipeline_name, item)
            else:
                result = evaluate_full(workspace_id, pipeline_name, item)

            results_by_id[item["id"]] = result
            unfinished_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            unfinished_file.flush()

    results = []
    for item in questions:
        results.append(results_by_id[item["id"]])

    summary = summarize(results, retrieval_only)
    path = save_run(workspace_id, pipeline_name, model_name, summary, results, retrieval_only)
    os.remove(unfinished_path)
    return summary, path
