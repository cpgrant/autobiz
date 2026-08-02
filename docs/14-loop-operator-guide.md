# Operator guide — using the three loops

Open `/operator/`. Work from top to bottom. AI output is always a draft based on
synthetic records; it never sends messages or executes external work.

## Recommended schedule

| Loop | Normal cadence | Best time to run | Also run when | Do not run when |
|---|---|---|---|---|
| Management | Once each week | After the week's metrics and risks are current, before choosing next week's priorities | A goal, major risk, budget, or strategic assumption materially changes | Records are stale or there is no real decision to make |
| Operations | Once each operating day | Immediately after the daily cycle completes | A cycle fails, a repeated exception appears, or an important metric moves unexpectedly | The daily cycle is incomplete or nothing has changed since the previous review |
| Customer | On demand | After a synthetic request or customer state changes and before a response is prepared | An offer, engagement, delivery, or revision needs a new draft | The source record is incomplete, disputed, or contains real customer data |

Simple weekly rhythm:

1. **Every operating day:** complete the daily cycle, then run Operations once.
2. **When a response is needed:** run Customer for that request and review the draft.
3. **At the end or start of each week:** refresh metrics, review risks, then run Management.
4. **After any loop:** accept only useful grounded output; defer uncertain work and reject
   unsupported or duplicate output.

Avoid rerunning a loop merely to obtain a more agreeable answer. Correct the source
records or record a human decision instead. If a loop repeatedly produces weak output,
stop using it and run its evaluation before changing prompts, models, or automation.

## Management Loop

Use it to decide **what deserves attention**.

1. Select **Generate synthetic suggestions**.
2. Review the cited evidence.
3. Accept, defer, or reject. Acceptance creates a proposed `WorkItem` only.

Example acceptance note: `Grounded in the open risk; useful as draft internal work.`

## Operations Loop

Use it to improve **how completed daily cycles run**.

1. Select **Generate Operations suggestions**.
2. Check that each suggestion cites a completed cycle, metric, risk, or work item.
3. Accept, defer, or reject. Acceptance still creates draft internal work only.

Example defer note: `Useful, but wait for two more completed cycles.`

## Customer Loop

Use it to prepare **a customer-facing draft** from synthetic customer records.

1. Select **Generate customer draft**.
2. Check names, price, scope, delivery status, promises, and cited evidence.
3. Choose **Approve draft only**, defer, or reject.

Example approval note: `Matches the request, makes no unsupported promise, and is safe as a draft.`

Approval does **not** send the draft. Copying or sending it is outside the current
system boundary.

## Evaluation gates

Run offline evaluation after code changes. Run live synthetic evaluation only when
you want to assess the configured model. If all technical cases pass, review several
outputs and record a short usefulness reason in the pass/fail field.

Never pass a gate merely because the score says 100%. Fail it when drafts are vague,
misleading, unhelpful, or would require substantial rewriting.
