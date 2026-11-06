import argparse

PIPELINE_NAMES = ["baseline", "hybrid", "agentic"]


def setup_demo_command(args):
    from nexus.ingestion.pipeline import sync_source
    from nexus.workspaces.demo import create_demo_workspaces
    from nexus.workspaces import store

    new_sources = create_demo_workspaces()
    if len(new_sources) == 0:
        print("The demo workspaces already exist. Use `python main.py sync <workspace>` to refresh them.")
        return

    for workspace_id, source_id in new_sources:
        print("Syncing", workspace_id, "/", source_id)
        sync_source(workspace_id, source_id)
        source = store.get_source(workspace_id, source_id)
        print("  ", source["status"] + ":", source["message"])


def workspaces_command(args):
    from nexus.workspaces import store

    for workspace in store.list_workspaces():
        print(workspace["id"], "-", workspace["name"])
        for source in workspace["sources"]:
            print("   ", source["id"], "(" + source["type"] + ")", source["documents"], "documents,", source["status"])


def sync_command(args):
    from nexus.ingestion.pipeline import sync_source
    from nexus.workspaces import store

    workspace = store.get_workspace(args.workspace)
    if workspace is None:
        print("No workspace called", args.workspace)
        return

    for source in workspace["sources"]:
        if args.source and source["id"] != args.source:
            continue
        print("Syncing", source["id"])
        sync_source(args.workspace, source["id"])
        print("  ", store.get_source(args.workspace, source["id"])["message"])


def ask_command(args):
    from nexus.pipelines import get_pipeline

    answer_question = get_pipeline(args.pipeline)
    result = answer_question(args.workspace, args.question)

    if result["steps"]:
        print()
        print("Steps:")
        for step in result["steps"]:
            print("  -", step["text"])

    print()
    print(result["answer"])
    check = result["check"]
    if check:
        print()
        print("Answer check:", check["status"])
        for claim in check["unsupported"]:
            print("  -", claim["claim"], "(" + claim["reason"] + ")")

    print()
    print("Sources:")
    for source in result["sources"]:
        print("  [" + str(source["citation"]) + "]", source["title"], "-", source["label"])
        print("     ", source["url"])
    print()
    print("Answered by", result["model"], "in", result["seconds"], "seconds")


def eval_command(args):
    from nexus.evaluation.runner import print_summary, run_eval

    summary, path = run_eval(args.workspace, args.pipeline, limit=args.limit, retrieval_only=args.retrieval_only)
    print_summary(summary)
    print("Saved to", path)


def compare_command(args):
    from nexus.evaluation.compare import print_comparison

    print_comparison(args.workspace, args.mode)


def serve_command(args):
    import uvicorn

    uvicorn.run("nexus.api.server:app", host="127.0.0.1", port=args.port)


def main():
    parser = argparse.ArgumentParser(description="Nexus: ask questions across your company's docs, files and tickets")
    commands = parser.add_subparsers(dest="command", required=True)

    setup_parser = commands.add_parser("setup-demo", help="create and sync the GitLab Handbook and LangGraph workspaces")
    setup_parser.set_defaults(handler=setup_demo_command)

    list_parser = commands.add_parser("workspaces", help="list workspaces and their sources")
    list_parser.set_defaults(handler=workspaces_command)

    sync_parser = commands.add_parser("sync", help="fetch and index the sources of a workspace")
    sync_parser.add_argument("workspace")
    sync_parser.add_argument("--source", help="only sync this source")
    sync_parser.set_defaults(handler=sync_command)

    ask_parser = commands.add_parser("ask", help="ask a question from the terminal")
    ask_parser.add_argument("workspace")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--pipeline", default="agentic", choices=PIPELINE_NAMES)
    ask_parser.set_defaults(handler=ask_command)

    eval_parser = commands.add_parser("eval", help="run the evaluation set of a workspace")
    eval_parser.add_argument("workspace")
    eval_parser.add_argument("--pipeline", default="agentic", choices=PIPELINE_NAMES)
    eval_parser.add_argument("--limit", type=int, default=None, help="only run the first N questions")
    eval_parser.add_argument("--retrieval-only", action="store_true", help="only check retrieval, makes no LLM calls")
    eval_parser.set_defaults(handler=eval_command)

    compare_parser = commands.add_parser("compare", help="print the latest eval results of each pipeline as a table")
    compare_parser.add_argument("workspace")
    compare_parser.add_argument("--mode", default="full", choices=["full", "retrieval"])
    compare_parser.set_defaults(handler=compare_command)

    serve_parser = commands.add_parser("serve", help="start the web app")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.set_defaults(handler=serve_command)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
