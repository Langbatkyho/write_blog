import argparse
import sys
from pathlib import Path

# Add project root to sys.path to allow absolute imports of engine.*
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.utils import resolve_path
from engine.workflow import run_workflow, run_learning_loop

def main() -> int:
    parser = argparse.ArgumentParser(description="Run the mindful blog workflow.")
    parser.add_argument("--input", help="Path to the author input markdown file.")
    parser.add_argument(
        "--learn-from-run",
        help="Path to an existing run directory. Uses final_blog.md and production_blog.md to learn workflow improvements.",
    )
    parser.add_argument(
        "--production",
        help="Optional path to production_blog.md. Defaults to production_blog.md inside --learn-from-run.",
    )
    parser.add_argument(
        "--config",
        default="engine/config.local.yaml",
        help="Path to config YAML. Defaults to engine/config.local.yaml.",
    )
    parser.add_argument(
        "--client",
        choices=["openai", "antigravity"],
        default="openai",
        help="LLM Client to use. 'openai' (default) or 'antigravity'.",
    )
    parser.add_argument(
        "--client-map",
        help=(
            "Per-stage LLM client mapping. Format: 'stage1=client,stage2=client'. "
            "Valid clients: openai, antigravity. "
            "Stages not listed use --client as fallback."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Create run logs without calling the OpenAI endpoint.",
    )
    parser.add_argument(
        "--offline-learning",
        action="store_true",
        help="Run the learning loop with local text comparison instead of calling OpenAI.",
    )
    args = parser.parse_args()

    config_path = resolve_path(args.config)
    if not config_path.exists() and args.config == "engine/config.local.yaml":
        config_path = resolve_path("engine/config.example.yaml")

    from engine.client_router import build_client_map, create_routing_client

    fallback_client_name = args.client
    client_map = build_client_map(args.client_map, fallback_client_name)
    llm_client = create_routing_client(client_map, fallback_client_name)

    if args.learn_from_run:
        run_dir = resolve_path(args.learn_from_run)
        production_path = resolve_path(args.production) if args.production else None
        
        learning_dir = run_learning_loop(
            config_path=config_path,
            run_dir=run_dir,
            production_path=production_path,
            dry_run=args.dry_run,
            offline=args.offline_learning,
            llm_client=llm_client,
        )
        print(f"Learning run saved to: {learning_dir}")
        print(f"Learning report: {learning_dir / 'editorial_learning_report.md'}")
        return 0

    if not args.input:
        parser.error("--input is required unless --learn-from-run is used.")

    input_path = resolve_path(args.input)
    
    run_dir = run_workflow(
        config_path=config_path, 
        input_path=input_path, 
        dry_run=args.dry_run,
        llm_client=llm_client,
    )
    print(f"Workflow run saved to: {run_dir}")
    print(f"Full log: {run_dir / 'run_log.md'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
