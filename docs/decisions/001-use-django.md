# ADR 001 — Use Django as the application foundation

**Status:** Accepted for foundation
**Date:** 2026-07-27

## Context

Autobiz needs business records, authentication, permissions, forms, migrations, and
an internal control interface before it needs a sophisticated customer frontend.

## Decision

Use Django as a modular monolith and Django Admin as the initial operator interface.

## Consequences

- Core business capabilities arrive with few dependencies.
- The application remains one deployable unit initially.
- Customer-facing interaction can use templates and HTMX when justified.
- API-only frameworks remain possible for specialized services later.

## Reconsider when

A validated requirement cannot be served cleanly by the modular monolith or a
separately scalable boundary is demonstrated by production load or ownership.
