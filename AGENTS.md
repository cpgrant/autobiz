# Repository guidance

## Primary objective

Complete the smallest credible hackathon MVP.

Completion takes priority over:
- architectural improvement;
- refactoring;
- abstraction;
- additional agents;
- additional integrations;
- presentation polish;
- speculative future capabilities.

Do not add nice-to-have features.

## Working discipline

Before changing code:

1. State the exact task.
2. Identify the minimum files likely required.
3. Inspect only those files.
4. Make the smallest viable change.
5. Run only the relevant checks.
6. Report what changed and whether the task is complete.
7. Stop.

Do not recursively inspect the entire repository unless explicitly instructed.

Do not modify unrelated files.

Do not refactor working code unless the requested task cannot be completed safely without it.

When requirements are ambiguous, preserve existing behaviour and report the ambiguity rather than expanding scope.

## Excluded paths

Do not inspect or process these paths unless explicitly required:

- `.git/`
- `.venv/`
- `venv/`
- `node_modules/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `htmlcov/`
- `coverage/`
- `staticfiles/`
- `media/`
- `logs/`
- `dist/`
- `build/`
- generated diagrams
- screenshots
- database dumps
- binary documents
- local databases

Do not print large directory trees, dependency listings, test logs, Docker
logs, or Git histories. Show only output relevant to the current task.

## MVP boundary

The required vertical workflow is:

1. Customer submits a request.
2. An order is created.
3. Stripe payment is completed or safely simulated in test mode.
4. The consulting workflow is started.
5. A deliverable is produced.
6. The customer can access the result.
7. Operations can see the request, payment, execution and delivery status.

Anything outside this workflow is optional unless explicitly marked as required.

## Product discipline

- Treat initial customer, problem, product, pricing and growth assumptions as hypotheses.
- Do not add automation without a validated workflow and explicit authority boundary.
- Keep PostgreSQL business records authoritative.
- AI and orchestration state are secondary.
- Consequential external actions require explicit approval or a defined control boundary.

## Agent discipline

Agents may:

- interpret a customer request;
- produce a structured consulting task;
- perform the defined consulting workflow;
- generate a draft deliverable;
- update non-authoritative execution status;
- recommend an action.

Agents may not autonomously:

- charge a customer;
- refund money;
- enter contracts;
- delete records;
- send consequential external communications;
- change pricing;
- incur expenditure;
- alter governance or safety controls.

These actions require deterministic validation and, where appropriate, human approval.

## Architecture

- Maintain a modular Django monolith until measured evidence justifies separation.
- Put business logic in domain services or models, not views, templates, prompts or tasks.
- Keep provider-specific AI code behind a service boundary.
- Prefer deterministic code for policy, validation, permissions and calculations.
- Do not introduce another framework, message broker or orchestration platform unless necessary for the MVP workflow.

## Development

- Python version: 3.12.3 via pyenv.
- Use `uv` with `pyproject.toml` for dependencies.
- Add tests for behaviour changes.
- Add migrations for model changes.
- Never commit `.env`, credentials, customer data or generated local databases.
- Run the narrowest relevant test first.
- Run `make check` before declaring a task complete.
- Do not fix unrelated failures without explicit instruction.

## Completion criteria

A task is complete only when:

- the requested behaviour works;
- relevant tests pass;
- required migrations exist;
- no unrelated behaviour was changed;
- the exact changed files are reported;
- remaining blockers are explicitly listed.

Do not continue improving a completed task.

## Documentation and diagrams

- Update documentation only when the implemented behaviour or boundary changed.
- Record durable architecture decisions in `docs/decisions/`.
- Mermaid diagrams must reflect implemented architecture.
- Do not generate new architecture, dependency or class diagrams unless they are required for the submission or requested explicitly.
- Do not run `pyreverse`, `pydeps` or Graphviz merely to reconfirm known architecture.

## Final response format

After each implementation task, report only:

1. Status: COMPLETE or BLOCKED.
2. Files changed.
3. Behaviour implemented.
4. Verification performed.
5. Remaining blocker, if any.

Then stop.