# ADR 005: Run Customer Zero as a controlled synthetic simulation

**Status:** Accepted

**Date:** 2026-08-01

## Context

Autobiz needs an end-to-end operating environment in which planning, approvals,
auditing, reporting, and safe internal execution can be exercised before customer
workflows or external authority are validated.

## Decision

Run Customer Zero locally with explicitly synthetic business records. Keep
authority policy deterministic, preserve PostgreSQL business records as the source
of truth, and keep all external executors disabled. Treat approval and execution
capability as separate controls. Unknown action types are prohibited.

The experiment may use reversible internal simulation but may not send, spend,
publish, contract, delete autonomously, or access external customer systems.

## Consequences

- The complete company loop can be measured without real-world side effects.
- Results validate system behavior, not market demand or product-market fit.
- AI can be added later behind a service boundary without controlling permissions
  or authoritative calculations.
- Production and market-validation gates remain unchanged.
