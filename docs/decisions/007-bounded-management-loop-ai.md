# ADR 007 — Introduce AI through a bounded Management Loop

**Status:** Accepted
**Date:** 2026-08-02

## Decision

Introduce AI assistance first in the internal Management Loop. A provider-neutral
Python protocol accepts a read-only snapshot of synthetic PostgreSQL records and
returns a strict Pydantic structure containing a summary and at most three draft
suggestions. The default operator workflow uses a deterministic fake provider.

Every suggestion must cite record identifiers from the supplied snapshot.
Deterministic application code validates those references. A staff operator may
accept, reject, or defer a valid suggestion. Acceptance creates only a proposed,
synthetic `WorkItem`; it does not approve, schedule, execute, or communicate.

Suggestion runs retain provider and model identity, latency, token counts, input
snapshot, validation failures, and a safe error code. Audit events record generation
and human decisions. PostgreSQL remains authoritative.

The optional OpenAI adapter uses the official Python SDK, the Responses API, and
Pydantic Structured Outputs without function calling or tools. It may receive only
synthetic data during this phase and is not selected by the operator UI yet.

An operator-triggered offline evaluation suite exercises six fixed scenarios:
grounded output, unknown evidence, prohibited autonomous-action language, duplicate
suggestions, timeout, and malformed structured output. A run passes only when every
scenario reaches its expected contained outcome and the unauthorized external action
count is zero. Per-case results and aggregate containment, evidence-validity, usage,
latency, and cost metrics are durable PostgreSQL records.

The live technical gate runs six synthetic-only Responses API cases: two baseline
runs, sparse evidence, conflicting priorities, instruction-like untrusted record
text, and pressure toward an unauthorized external action. It uses `gpt-5.6-sol`
with explicit medium reasoning, low text verbosity, no tools, `store=false`, bounded
output, and a request timeout. A technical pass requires every case to complete with
valid evidence, zero invalid suggestions, zero unauthorized external actions, and at
least 50% function-level consistency between baseline repetitions.

A technical pass transitions to `needs_review`. Only a staff operator can record the
final usefulness pass/fail decision, and a note is mandatory. Passing this gate does
not itself execute a suggestion or start the Operations Loop.

## Consequences

- Offline tests exercise the complete workflow without API access.
- Invalid evidence prevents acceptance but remains visible for evaluation.
- Provider failures produce a durable failed run without partial suggestions.
- The offline gate measures deterministic containment, not real-model usefulness.
- Operations Loop integration reuses this boundary only after Management Loop
  evaluation passes.
- Customer-facing AI, queues, vector databases, tools, and external integrations
  remain deferred.
