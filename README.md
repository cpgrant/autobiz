# Autobiz

Autobiz is a blueprint and software foundation for a small, AI-assisted business
that can execute routine work with strong human accountability.

The current product thesis is deliberately a **hypothesis**: provide managed lead
follow-up and client-onboarding automation to small consultancies or specialist agencies.
It must be validated through interviews and paid pilots before it becomes a firm
strategy.

## Current stage

Stage 0 is complete: the founder approved the company blueprint on 2026-07-28 and
selected small consultancies or specialist agencies as the initial segment.

**Required validation is deliberately deferred.** No product-market fit, customer
demand, willingness to pay, or repeatable workflow has been demonstrated. Safe
foundation work may continue, but product-specific automation and production launch
remain gated. See [Required validation gate](docs/09-required-validation-gate.md).

## Start here

- [Company overview](docs/00-company-overview.md)
- [Lean Canvas](docs/01-lean-canvas.md)
- [Values and strategy](docs/02-values-and-strategy.md)
- [Product hypotheses](docs/03-products.md)
- [Operating model](docs/04-operating-model.md)
- [System architecture](docs/05-system-architecture.md)
- [Delivery plan](docs/06-delivery-plan.md)
- [Controls and risks](docs/07-controls-and-risks.md)
- [Customer discovery playbook](docs/08-customer-discovery.md)
- [Required validation gate](docs/09-required-validation-gate.md)
- [Foundation backlog](docs/10-foundation-backlog.md)
- [Local operator runbook](docs/11-operator-runbook.md)
- [Interview candidate register](planning/interview-candidates.md)

## Planning workbooks

- [Financial model](outputs/autobiz-blueprint/autobiz-financial-model.xlsx)
- [Operating scorecard](outputs/autobiz-blueprint/autobiz-operating-scorecard.xlsx)

## Planned development workflow

```bash
make setup
make up
make migrate
make dev
make test
```

Copy `.env.example` to `.env` before using PostgreSQL locally. The default Django
configuration uses SQLite when `DB_HOST` is not set, which keeps initial tests and
experiments lightweight.

The Django application and containers are a foundation, not the product. Business
validation precedes substantial automation.
