# Foundation backlog while validation is deferred

This backlog contains generic, reversible work that does not assume the product
hypothesis is correct.

| Priority | Item | Completion evidence | Status |
|---:|---|---|---|
| 1 | Commit the reviewed foundation | Clean initial Git commit | Complete — 2026-07-28 |
| 2 | Run the application against PostgreSQL | Migrations and tests pass using Compose PostgreSQL | Complete — 2026-07-28 |
| 3 | Build and smoke-test the web container | Image builds; `/health/` returns 200 | Complete — 2026-07-28 |
| 4 | Expand model/admin tests | Approval, immutable audit, Admin, readiness, and logging behavior tested | Complete — 2026-07-28 |
| 5 | Add structured application logging | Request identifiers visible without sensitive payloads | Complete — 2026-07-28 |
| 6 | Add readiness check | Database-aware readiness separate from liveness | Complete — 2026-07-28 |
| 7 | Rehearse backup and restore locally | PostgreSQL backup restored into a clean scratch database | Complete — 2026-07-28 |
| 8 | Add dependency and container scanning in CI | Scans and failure policy configured; first CI run pending | Implemented — CI execution pending |
| 9 | Document local operator runbook | Setup, migration, recovery, and troubleshooting tested | Complete — 2026-07-28 |
| 10 | Review blueprint quarterly or at evidence change | Decision log updated | Recurring — next review 2026-10-28 or evidence change |

## Stop boundary

Do not pull work forward from AI-assisted workflow, customer integrations, offer
automation, or production launch while the required validation gate remains open.

## Verification record

On 2026-07-28:

- PostgreSQL 17 started successfully through Docker Compose and reported healthy;
- all Django migrations applied to PostgreSQL;
- the two existing tests passed against PostgreSQL;
- the Django web image built successfully;
- the web and database containers started together; and
- `GET /health/` returned HTTP 200 with `{"status": "ok", "service": "autobiz"}`.

Additional verification on 2026-07-28:

- the test suite expanded from 2 to 11 tests covering approval decisions,
  append-only audit events, Admin restrictions, readiness, and request correlation;
- a PostgreSQL custom-format backup was created under ignored local storage;
- the backup restored into the isolated `autobiz_restore_check` database;
- the restored database contained 19 migration records and the scratch database was removed;
- `/ready/` returned HTTP 200 with database status `ok`;
- the web container reported healthy through its database-aware health check;
- a supplied safe `X-Request-ID` was returned unchanged; and
- container logs showed JSON request events with method, path, status, duration, and
  request ID, without request bodies or query strings.
- Docker Scout indexed 141 packages in the local application image and reported no
  known vulnerabilities at any severity; CI remains configured to run independent
  dependency and image scans after the repository is connected to GitHub.
