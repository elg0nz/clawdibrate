"""Entry point for transcript-based AGENTS.md calibration."""

import sys
from pathlib import Path

from .cli import build_parser
from .env_bootstrap import load_clawdibrate_env
from .modes import resolve_mode_defaults, run_idempotency_check, run_max_mode, run_progressive_mode
from .orchestrator import calibrate, resolve_default_calibration_agent
from .scores import show_scores


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = (args.repo or Path.cwd()).resolve()
    load_clawdibrate_env(repo_root)
    agent_name = args.agent or resolve_default_calibration_agent()
    resolve_mode_defaults(args)

    if args.scores:
        show_scores(repo_root)
        sys.exit(0)

    if args.check_idempotent:
        run_idempotency_check(args, agent_name)
        return

    if args.setup:
        from .instruction_files import ensure_clawdibrate_setup

        result = ensure_clawdibrate_setup(repo_root)
        print(f"Active instruction file: {result['active_path']}")
        if result["created_pointer"]:
            print(f"Created pointer file: {result['created_pointer']}")
        if result.get("skills_installed"):
            print("Skills installed: record-start, record-stop, record-from-git, loop")
        if result.get("permissions_configured"):
            print("Permissions configured: .claude/settings.json")
        return

    if args.dump_session:
        from .session_dump import dump_session

        output = dump_session(
            repo_root=repo_root,
            session_id=args.session_id,
            output_path=args.transcript,
            agent=agent_name,
        )
        print(output)
        return

    if args.compress:
        from .compress import run_compress_advisor
        from .instruction_files import detect_instruction_file

        instruction_result = detect_instruction_file(repo_root)
        if instruction_result is None:
            print("No instruction file found.")
            return
        run_compress_advisor(instruction_result["active"]["path"])
        return

    if args.synthesize_git_history:
        from .git_history import synthesize_transcript_from_git

        output = synthesize_transcript_from_git(
            repo_root=repo_root,
            files=tuple(args.git_files) if args.git_files else None,
            limit=args.git_limit,
            output_path=args.transcript,
        )
        print(output)
        return

    if args.mode == "progressive":
        run_progressive_mode(args, agent_name, repo_root)
        return
    if args.mode == "max":
        run_max_mode(args, agent_name, repo_root)
        return

    calibrate(
        agent=agent_name,
        transcript_path=args.transcript,
        repo_root=args.repo,
        dry_run=args.dry_run,
        holdout_ratio=args.holdout_ratio,
        staleness_halflife_days=args.staleness_halflife_days,
        max_transcripts=args.max_transcripts,
        token_budget=args.token_budget,
        workers=args.workers,
        model=args.model,
        auto_section_skills=not args.no_auto_section_skills,
        run_mode=args.mode,
        target_score=args.target_score,
    )


if __name__ == "__main__":
    main()
