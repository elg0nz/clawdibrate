"""Calibration mode logic — defaults, transcript listing, and run loops."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .orchestrator import calibrate, estimate_iterations_to_target


def resolve_mode_defaults(args: argparse.Namespace) -> None:
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


def list_transcripts(repo_root: Path) -> list[Path]:
    """Return .jsonl transcript files sorted newest-first."""
    transcripts_dir = repo_root / ".clawdibrate" / "transcripts"
    if not transcripts_dir.exists():
        return []
    return sorted(
        transcripts_dir.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def run_progressive_mode(args: argparse.Namespace, agent_name: str, repo_root: Path) -> None:
    """Run many small, cancel-safe calibrations over recent transcripts."""
    transcripts = list_transcripts(repo_root)
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


def run_max_mode(args: argparse.Namespace, agent_name: str, repo_root: Path) -> None:
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


def run_idempotency_check(args: argparse.Namespace, agent_name: str) -> None:
    """Run calibrate twice on the same transcript and verify convergence.

    Exit code 0 if the second pass produces no changes; 1 if it diverges.
    """
    if not args.transcript:
        print("error: --check-idempotent requires --transcript", file=sys.stderr)
        sys.exit(1)

    shared_kwargs = dict(
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

    print("[idempotency] Run 1 …")
    calibrate(**shared_kwargs)

    print("[idempotency] Run 2 …")
    result2 = calibrate(**shared_kwargs)

    changed2 = result2.get("changed", False)
    edit_distances: dict[str, int] = result2.get("edit_distances", {})
    all_zero = all(d == 0 for d in edit_distances.values())

    if not changed2 or all_zero:
        print("PASS: calibration is idempotent")
        sys.exit(0)
    else:
        print("FAIL: calibration diverged on second pass")
        for section, dist in edit_distances.items():
            if dist > 0:
                print(f"  section={section!r} edit_distance={dist}")
        sys.exit(1)
