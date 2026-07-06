# Security Policy

## Supported Versions

This project currently supports the latest version on the `main` branch.

## Reporting a Vulnerability

If you discover a security issue, please do not open a public issue with
detailed exploit information.

Instead:

1. Share a private report with the maintainer.
2. Include steps to reproduce, expected impact, and suggested mitigation.
3. Allow reasonable time for triage and remediation before public disclosure.

## Sensitive Data Expectations

- Never commit secrets such as API keys, tokens, or passwords.
- Keep `.env` local only.
- Keep `app/data/LinkedinExport.pdf` local only.
- Do not add personal contact details or confidential organization details to
  public markdown knowledge files.
