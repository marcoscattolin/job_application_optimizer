"""Agent classes for the job application optimizer pipeline."""

from openai import OpenAI

from .models import JobSpec, ApplicationPlan
from .prompts import (
    load_prompt,
    SCOUT_USER_TEMPLATE,
    STRATEGY_USER_TEMPLATE,
    WRITER_USER_TEMPLATE,
)


class BaseAgent:
    """Base class for all agents."""

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model


class ScoutAgent(BaseAgent):
    """Extracts structured JobSpec from a job posting."""

    def __init__(self, client: OpenAI, model: str):
        super().__init__(client, model)
        self.system_prompt = load_prompt("scout_agent")

    def run(self, job_post: str, lang: str) -> JobSpec:
        """Parse a job posting into a structured JobSpec.
        
        Args:
            job_post: Raw text of the job posting.
            lang: Output language ('EN' or 'IT').
        
        Returns:
            Parsed JobSpec object.
        """
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": SCOUT_USER_TEMPLATE.format(lang=lang, job_post=job_post)},
            ],
            text_format=JobSpec,
        )
        return response.output_parsed


class StrategyAgent(BaseAgent):
    """Evaluates job fit and creates an application strategy."""

    def __init__(self, client: OpenAI, model: str):
        super().__init__(client, model)
        self.system_prompt = load_prompt("strategy_agent")

    def run(self, jobspec: JobSpec, bio: str, lang: str) -> ApplicationPlan:
        """Evaluate fit and create application strategy.
        
        Args:
            jobspec: Structured job specification from Scout.
            bio: Biography profile markdown content.
            lang: Output language ('EN' or 'IT').
        
        Returns:
            ApplicationPlan with decision, fit score, and recommendations.
        """
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": STRATEGY_USER_TEMPLATE.format(
                        lang=lang,
                        jobspec_json=jobspec.model_dump_json(indent=2),
                        bio_md=bio,
                    ),
                },
            ],
            text_format=ApplicationPlan,
        )
        return response.output_parsed


class WriterAgent(BaseAgent):
    """Generates application artifacts (cover letter, CV, emails)."""

    def __init__(self, client: OpenAI, model: str):
        super().__init__(client, model)
        self.system_prompt = load_prompt("writer_agent")

    def run(
        self,
        jobspec: JobSpec,
        plan: ApplicationPlan,
        bio: str,
        lang: str,
        output_type: str,
    ) -> str:
        """Generate an application artifact.
        
        Args:
            jobspec: Structured job specification.
            plan: Application strategy from Strategy agent.
            bio: Biography profile markdown content.
            lang: Output language ('EN' or 'IT').
            output_type: Type of artifact to generate 
                        (cover_letter, targeted_cv_md, headhunter_email, etc.)
        
        Returns:
            Generated text content.
        """
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": WRITER_USER_TEMPLATE.format(
                        lang=lang,
                        output_type=output_type,
                        jobspec_json=jobspec.model_dump_json(indent=2),
                        plan_json=plan.model_dump_json(indent=2),
                        bio_md=bio,
                    ),
                },
            ],
        )
        return (response.output_text or "").strip()
