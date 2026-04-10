# script-gen

Batch ad script generation pipeline using FastAPI and Google Gemini. Generates 300 unique ad scripts by combining 50 hooks × 3 meats × 2 CTAs from business intake data.

## Project Structure

```
app/
├── main.py          # FastAPI app, endpoints (/generate, /health)
├── config.py        # Pydantic settings (env vars)
├── schemas.py       # Request/response models
├── prompts.py       # LLM prompt templates
├── pipeline.py      # Pipeline orchestration
├── generator.py     # Script generation logic
└── formatter.py     # Markdown output formatting
```

## Tech Stack

- **Python 3.12+**, FastAPI, Uvicorn
- **Google Gemini** (google-genai) for generation
- **Pydantic** for validation and settings
- **Ruff** for linting/formatting, **pytest** for tests

## Organization Rules

**Keep code organized and modularized:**
- API routes/endpoints → `app/main.py`
- Data models → `app/schemas.py`
- Prompt templates → `app/prompts.py`
- Pipeline logic → `app/pipeline.py`
- Generation logic → `app/generator.py`
- Configuration → `app/config.py`
- Tests → next to code or in `/tests`

**Modularity principles:**
- Single responsibility per file
- Clear, descriptive file names
- No monolithic files

## Code Quality - Zero Tolerance

After editing ANY file, run:

```bash
ruff check .
ruff format --check .
```

Fix ALL errors/warnings before continuing.

## Dev Commands

```bash
# Install
pip install -e ".[dev]"

# Run server
python -m app.main

# Lint & format
ruff check .
ruff format .

# Test
pytest
```

## Environment

Required in `.env`:
- `GEMINI_API_KEY` — Google AI API key
- `GEMINI_MODEL` — defaults to `gemini-2.5-flash`
- `HOST` / `PORT` — defaults to `0.0.0.0:8100`
