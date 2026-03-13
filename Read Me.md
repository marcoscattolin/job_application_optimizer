# Job Application Optimizer

AI-powered job application optimizer using a multi-agent workflow: **Scout → Strategy → Writer**.

Given a job posting, this tool analyzes the role, evaluates fit against your biography profile, and generates tailored application materials (cover letter, targeted CV, headhunter emails).

## Folder Structure

```
├── agents/       # Agent prompt definitions (loaded at runtime)
├── bio/          # Your biography and CV source files
├── code/         # Python package
│   ├── models.py     # Pydantic schemas
│   ├── agents.py     # Agent classes
│   ├── prompts.py    # Prompt loader
│   └── run_optimizer.py  # CLI entry point
├── outputs/      # Generated application materials
├── templates/    # Email and CV templates
```

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd job_application_optimizer

# Install dependencies
uv venv
.\.venv\Scripts\activate
uv sync
```

## Configuration

Set your OpenAI API key as an environment variable:

```bash
# Linux/macOS
export OPENAI_API_KEY="sk-..."

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-..."
```

## Usage

### Basic Usage

```bash
# With a job post file
uv run python -m code.run_optimizer --job .\job_posts\job_post.txt

# Pipe job post from stdin
cat job_post.txt | uv run python -m code.run_optimizer

# Specify output language (IT or EN)
uv run python -m code.run_optimizer --job job_post.txt --lang IT
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--bio` | `bio/BIOGRAPHY_PROFILE.md` | Path to your biography profile |
| `--job` | `-` (stdin) | Path to job post file |
| `--lang` | `EN` | Output language (`EN` or `IT`) |
| `--out` | `outputs` | Output directory |
| `--model-structured` | `gpt-4o-mini` | Model for Scout/Strategy agents |
| `--model-writer` | `gpt-4o-mini` | Model for Writer agent |

### Output Files

After running, the `outputs/` folder will contain:

- `jobspec.json` - Structured job specification extracted by Scout
- `application_plan.json` - Strategy analysis with fit score and recommendations
- `cover_letter.md` - Generated cover letter
- `targeted_cv.md` - CV tailored to the job
- `headhunter_email.md` - (optional) If recommended by Strategy

## How It Works

### 1. Scout Agent
Extracts structured data from the job posting:
- Company, role, seniority level
- Responsibilities and requirements
- Keywords and AI maturity signals
- Red flags and questions for clarity

### 2. Strategy Agent
Evaluates fit and plans the application:
- Calculates fit score (0-100)
- Decides: APPLY (≥70), MAYBE (50-69), or SKIP (<50)
- Selects relevant projects from your profile
- Chooses positioning angle and narrative assets
- Identifies gaps and cover stories

### 3. Writer Agent
Generates application materials:
- Cover letter (250-400 words)
- Targeted CV in Markdown
- Headhunter email (if recommended)

All outputs follow your biography profile as the single source of truth - no invented facts or metrics.

## Customization

### Biography Profile
Edit `bio/BIOGRAPHY_PROFILE.md` with your experience, skills, key projects, and preferences.

### Agent Prompts
Edit the prompts in `agents/` to customize agent behavior - changes take effect immediately without code changes.

### Templates
Check `templates/` for email and CV structure templates.

## License

Private repository - all rights reserved.
