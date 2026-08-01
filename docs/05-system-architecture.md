# System architecture

## Architecture principles

- Modular monolith before distributed services.
- PostgreSQL is the business system of record.
- Deterministic software controls policy; models assist with interpretation.
- Every consequential action has an authority check and audit event.
- External side effects are idempotent and retriable.
- Development is local; production uses the same container image.

## Logical architecture

```mermaid
flowchart TB
    U["Customers and operators"] --> W["Django web application"]
    W --> UI["Templates / HTMX"]
    W --> ADM["Django Admin"]
    W --> API["API and webhooks"]
    W --> DB[("PostgreSQL: system of record")]
    W --> Q["Job and approval records"]
    Q --> WK["Background worker"]
    WK --> AI["AI service boundary"]
    AI --> OAI["OpenAI Responses API / Agents SDK"]
    WK --> EXT["Approved external integrations"]
    WK --> DB
    WK --> AP{"Authority / approval check"}
    AP -->|approved| EXT
    AP -->|needs review| ADM
```

## Initial deployment

```mermaid
flowchart LR
    I["Internet"] --> C["Caddy: HTTPS and reverse proxy"]
    subgraph VM["Single Linux VM"]
      C --> WEB["Django / Gunicorn container"]
      WEB --> PG[("PostgreSQL container")]
      WEB --> WRK["Worker container — later"]
      WRK --> PG
    end
    PG -. encrypted backup .-> B["Off-VM object storage"]
    WEB --> OA["OpenAI API"]
    WEB --> E["Email / payments / customer systems"]
```

PostgreSQL may move to a managed service before scaling the application across
multiple hosts.

## Core data model

```mermaid
erDiagram
    CUSTOMER ||--o{ CONTACT : has
    CUSTOMER ||--o{ ENGAGEMENT : purchases
    PRODUCT ||--o{ ENGAGEMENT : defines
    ENGAGEMENT ||--o{ WORKFLOW_RUN : generates
    WORKFLOW_RUN ||--o{ APPROVAL : requests
    WORKFLOW_RUN ||--o{ AUDIT_EVENT : records
    WORKFLOW_RUN ||--o{ ARTIFACT : produces
    CUSTOMER {
      uuid id
      string name
      string status
    }
    PRODUCT {
      uuid id
      string name
      string status
    }
    WORKFLOW_RUN {
      uuid id
      string workflow_key
      string status
      integer attempt_count
      decimal estimated_cost
    }
    APPROVAL {
      uuid id
      string action_type
      string status
      datetime decided_at
    }
    AUDIT_EVENT {
      uuid id
      string event_type
      json payload
      datetime created_at
    }
```

The implemented Customer Zero boundary includes company state, goals, opportunities,
work, finance, risk, metrics, operating cycles, action proposals, approvals, and
append-only audit events. The synthetic customer journey adds CustomerRequest,
Offer, SyntheticPayment, and Deliverable while keeping PostgreSQL authoritative.

## Synthetic customer journey boundary

```mermaid
flowchart LR
    R["Synthetic request"] --> O["Fixed Establish offer"]
    O --> P["Internal payment simulation"]
    P --> E["Engagement and work items"]
    E --> D["Local operating-plan deliverable"]
    D --> V{"Customer review"}
    V -->|Accept| C["Complete"]
    V -->|Revise| X["Revision work item"]
    X --> D2["Next deliverable version"]
    D2 --> V
    P -. no provider or card data .-> N["External execution disabled"]
```

Pricing and artifact generation are deterministic domain-service behavior. Customer
input is untrusted data, not an instruction channel. Real payment or customer mode
is outside this boundary and requires authentication, authorization, verified
webhooks, reconciliation, legal, tax, privacy, refund, and operational controls.

Deliverables use a per-request version number and a database-enforced single-current
constraint. Prior versions remain authoritative history; revisions create new rows
rather than overwriting reviewed artifacts.

## Workflow state

```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> Running
    Running --> AwaitingApproval
    AwaitingApproval --> Running: approved
    AwaitingApproval --> Cancelled: rejected
    Running --> Retrying: transient failure
    Retrying --> Running
    Retrying --> Failed: retry limit
    Running --> Completed
    Pending --> Cancelled
    Failed --> Pending: authorized replay
    Completed --> [*]
    Cancelled --> [*]
```

## Initial stack

| Concern | Choice | Reason |
|---|---|---|
| Runtime | Python 3.12 | Mature ecosystem and existing environment |
| Application | Django | ORM, migrations, authentication, permissions, admin |
| UI | Django templates; HTMX when needed | Avoid premature frontend application complexity |
| Database | PostgreSQL | Durable relational system of record |
| AI | OpenAI Agents SDK / Responses API | Tools, structured output, guardrails, tracing |
| Worker | Add after a real asynchronous workflow exists | Avoid queue infrastructure before need |
| Durable orchestration | LangGraph or Temporal only after evidence | Complexity must be justified by workflow behavior |
| Local/production packaging | Docker Compose | Reproducible single-host operation |
| HTTPS | Caddy in production | Simple certificate and reverse-proxy management |
| Testing | pytest + pytest-django | Fast automated verification |
| Quality | Ruff + Pyright | Formatting, linting, and type checking |

## Environments

| Environment | Application | Database | External effects |
|---|---|---|---|
| Unit tests | Local process | Temporary SQLite initially | Mocked |
| Local development | `.venv` | PostgreSQL via Compose | Test/sandbox only |
| Local system test | Containers | PostgreSQL container | Test/sandbox only |
| Staging | VM/container | Separate PostgreSQL | Test accounts and restricted sending |
| Production | VM/container | Production PostgreSQL | Explicitly authorized |

## Operational health and logs

- `GET /health/` is a liveness check and does not query dependencies.
- `GET /ready/` executes a minimal database query and returns 503 when PostgreSQL is unavailable.
- Containers use readiness for health reporting.
- Every request receives an `X-Request-ID`; safe incoming identifiers are preserved.
- Application request events are emitted as JSON with method, path, status, duration,
  and request ID. Query strings, bodies, credentials, and model/customer payloads are excluded.
- Database backups use PostgreSQL custom format and are validated through an isolated
  scratch restore before being considered usable.

## Deliberate exclusions

No Kubernetes, microservices, vector database, multi-agent hierarchy, React SPA,
self-hosted model, or general integration platform in the initial architecture.
