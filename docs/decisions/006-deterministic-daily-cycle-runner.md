# ADR 006: Use a deterministic, operator-triggered Daily Cycle Runner

**Status:** Accepted

**Date:** 2026-08-01

## Context

Customer Zero needs repeatable daily operation before AI suggestions or scheduled
automation can be evaluated. The runner must exercise company records, work
selection, approvals, safe simulation, metrics, audits, and reports without gaining
external authority.

## Decision

Implement the first controlled operating component as a synchronous Django domain
service triggered by a staff operator or management command. Select dates, work,
and opportunities with deterministic rules and stable tie-breaks. Use PostgreSQL
records as authoritative state, date-keyed idempotency, one transaction for the
cycle body, append-only audit events, and durable daily and weekly reports.

Create consequential proposals only through the existing approval model. Approval
does not supply an executor, and company-wide external execution remains disabled.
Do not add AI, a scheduler, a task queue, or an external integration in this phase.

## Consequences

- Repeated synthetic days provide a measurable baseline for later AI suggestions.
- Completed dates do not duplicate work, proposals, approvals, or audit completion.
- Partial cycle work rolls back on failure; the failed date is retained for recovery.
- Operation remains explicitly human-triggered and local.
- Scheduling and AI remain separate future decisions supported by evidence from
  these deterministic runs.
