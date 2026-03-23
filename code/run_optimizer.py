#!/usr/bin/env python3
"""
Job Application Optimizer - CLI Orchestrator

Runs the Scout -> Strategy -> Writer pipeline to generate
tailored application materials from a job posting.

Usage:
  uv run job-optimizer --job job.txt
  uv run python -m code.run_optimizer --job job.txt
  cat job.txt | uv run job-optimizer --lang IT
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from openai import OpenAI

from code.agents import ScoutAgent, StrategyAgent, WriterAgent
from code.scraper import fetch_linkedin_job


def read_file(path: str) -> str:
    """Read text from a file path."""
    logger.debug(f"Reading file: {path}")
    content = Path(path).read_text(encoding="utf-8")
    logger.debug(f"Read {len(content)} chars from {path}")
    return content


def read_job_post(job_path: str, url: str | None = None) -> str:
    """Read job post from URL, file, or stdin."""
    if url:
        logger.debug(f"Fetching job post from URL: {url}")
        return fetch_linkedin_job(url)
    if job_path and job_path != "-":
        logger.debug(f"Reading job post from file: {job_path}")
        content = Path(job_path).read_text(encoding="utf-8")
        logger.debug(f"Read {len(content)} chars from job post file")
        return content
    logger.debug("Reading job post from stdin")
    content = sys.stdin.read()
    logger.debug(f"Read {len(content)} chars from stdin")
    return content


def ensure_dir(path: str) -> Path:
    """Ensure directory exists and return Path object."""
    p = Path(path)
    logger.debug(f"Ensuring directory exists: {p}")
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_api_key() -> str:
    """Load OpenAI API key from secrets file."""
    key_file = Path(__file__).parent.parent / "secrets" / "openai_api_key.txt"
    logger.debug(f"Looking for API key at {key_file}")
    if not key_file.exists():
        raise SystemExit(f"Missing API key file: {key_file}")
    key = key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit(f"API key file is empty: {key_file}")
    logger.info("API key loaded successfully")
    return key


def main() -> None:
    parser = argparse.ArgumentParser(description="Job Application Optimizer")
    parser.add_argument("--bio", default="bio/BIOGRAPHY_PROFILE.md", help="Path to biography profile")
    parser.add_argument("--cover-letter", default="bio/COVER_LETTER.md", help="Path to cover letter")
    parser.add_argument("--job", default="-", help="Path to job post (or - for stdin)")
    parser.add_argument("--url", default=None, help="LinkedIn job posting URL (overrides --job)")
    parser.add_argument("--lang", choices=["IT", "EN"], default="EN", help="Output language")
    parser.add_argument("--out", default="outputs", help="Output directory")
    parser.add_argument("--model-structured", default="gpt-4o-mini", help="Model for Scout/Strategy")
    parser.add_argument("--model-writer", default="gpt-4o-mini", help="Model for Writer")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level (default: INFO)")
    args = parser.parse_args()

    # Configure logging level
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=args.log_level)

    if args.url and args.job != "-":
        logger.warning("Both --url and --job provided; --url takes precedence.")

    logger.info(f"Starting job optimizer | lang={args.lang} | model_structured={args.model_structured} | model_writer={args.model_writer}")

    # Load API key from secrets file
    api_key = load_api_key()

    # Load inputs
    bio = read_file(args.bio).strip()
    job_post = read_job_post(args.job, url=args.url).strip()
    cover_letter = read_file(args.cover_letter).strip()

    logger.info(f"Loaded biography ({len(bio)} chars), job post ({len(job_post)} chars), cover letter ({len(cover_letter)} chars)")

    if not bio:
        raise SystemExit("Biography profile is empty.")
    if not cover_letter:
        raise SystemExit("Cover letter is empty.")
    if not job_post:
        raise SystemExit("Job post is empty (provide --job or pipe to stdin).")

    # Setup output directory: {out}/{job_name}/{timestamp}/
    if args.url:
        from code.scraper import _extract_job_id
        job_id = _extract_job_id(args.url)
        job_name = f"linkedin_{job_id}" if job_id else "linkedin_job"
    else:
        job_name = Path(args.job).stem if args.job != "-" else "stdin_job"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ensure_dir(Path(args.out) / job_name / timestamp)
    logger.info(f"Output directory: {out_dir}")
    client = OpenAI(api_key=api_key)

    # Initialize agents
    scout = ScoutAgent(client, args.model_structured)
    strategy = StrategyAgent(client, args.model_structured)
    writer = WriterAgent(client, args.model_writer)
    logger.debug("Agents initialized: Scout, Strategy, Writer")

    # Step 1: Scout - Extract job spec
    logger.info("Step 1/3: Running Scout agent to extract job spec...")
    jobspec = scout.run(job_post, args.lang)
    logger.info(f"Scout complete | company={jobspec.company} | role={jobspec.role_title}")
    (out_dir / "jobspec.json").write_text(jobspec.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Wrote jobspec.json")

    # Step 2: Strategy - Evaluate fit and plan
    logger.info("Step 2/3: Running Strategy agent to evaluate fit and plan...")
    plan = strategy.run(jobspec, bio, args.lang)
    logger.info(f"Strategy complete | decision={plan.decision} | fit_score={plan.fit_score} | mode={plan.mode}")
    (out_dir / "application_plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Wrote application_plan.json")

    # Step 3: Writer - Generate artifacts
    logger.info("Step 3/3: Running Writer agent to generate artifacts...")
    artifacts = []

    logger.debug("Generating cover letter...")
    cover_letter = writer.run(jobspec=jobspec, plan=plan, bio=bio, cover_letter=cover_letter, lang=args.lang, output_type="cover_letter")
    (out_dir / "cover_letter.md").write_text(cover_letter + "\n", encoding="utf-8")
    artifacts.append("cover_letter.md")
    logger.debug("Wrote cover_letter.md")

    logger.debug("Generating targeted CV...")
    targeted_cv = writer.run(jobspec=jobspec, plan=plan, bio=bio, cover_letter=cover_letter, lang=args.lang, output_type="targeted_cv_md")
    (out_dir / "targeted_cv.md").write_text(targeted_cv + "\n", encoding="utf-8")
    artifacts.append("targeted_cv.md")
    logger.debug("Wrote targeted_cv.md")

    if "headhunter_email" in plan.recommended_outputs:
        logger.debug("Generating headhunter email...")
        headhunter = writer.run(jobspec=jobspec, plan=plan, bio=bio, cover_letter=cover_letter, lang=args.lang, output_type="headhunter_email")
        (out_dir / "headhunter_email.md").write_text(headhunter + "\n", encoding="utf-8")
        artifacts.append("headhunter_email.md")
        logger.debug("Wrote headhunter_email.md")

    # Output summary
    logger.info(f"Pipeline complete | artifacts={len(artifacts)} | output_dir={out_dir}")
    print(json.dumps({
        "out_dir": str(out_dir),
        "decision": plan.decision,
        "fit_score": plan.fit_score,
        "mode": plan.mode,
        "files_written": ["jobspec.json", "application_plan.json", *artifacts],
        "human_review_needed": any(
            "[HUMAN REVIEW NEEDED:" in text
            for text in [cover_letter, targeted_cv]
        ),
    }, indent=2))


if __name__ == "__main__":
    main()
