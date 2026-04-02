"""Entry point for transcript-based AGENTS.md calibration."""

import argparse
from pathlib import Path

from .git_history import synthesize_transcript_from_git
from .instruction_files import (
    ensure_clawdibrate_setup,
)
from .compress import run_compress_advisor
from .env_bootstrap import load_clawdibrate_env
from .orchestrator import (
    calibrate,
    estimate_iterations_to_target,
    resolve_default_calibration_agent,
)
from .session_dump import dump_session


def _resolve_mode_defaults(args: argparse.Namespace) -> None:
    """Apply opinionated defaults for fast/progressive/max while preserving explicit flags."""
    mode = args.mode
    explicit_max_transcripts = args.max_transcripts is not None
    explicit_workers = args.workers != 4
    explicit_auto_skills = args.no_auto_section_skills

    if mode == "fast":
        if not explicit_max_transcripts:
            args.max_transcripts = 8
        if not explicit_workers:
            args.workers = min(4, max(1, args.workers))
        if not explicit_auto_skills:
            args.no_auto_section_skills = True
    elif mode == "progressive":
        if not explicit_workers:
            args.workers = 1
        if not explicit_auto_skills:
            args.no_auto_section_skills = True
    elif mode == "max":
        if not explicit_workers:
            args.workers = max(2, args.workers)


def _list_transcripts(repo_root: Path) -> list[Path]:
    transcripts_dir = repo_root / ".clawdibrate" / "transcripts"
    if not transcripts_dir.exists():
        return []
    return sorted(transcripts_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def _run_progressive_mode(args: argparse.Namespace, agent_name: str, repo_root: Path) -> None:
    """Run many small, cancel-safe calibrations over recent transcripts."""
    transcripts = _list_transcripts(repo_root)
    if not transcripts:
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
            run_iteration=1,
            target_score=args.target_score,
        )
        return

    max_iters = args.max_iterations or min(20, len(transcripts))
    no_change_streak = 0
    print(
        f"Progressive mode: up to {max_iters} step(s), "
        f"batch_size={args.progressive_batch_size}, cancellable at any time."
    )
    try:
        for i in range(max_iters):
            batch = transcripts[i * args.progressive_batch_size:(i + 1) * args.progressive_batch_size]
            if not batch:
                break
            print(f"\n[progressive] iteration {i + 1}/{max_iters} using {len(batch)} transcript(s)")
            changed_this_iter = False
            for t in batch:
                result = calibrate(
                    agent=agent_name,
                    transcript_path=t,
                    repo_root=args.repo,
                    dry_run=args.dry_run,
                    holdout_ratio=args.holdout_ratio,
                    staleness_halflife_days=args.staleness_halflife_days,
                    max_transcripts=None,
                    token_budget=args.token_budget,
                    workers=args.workers,
                    model=args.model,
                    auto_section_skills=not args.no_auto_section_skills,
                    run_mode=args.mode,
                    run_iteration=i + 1,
                    target_score=args.target_score,
                )
                changed_this_iter = changed_this_iter or bool(result.get("changed"))

            est = estimate_iterations_to_target(repo_root / ".clawdibrate" / "history", target_score=args.target_score)
            print(
                f"[progressive] estimate: remaining="
                f"{est.get('iterations_remaining') if est.get('iterations_remaining') is not None else 'unknown'} "
                f"(current={est.get('current_avg', 0.0):.3f}, trend={est.get('slope_per_run', 0.0):+.4f}/run)"
            )
            if changed_this_iter:
                no_change_streak = 0
            else:
                no_change_streak += 1
                if no_change_streak >= 3:
                    print("[progressive] no changes for 3 iterations, stopping.")
                    break
    except KeyboardInterrupt:
        print("\nProgressive mode cancelled by user; all completed mini-iterations remain committed.")


def _run_max_mode(args: argparse.Namespace, agent_name: str, repo_root: Path) -> None:
    """Run until target optimization is reached or trend plateaus."""
    max_iters = args.max_iterations or 25
    no_change_streak = 0
    print(f"Max mode: target_score={args.target_score:.2f}, max_iterations={max_iters}")
    try:
        for i in range(max_iters):
            result = calibrate(
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
                run_iteration=i + 1,
                target_score=args.target_score,
            )
            estimate = result.get("estimate", {})
            remaining = estimate.get("iterations_remaining")
            print(
                f"[max] iteration {i + 1}: avg={result.get('avg_score', 0.0):.3f}, "
                f"optimized={result.get('optimized')}, remaining={remaining if remaining is not None else 'unknown'}"
            )
            if result.get("optimized"):
                print("[max] optimization target reached.")
                break
            if result.get("changed"):
                no_change_streak = 0
            else:
                no_change_streak += 1
                if no_change_streak >= 2:
                    print("[max] no additional improvements detected across 2 runs; stopping.")
                    break
        else:
            print("[max] reached max iterations.")
    except KeyboardInterrupt:
        print("\nMax mode cancelled by user; completed iterations remain committed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clawdibrate transcript-based AGENTS.md calibration"
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["calibrate"],
        help="Optional alias for the default calibration command",
    )
    parser.add_argument(
        "--agent",
        default=None,
        help="CLI agent to use (default: claude; repo .clawdibrate/env or CLAWDIBRATE_AGENT or --agent)",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=None,
        help="Path to a specific .jsonl transcript file",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Target repository root containing AGENTS.md or CLAUDE.md",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without mutating AGENTS.md",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Configure the target repo to use clawdibrate and create a pointer file when needed",
    )
    parser.add_argument(
        "--synthesize-git-history",
        action="store_true",
        help="Create a bootstrap transcript from recent git history instead of calibrating",
    )
    parser.add_argument(
        "--git-limit",
        type=int,
        default=20,
        help="Number of recent relevant commits to include when synthesizing from git",
    )
    parser.add_argument(
        "--git-files",
        nargs="+",
        default=None,
        help="Tracked instruction files to mine from git history",
    )
    parser.add_argument(
        "--holdout-ratio",
        type=float,
        default=0.2,
        help="Fraction of transcripts to hold out for overfitting detection (default: 0.2)",
    )
    parser.add_argument(
        "--staleness-halflife-days",
        type=float,
        default=30.0,
        help="Half-life in days for transcript recency decay (default: 30)",
    )
    parser.add_argument(
        "--max-transcripts",
        type=int,
        default=None,
        help="Maximum number of transcripts to process per calibration run (default: all)",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help="Optional hard cap on total file tokens; default none (no rejections; compression if file grows past pre-run size)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4, 1 = sequential)",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Model for parallel workers (default: sonnet)",
    )
    parser.add_argument(
        "--dump-session",
        action="store_true",
        help="Convert the most recent Claude Code session into a clawdibrate transcript",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Specific Claude Code session UUID to dump (default: most recent)",
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Run compression advisor on the instruction file and print suggestions",
    )
    parser.add_argument(
        "--no-auto-section-skills",
        action="store_true",
        help="Do not create src/skills/*, replace sections with pointers, or run npx skills add",
    )
    parser.add_argument(
        "--mode",
        choices=["standard", "fast", "progressive", "max"],
        default="standard",
        help="Calibration mode: standard, fast, progressive (cancel-safe mini-runs), or max (run until optimized/plateau)",
    )
    parser.add_argument(
        "--target-score",
        type=float,
        default=0.9,
        help="Optimization target score for progressive/max mode estimates (default: 0.9)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum iterations for progressive/max mode",
    )
    parser.add_argument(
        "--progressive-batch-size",
        type=int,
        default=1,
        help="How many transcripts to process per progressive iteration (default: 1)",
    )

    args = parser.parse_args()
    repo_root = (args.repo or Path.cwd()).resolve()
    load_clawdibrate_env(repo_root)
    agent_name = args.agent or resolve_default_calibration_agent()
    _resolve_mode_defaults(args)
    if args.setup:
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
        output = dump_session(
            repo_root=repo_root,
            session_id=args.session_id,
            output_path=args.transcript,
            agent=agent_name,
        )
        print(output)
        return

    if args.compress:
        from .instruction_files import detect_instruction_file
        instruction_result = detect_instruction_file(repo_root)
        if instruction_result is None:
            print("No instruction file found.")
            return
        run_compress_advisor(instruction_result["active"]["path"])
        return

    if args.synthesize_git_history:
        output = synthesize_transcript_from_git(
            repo_root=repo_root,
            files=tuple(args.git_files) if args.git_files else None,
            limit=args.git_limit,
            output_path=args.transcript,
        )
        print(output)
        return

    if args.mode == "progressive":
        _run_progressive_mode(args, agent_name, repo_root)
        return
    if args.mode == "max":
        _run_max_mode(args, agent_name, repo_root)
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
