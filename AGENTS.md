# Repository guidance

## Product discipline

- Treat the initial customer, problem, product, pricing, and growth assumptions as hypotheses.
- Do not add automation without a validated workflow and explicit authority boundary.
- Keep PostgreSQL business records authoritative; AI or orchestration state is secondary.
- Consequential external actions require an explicit approval/control design.

## Architecture

- Maintain a modular Django monolith until measured evidence justifies separation.
- Put business logic in domain services or models, not views, templates, prompts, or tasks.
- Keep provider-specific AI code behind a service boundary.
- Prefer deterministic code for policy, validation, permissions, and calculations.

## Development

- Python version: 3.12.3 via pyenv.
- Use `uv` with `pyproject.toml` for dependencies.
- Run `make check` before considering a change complete.
- Add tests for behavior changes and migrations for model changes.
- Never commit `.env`, credentials, customer data, or generated local databases.

## Documentation

- Update the relevant blueprint document when changing strategy, product scope, controls, architecture, or milestones.
- Record durable architecture choices in `docs/decisions/`.
- Mermaid diagrams must remain valid and reflect the implemented boundary.
