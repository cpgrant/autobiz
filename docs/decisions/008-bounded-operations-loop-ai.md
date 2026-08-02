# ADR 008 — Extend bounded AI assistance to the Operations Loop

**Status:** Accepted  
**Date:** 2026-08-02

## Decision

Extend the provider-neutral AI boundary to the internal Operations Loop only after
the live Management Loop evaluation has passed its technical and explicit human
usefulness gates.

The Operations provider receives a read-only snapshot of completed operating
cycles, metrics, open risks, and open work items. It returns a strict Pydantic
summary, exceptions, and at most three draft internal improvements. Deterministic
code validates every evidence reference and blocks unsafe external-action language.
Provider output remains secondary to PostgreSQL business records.

Operators retain accept, reject, and defer controls. Acceptance creates only a
proposed synthetic `WorkItem`; it cannot alter cycle facts, approve a proposal,
execute work, communicate externally, or change authority.

The offline evaluation uses six deterministic cases for grounded evidence, unknown
evidence, unsafe language, duplicates, timeout, and malformed output. The live gate
uses six synthetic cases covering repeatability, failure recovery, stale/conflicting
context, untrusted instructions, and external pressure. A live technical pass still
requires an explicit, noted human usefulness decision.

## Consequences

- Management and Operations reuse one provider and decision infrastructure while
  retaining loop-specific schemas, snapshots, evidence rules, and evaluation data.
- Every Operations suggestion run is linked to the latest completed operating cycle.
- No tools, queues, vector database, external executor, or customer data is added.
- The Customer Loop remains deferred until the Operations live and human gates pass.
