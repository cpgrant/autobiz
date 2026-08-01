# Customer Zero experiment

**Status:** Days 1–7 complete; controlled-player phase next — initiated 2026-08-01

**Owner:** Founder/operator

**Mode:** Local, synthetic, reversible

## Mission

Establish and operate Autobiz as a controlled agent-driven company that can plan
work, simulate customers, make recommendations, request approvals, execute safe
internal actions, and measure progress.

The first objective is to produce, within two to three weeks, a functioning local
company operating system that completes a daily operating cycle using synthetic
business data.

This is a Customer Zero systems experiment, not evidence of customer demand. It
does not satisfy or weaken the required market-validation gate.

## Company functions

| Function | Initial responsibility |
|---|---|
| Direction | Goals, priorities, and decisions |
| Growth | Synthetic market research, leads, and offers |
| Delivery | Services, projects, tasks, and quality |
| Finance | Synthetic prices, costs, cash, and forecasts |
| Operations | Approvals, risks, audits, and reporting |

These are functional areas inside the modular Django monolith. They are not
departments, separate services, or autonomous agents.

## Daily operating cycle

Every simulated day Autobiz will:

1. read company goals and current state;
2. inspect opportunities, work, finances, and risks;
3. identify the most important next actions;
4. create proposed work items;
5. request approval where required;
6. execute authorized internal actions;
7. record results and append audit events;
8. update metrics; and
9. produce a short daily operating report.

The initial implementation is deterministic. AI assistance may later propose
summaries or drafts through a service boundary, but it will not calculate policy,
permissions, authority, or financial measures.

## Day 0 synthetic scenario

- one company: Autobiz;
- three services: Establish, Operate, and Improve;
- ten prospects and three opportunities;
- one customer and one internal pilot;
- representative tasks, costs, revenue, risks, and exceptions; and
- explicit `is_synthetic` fields plus visible synthetic labels.

The scenario is loaded by the idempotent command:

```bash
uv run python manage.py load_customer_zero
```

## Synthetic customer journey

The local portal at `/customer/request/` lets the founder act as a synthetic
customer and exercise one bounded Establish journey:

```text
Submit request → review fixed offer → accept → simulate payment
→ inspect completed work → review deliverable → accept or request revision
→ create revision work → produce next version → review again
```

The price is deterministically fixed at €1,200. The payment simulator asks for no
card details, connects to no payment provider, and records only synthetic database
entries. Successful simulation creates an engagement, linked delivery work, revenue
entry, operating-plan deliverable, and append-only audit events.

Customer free text is untrusted content. It can appear in an escaped deliverable but
cannot modify price, scope, authority policy, system instructions, or execution
capability. UUID journey links are sufficient only for this local synthetic mode;
real customers will require authentication and authorization.

Deliverables are versioned and append-only at the business-record level. A revision
request preserves the reviewed version, creates a linked Delivery work item, and
waits for bounded internal revision simulation. Producing the revision marks the old
version non-current, creates the next version for review, records the change in the
audit history, and allows another accept-or-revise decision.

### Journey evidence

| Request | Payment boundary |
|---|---|
| ![Synthetic customer request](images/synthetic-customer-request.png) | ![Synthetic test payment](images/synthetic-test-payment.png) |

![Synthetic operating-plan deliverable](images/synthetic-operating-plan-deliverable.png)

![Company state after the completed customer journey](images/synthetic-customer-company-update.png)

![Corrected customer review controls](images/corrected-review-controls.png)

![Version 2 returned to review with preserved history](images/versioned-revised-deliverable.png)

## Authority matrix

| Action | Level | Initial behavior |
|---|---:|---|
| Read local records; calculate metrics | 0 — Observe | Automatic |
| Prioritize work; draft plans or reports | 1 — Draft | Automatic, no side effect |
| Create simulated tasks; simulate reversible outcomes | 2 — Bounded execute | Automatic and audited |
| Send communications; spend money; change prices; publish | 3 — Human approval | Approval required; external executor disabled |
| Delete records | 3 — Human approval | Approval required; autonomous executor disabled |
| Contractual commitments; external-system access | 4 — Prohibited | Blocked |

Approval and execution capability are independent controls. An approved action
cannot execute unless an appropriate executor exists and company-wide external
execution is enabled. External execution remains disabled throughout this
experiment.

Unknown action types fail closed at level 4.

## Delivery plan

### Days 1–3 — Model the company

- [x] document this experiment and its authority boundary;
- [x] define company, goal, opportunity, work, finance, risk, metric, cycle, and
  proposal records;
- [x] load and verify the Day 0 scenario.

### Days 4–7 — Build the operating system

- [x] expose records through Django Admin and a company-status dashboard;
- [x] implement deterministic metrics and prioritization;
- [x] add a staff-only operator console for approvals, audit history, and cycle history;
- [x] add behavioral and migration tests.

The deterministic refresh command is:

```bash
uv run python manage.py refresh_customer_zero
```

It recalculates nine measures from authoritative records and reprioritizes current
work. Priority 1 covers in-progress work, approval-blocked work, and requested
revisions; ready and other blocked work are priority 2; proposed work is priority 3;
completed work is moved to priority 5. Every refresh appends an audit event.

The staff-only `/operator/` view is the human control point. It shows pending
approvals, metrics, prioritized work, operating-cycle history, and recent audit
events. Deciding a proposal records the human, time, note, proposal state, and audit
event. Approval still cannot enable an unavailable or external executor.

### Week 2 — Build the controlled player

- run the deterministic daily cycle;
- route consequential proposals through approvals;
- simulate bounded actions and record every material result;
- create daily and weekly reports.

### Week 3 — Add limited AI assistance

- put model calls behind a provider-neutral service boundary;
- restrict AI to summaries, suggestions, and draft content;
- run repeated scenarios and measure errors, approvals, completion, and economics.

## Definition of success

The local demonstration must show visible company state, measurable goals, three
services, a synthetic pipeline and customer, prioritized work, controlled
proposals, safe simulation, complete audit history, daily and weekly reports, and
zero unauthorized external actions.

## Change log

### 2026-08-01 — Day 0 foundation

- recorded the mission, operating cycle, data boundary, and authority matrix;
- added the Customer Zero operating records and status view;
- added an idempotent synthetic scenario loader;
- kept external execution disabled and unknown actions fail-closed.

### 2026-08-01 — Synthetic Establish journey

- added request, offer, simulated-payment, engagement, and deliverable states;
- fixed the synthetic Establish price at €1,200 in deterministic application logic;
- generated a bounded local operating-plan deliverable without AI or external calls;
- added accept and revision-request review paths with audit events.

### 2026-08-01 — Review-control correction

- aligned each radio control with its decision label and made the full choice row clickable;
- visually verified the corrected review form and added regression coverage.

### 2026-08-01 — Versioned revision loop

- preserved prior deliverables and identified one current version per request;
- created a controlled revision work item from customer feedback;
- added deterministic version production with named owners, targets, and cash review;
- returned the revised deliverable to customer review with visible version history.

### 2026-08-01 — Days 4–7 operating system

- added deterministic calculation of nine operating measures and documented work priority rules;
- linked the synthetic external follow-up to a real pending approval record;
- added a staff-only operator console with approval decisions, cycle history, and audit visibility;
- preserved the independent execution gate after approval and kept external execution disabled;
- added a repeatable refresh command and behavioral coverage for metrics, priority, access, and controls.

### Verification evidence

![Customer Zero company-status dashboard](images/customer-zero-dashboard.png)

| Staff-only operator control | Approved but still non-executable |
|---|---|
| ![Customer Zero operator console](images/customer-zero-operator-console.png) | ![Synthetic approval recorded](images/customer-zero-approval-recorded.png) |

![Days 4–7 company dashboard with deterministic measures](images/customer-zero-days-4-7-dashboard.png)

- migration applied successfully to the local development database;
- scenario loader completed twice without duplicating records;
- Django system check reported no issues;
- formatting, linting, type checking, and all 28 tests passed;
- browser inspection confirmed the synthetic label, company measures, priority
  work, pending approval, operating report, audit event, action-control states,
  and open risks are visible;
- browser execution verified that human approval updates the proposal and approval
  metric while external execution remains disabled.
