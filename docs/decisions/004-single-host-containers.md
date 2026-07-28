# ADR 004 — Deploy containers on one host initially

**Status:** Accepted for initial production design
**Date:** 2026-07-27

## Decision

Use Docker Compose locally and on one small Linux VM for the first production
version. Use a production override, persistent storage, restart policies, HTTPS,
monitoring, and off-host backups.

## Consequences

Operations remain understandable and inexpensive. Managed PostgreSQL should be the
first infrastructure separation when reliability or growth warrants it.

## Reconsider when

Measured availability, load, recovery, compliance, or organizational requirements
cannot be met safely on a single host.
