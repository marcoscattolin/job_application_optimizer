"""Prompt loading utilities."""

from pathlib import Path

# Base directory for agent prompts (relative to repo root)
AGENTS_DIR = Path(__file__).parent.parent / "agents"


def load_prompt(agent_name: str) -> str:
    """Load a system prompt from agents/{agent_name}.md file.
    
    Args:
        agent_name: Name of the agent (e.g., 'scout_agent', 'strategy_agent', 'writer_agent')
    
    Returns:
        The prompt content as a string.
    
    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
    """
    prompt_path = AGENTS_DIR / f"{agent_name}.md"
    return prompt_path.read_text(encoding="utf-8")


# User message templates (these are simple format strings, kept in code)

SCOUT_USER_TEMPLATE = """OUTPUT_LANGUAGE: {lang}
JOB_POST:
{job_post}
"""

STRATEGY_USER_TEMPLATE = """OUTPUT_LANGUAGE: {lang}
JOBSPEC_JSON:
{jobspec_json}

BIOGRAPHY_PROFILE:
{bio_md}
"""

WRITER_USER_TEMPLATE = """OUTPUT_LANGUAGE: {lang}
OUTPUT_TYPE: {output_type}

JOBSPEC_JSON:
{jobspec_json}

APPLICATIONPLAN_JSON:
{plan_json}

BIOGRAPHY_PROFILE:
{bio_md}
"""
