"""CLI for the Codex Cloud stage protocol. No provider API calls."""

import argparse
import json
from pathlib import Path

from engine.cloud_stages import create_run, finalize_blog, prepare_stage, submit_stage, verify_run, recover_run
from engine.cloud_transfer import export_run, import_run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "prepare", "submit", "finalize", "export", "import", "verify", "recover"])
    parser.add_argument("--config", type=Path, default=Path("engine/config.example.yaml"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--mode", choices=["moment", "deep"], default="moment")
    parser.add_argument("--style", default="reflective")
    parser.add_argument("--stage-id")
    parser.add_argument("--token")
    parser.add_argument("--response-file", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--approved-file", type=Path)
    args = parser.parse_args()
    if args.action == "create":
        if args.input is None or args.output_root is None:
            parser.error("create requires --input and --output-root")
        result = {"run_dir": str(create_run(args.config, args.input, args.output_root, mode=args.mode, style=args.style))}
    elif args.action == "prepare":
        if args.run_dir is None:
            parser.error("prepare requires --run-dir")
        result = prepare_stage(args.run_dir, args.config)
    elif args.action == "submit":
        if not all((args.run_dir, args.stage_id, args.token, args.response_file)):
            parser.error("submit requires --run-dir, --stage-id, --token and --response-file")
        result = submit_stage(args.run_dir, args.config, args.stage_id, args.token, args.response_file.read_text(encoding="utf-8"))
    elif args.action == "finalize":
        if args.run_dir is None or args.approved_file is None:
            parser.error("finalize requires --run-dir and --approved-file")
        result = {"final_blog": str(finalize_blog(args.run_dir, args.config, args.approved_file)),
                  "run_log": str(args.run_dir / "run_log.md")}
    elif args.action in {"verify", "recover"}:
        if args.run_dir is None:
            parser.error(f"{args.action} requires --run-dir")
        result = verify_run(args.run_dir, args.config) if args.action == "verify" else recover_run(args.run_dir, args.config)
    elif args.action == "export":
        if args.run_dir is None or args.archive is None:
            parser.error("export requires --run-dir and --archive")
        result = {"archive": str(export_run(args.run_dir, args.archive))}
    else:
        if args.archive is None or args.output_root is None:
            parser.error("import requires --archive and --output-root")
        result = {"run_dir": str(import_run(args.archive, args.output_root))}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
