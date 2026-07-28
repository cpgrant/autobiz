# CI security policy

## Scope

CI performs two generic supply-chain checks:

1. `pip-audit` checks resolved Python dependencies against known vulnerability data.
2. Trivy scans the built application image for high and critical known vulnerabilities.

These checks support dependency hygiene; they are not a complete security review,
threat model, penetration test, or production authorization.

## Failure policy

- Known vulnerable Python dependencies fail CI.
- Fixed high or critical container findings fail CI.
- Unfixed operating-system findings are reported but do not fail CI to avoid a
  permanently blocked build with no available remediation.
- Findings must not be ignored without a documented decision in `docs/decisions/`
  including scope, impact, compensating controls, owner, and review date.
- Scanners must not receive application secrets or customer data.

## Review cadence

Review findings on every pull request and at least monthly while active development
continues. Reassess severity and failure policy before production deployment.
