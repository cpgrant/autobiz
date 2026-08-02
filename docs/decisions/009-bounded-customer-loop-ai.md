# ADR 009 — Add a draft-only Customer Loop

**Status:** Accepted  
**Date:** 2026-08-02

## Decision

Add customer-facing AI only after the Management and Operations live technical and
human gates pass. The Customer Loop receives synthetic customer requests, offers,
engagements, and deliverable metadata. It returns strict Pydantic drafts with intent,
optional escalation, and evidence references.

Deterministic validation blocks unknown evidence, unsupported promises, automatic
sending or approval claims, prompt-injection language, and requests for common
sensitive credentials. A human may approve, reject, or defer a valid draft.
Approval changes only the draft review status. There is no sending endpoint,
messaging integration, or external executor.

Offline and live synthetic evaluations are separate durable gates. Live technical
success becomes `needs_review` and requires a noted human usefulness decision.

## Consequences

- PostgreSQL customer, price, payment, and delivery records remain authoritative.
- Provider failures are durable and create no partial drafts.
- Approved drafts are explicitly distinguishable from sent communication.
- Real customer data, authentication, delivery, and messaging remain out of scope.
