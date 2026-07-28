# ADR 002 — Use PostgreSQL as the system of record

**Status:** Accepted
**Date:** 2026-07-27

## Decision

Use PostgreSQL for durable business records, workflow state, approvals, and audit
events. SQLite remains acceptable only for fast isolated tests.

## Consequences

Business truth is queryable and transactional. AI session or orchestration state
must reference, not replace, authoritative customer and commercial records.
