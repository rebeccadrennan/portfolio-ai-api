# Contributing

Thanks for contributing to `portfolio-ai-api`.

## Local Development

1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Add a local `.env` file with `GEMINI_API_KEY`.
4. Run the API and test before committing.

## Commands

Run tests:

```bash
python -m pytest -q
```

Run API:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Knowledge Base Rules

- Keep `app/data/*.md` public-safe and portfolio-focused.
- Do not add private contact details.
- Do not add confidential employer, client, or internal project names.
- `app/data/LinkedinExport.pdf` is local-only and must not be committed.

## Pull Request Checklist

- [ ] Tests pass locally.
- [ ] No API keys or secrets are committed.
- [ ] Documentation is updated when behavior changes.
- [ ] Knowledge base content remains public-safe.
