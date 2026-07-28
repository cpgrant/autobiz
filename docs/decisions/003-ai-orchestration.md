# ADR 003 — Start with direct, bounded AI orchestration

**Status:** Accepted for foundation
**Date:** 2026-07-27

## Decision

Use the OpenAI Responses API or Agents SDK behind an internal service boundary.
Start with one agent/tool loop or direct structured call. Do not adopt LangGraph by
default.

## Rationale

The first workflow is not yet validated. Additional orchestration abstractions
would encode assumptions before real execution behavior is known.

## Reconsider when

The proven workflow is long-running, highly branched, must pause and resume across
process restarts, or becomes difficult to express and test as explicit Python state.
At that point compare LangGraph with a durable workflow engine such as Temporal.
