"""Streamlit frontend for the Job Application Optimizer."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from openai import OpenAI

# Resolve project root (two levels up from this file: code/ -> repo root)
PROJECT_ROOT = Path(__file__).parent.parent

# Add project root to path so imports work when run via `streamlit run`
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from code.agents import ScoutAgent, StrategyAgent, WriterAgent
from code.scraper import fetch_linkedin_job, _extract_job_id


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_api_key_from_file() -> str:
    key_file = PROJECT_ROOT / "secrets" / "openai_api_key.txt"
    if key_file.exists():
        key = key_file.read_text(encoding="utf-8").strip()
        return key
    return ""


def _load_bio() -> str:
    return (PROJECT_ROOT / "bio" / "BIOGRAPHY_PROFILE.md").read_text(encoding="utf-8").strip()


def _load_cover_letter_template() -> str:
    return (PROJECT_ROOT / "bio" / "COVER_LETTER.md").read_text(encoding="utf-8").strip()


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _decision_badge(decision: str, fit_score: int) -> str:
    if decision == "APPLY":
        color = "green"
    elif decision == "MAYBE":
        color = "orange"
    else:
        color = "red"
    return f":{color}[**{decision}**]"


def _score_color(score: int) -> str:
    if score >= 70:
        return "green"
    elif score >= 50:
        return "orange"
    return "red"


def _bullets(items: list[str]) -> None:
    for item in items:
        st.markdown(f"- {item}")


# ── Session state init ────────────────────────────────────────────────────────

def _init_state() -> None:
    for key in ("jobspec", "plan", "artifacts", "out_dir", "ran"):
        if key not in st.session_state:
            st.session_state[key] = None
    if "ran" not in st.session_state:
        st.session_state.ran = False


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_pipeline(
    job_post: str,
    job_name: str,
    api_key: str,
    lang: str,
    model_structured: str,
    model_writer: str,
) -> None:
    bio = _load_bio()
    cover_letter_template = _load_cover_letter_template()

    client = OpenAI(api_key=api_key)
    scout = ScoutAgent(client, model_structured)
    strategy = StrategyAgent(client, model_structured)
    writer = WriterAgent(client, model_writer)

    # Output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = _ensure_dir(PROJECT_ROOT / "outputs" / job_name / timestamp)

    # Step 1 — Scout
    with st.status("Step 1/3 — Scout: extracting job spec...", expanded=True) as status:
        jobspec = scout.run(job_post, lang)
        (out_dir / "jobspec.json").write_text(jobspec.model_dump_json(indent=2), encoding="utf-8")
        status.update(label=f"Scout complete — {jobspec.company} | {jobspec.role_title}", state="complete")

    # Step 2 — Strategy
    with st.status("Step 2/3 — Strategy: evaluating fit...", expanded=True) as status:
        plan = strategy.run(jobspec, bio, lang)
        (out_dir / "application_plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        status.update(
            label=f"Strategy complete — {plan.decision} | score {plan.fit_score}/100 | {plan.mode}",
            state="complete",
        )

    # Step 3 — Writer
    artifacts: dict[str, str] = {}
    with st.status("Step 3/3 — Writer: generating documents...", expanded=True) as status:
        cover_letter = writer.run(
            jobspec=jobspec, plan=plan, bio=bio,
            cover_letter=cover_letter_template, lang=lang, output_type="cover_letter",
        )
        (out_dir / "cover_letter.md").write_text(cover_letter + "\n", encoding="utf-8")
        artifacts["cover_letter"] = cover_letter
        st.write("Cover letter done.")

        targeted_cv = writer.run(
            jobspec=jobspec, plan=plan, bio=bio,
            cover_letter=cover_letter_template, lang=lang, output_type="targeted_cv_md",
        )
        (out_dir / "targeted_cv.md").write_text(targeted_cv + "\n", encoding="utf-8")
        artifacts["targeted_cv"] = targeted_cv
        st.write("Targeted CV done.")

        if "headhunter_email" in plan.recommended_outputs:
            headhunter = writer.run(
                jobspec=jobspec, plan=plan, bio=bio,
                cover_letter=cover_letter_template, lang=lang, output_type="headhunter_email",
            )
            (out_dir / "headhunter_email.md").write_text(headhunter + "\n", encoding="utf-8")
            artifacts["headhunter_email"] = headhunter
            st.write("Headhunter email done.")

        status.update(label=f"Writer complete — {len(artifacts)} documents generated", state="complete")

    # Persist to session state
    st.session_state.jobspec = jobspec
    st.session_state.plan = plan
    st.session_state.artifacts = artifacts
    st.session_state.out_dir = out_dir
    st.session_state.ran = True


# ── Results display ───────────────────────────────────────────────────────────

def show_results() -> None:
    jobspec = st.session_state.jobspec
    plan = st.session_state.plan
    artifacts = st.session_state.artifacts
    out_dir = st.session_state.out_dir

    # Human review warning
    if any("[HUMAN REVIEW NEEDED:" in text for text in artifacts.values()):
        st.warning("Some documents contain **[HUMAN REVIEW NEEDED]** flags — review before sending.")

    # Summary card
    score_color = _score_color(plan.fit_score)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Company", jobspec.company)
    col2.metric("Role", jobspec.role_title)
    col3.metric("Fit Score", f"{plan.fit_score}/100")
    col4.metric("Decision", plan.decision)

    st.markdown(
        f"**Decision:** {_decision_badge(plan.decision, plan.fit_score)} &nbsp;|&nbsp; "
        f"**Mode:** `{plan.mode}` &nbsp;|&nbsp; "
        f"**Seniority:** `{jobspec.seniority}` &nbsp;|&nbsp; "
        f"**Remote:** `{jobspec.remote_policy}` &nbsp;|&nbsp; "
        f"**Output dir:** `{out_dir}`"
    )
    st.divider()

    # Build tab list dynamically
    tab_labels = ["📋 JobSpec", "📝 Cover Letter", "📄 Targeted CV", "⚙️ Strategy"]
    if "headhunter_email" in artifacts:
        tab_labels.insert(3, "📧 Headhunter Email")

    tabs = st.tabs(tab_labels)
    tab_map = {label: tab for label, tab in zip(tab_labels, tabs)}

    # --- JobSpec tab ---
    with tab_map["📋 JobSpec"]:
        col_a, col_b = st.columns(2)
        with col_a:
            with st.expander("Responsibilities", expanded=True):
                _bullets(jobspec.responsibilities)
            with st.expander("Must-have requirements"):
                _bullets(jobspec.requirements_must)
            with st.expander("Nice-to-have requirements"):
                _bullets(jobspec.requirements_nice)
        with col_b:
            with st.expander("Keywords"):
                st.write(", ".join(jobspec.keywords))
            with st.expander("AI maturity signals"):
                _bullets(jobspec.signals_of_ai_maturity) if jobspec.signals_of_ai_maturity else st.write("None detected.")
            with st.expander("Red flags"):
                _bullets(jobspec.red_flags) if jobspec.red_flags else st.write("None.")
            with st.expander("Questions for clarity"):
                _bullets(jobspec.questions_for_clarity) if jobspec.questions_for_clarity else st.write("None.")

    # --- Cover Letter tab ---
    with tab_map["📝 Cover Letter"]:
        st.markdown(artifacts["cover_letter"])
        st.download_button(
            "Download cover_letter.md",
            data=artifacts["cover_letter"],
            file_name="cover_letter.md",
            mime="text/markdown",
        )

    # --- Targeted CV tab ---
    with tab_map["📄 Targeted CV"]:
        st.markdown(artifacts["targeted_cv"])
        st.download_button(
            "Download targeted_cv.md",
            data=artifacts["targeted_cv"],
            file_name="targeted_cv.md",
            mime="text/markdown",
        )

    # --- Headhunter Email tab (optional) ---
    if "📧 Headhunter Email" in tab_map:
        with tab_map["📧 Headhunter Email"]:
            st.markdown(artifacts["headhunter_email"])
            st.download_button(
                "Download headhunter_email.md",
                data=artifacts["headhunter_email"],
                file_name="headhunter_email.md",
                mime="text/markdown",
            )

    # --- Strategy tab ---
    with tab_map["⚙️ Strategy"]:
        st.subheader("Positioning angle")
        st.info(plan.positioning_angle)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            with st.expander("Rationale", expanded=True):
                _bullets(plan.rationale_bullets)
            with st.expander("Selected key projects"):
                _bullets(plan.selected_key_projects)
            with st.expander("Narrative assets"):
                _bullets(plan.selected_narrative_assets)
        with col_s2:
            with st.expander("Gaps & cover story"):
                _bullets(plan.gaps_and_cover_story) if plan.gaps_and_cover_story else st.write("No gaps identified.")
            with st.expander("Must confirm with human"):
                _bullets(plan.must_confirm_with_human) if plan.must_confirm_with_human else st.write("Nothing to confirm.")


# ── Main app ──────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Job Application Optimizer",
        page_icon="💼",
        layout="wide",
    )
    _init_state()

    st.title("💼 Job Application Optimizer")
    st.caption("Scout → Strategy → Writer pipeline for tailored application materials.")

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Settings")

        default_key = _load_api_key_from_file()
        api_key = st.text_input(
            "OpenAI API Key",
            value=default_key,
            type="password",
            help="Auto-loaded from secrets/openai_api_key.txt if present.",
        )

        lang = st.radio("Output language", ["EN", "IT"], horizontal=True)

        model_structured = st.selectbox(
            "Model — Scout & Strategy",
            ["gpt-4o-mini", "gpt-4o"],
            index=0,
        )
        model_writer = st.selectbox(
            "Model — Writer",
            ["gpt-4o-mini", "gpt-4o"],
            index=0,
        )

    # ── Job input ─────────────────────────────────────────────────────────────
    st.subheader("Job posting")
    input_tab_paste, input_tab_file, input_tab_url = st.tabs(["Paste text", "Upload file", "LinkedIn URL"])

    job_post = ""
    job_name = "job"

    with input_tab_paste:
        pasted = st.text_area(
            "Paste the job description here",
            height=300,
            placeholder="Copy and paste the full job posting text...",
        )
        if pasted:
            job_post = pasted
            job_name = "pasted_job"

    with input_tab_file:
        uploaded = st.file_uploader("Upload a .txt or .md file", type=["txt", "md"])
        if uploaded:
            job_post = uploaded.read().decode("utf-8")
            job_name = Path(uploaded.name).stem

    with input_tab_url:
        url = st.text_input("LinkedIn job URL", placeholder="https://www.linkedin.com/jobs/view/...")
        if url:
            job_name_from_id = _extract_job_id(url)
            job_name = f"linkedin_{job_name_from_id}" if job_name_from_id else "linkedin_job"

    # ── Run button ────────────────────────────────────────────────────────────
    st.divider()
    run_col, _ = st.columns([1, 4])
    run_clicked = run_col.button("Run Pipeline", type="primary", use_container_width=True)

    if run_clicked:
        # Resolve job post from URL if that tab was used
        if url and not job_post:
            with st.spinner("Fetching job from LinkedIn..."):
                try:
                    job_post = fetch_linkedin_job(url)
                except Exception as exc:
                    st.error(f"Failed to fetch LinkedIn job: {exc}")
                    st.stop()

        # Validate inputs
        if not api_key:
            st.error("Please provide an OpenAI API key in the sidebar.")
            st.stop()
        if not job_post or not job_post.strip():
            st.error("Please provide a job posting (paste text, upload a file, or enter a LinkedIn URL).")
            st.stop()

        # Clear previous results
        st.session_state.ran = False

        try:
            run_pipeline(
                job_post=job_post.strip(),
                job_name=job_name,
                api_key=api_key,
                lang=lang,
                model_structured=model_structured,
                model_writer=model_writer,
            )
        except Exception as exc:
            st.error(f"Pipeline error: {exc}")
            st.stop()

    # ── Show results ──────────────────────────────────────────────────────────
    if st.session_state.ran:
        st.divider()
        st.subheader("Results")
        show_results()


if __name__ == "__main__":
    main()
