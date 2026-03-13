"""Pydantic models for structured outputs."""

from typing import Literal, List

from pydantic import BaseModel, Field


# Type aliases for readability
Seniority = Literal["IC", "Manager", "Director", "VP", "C-level", "Unknown"]
RoleType = Literal["Executive", "Leadership", "Hybrid", "IndividualContributor", "Research", "Unknown"]
RemotePolicy = Literal["Onsite", "Hybrid", "Remote", "Unknown"]
Decision = Literal["APPLY", "MAYBE", "SKIP"]
Mode = Literal["EXPLORATIVE", "AGGRESSIVE"]
NarrativeAsset = Literal["MOTIVATION", "DIFFERENTIATORS", "FAILURE_AND_LEARNING", "LEADERSHIP_STYLE"]
OutputType = Literal["cover_letter", "screening_answers", "headhunter_email", "exec_summary", "targeted_cv_md"]


class JobSpec(BaseModel):
    """Structured job posting data extracted by Scout agent."""

    company: str = ""
    role_title: str = ""
    seniority: Seniority = "Unknown"
    role_type: RoleType = "Unknown"
    location: str = ""
    remote_policy: RemotePolicy = "Unknown"
    responsibilities: List[str] = Field(default_factory=list)
    requirements_must: List[str] = Field(default_factory=list)
    requirements_nice: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    signals_of_ai_maturity: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    questions_for_clarity: List[str] = Field(default_factory=list)


class ApplicationPlan(BaseModel):
    """Strategy output with fit assessment and application plan."""

    decision: Decision
    fit_score: int = Field(ge=0, le=100)
    mode: Mode
    rationale_bullets: List[str]
    selected_key_projects: List[str]
    selected_narrative_assets: List[NarrativeAsset]
    positioning_angle: str
    gaps_and_cover_story: List[str] = Field(default_factory=list)
    must_confirm_with_human: List[str] = Field(default_factory=list)
    recommended_outputs: List[OutputType] = Field(default_factory=list)
