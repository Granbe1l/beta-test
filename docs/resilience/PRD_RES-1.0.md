# Project Delivery Monitor — RES-1.0 (public review draft)

Status: DRAFT, not implementation or release authorization. Date: 2026-11-28 (WIB).
Companion to the approved product requirements, governance and data contracts. The complete internal RES-1.0 draft is maintained separately; this public version intentionally omits sensitive incident details, exact negative reproductions, private evidence and local paths. Do not use it as the sole implementation specification.

## Objectives
- Maintain trustworthy, current, reproducible public-source analytics, with fail-closed publication and truthful coverage.
- Separate security hardening, operational recovery, and release readiness. Passing one does not imply the others.
- Assess foreseeable single and combined failures; reuse existing controls and implement only evidenced, approved gaps.
- Preserve existing metric definitions, Verified 28-day methodology, cohort membership, freshness policy, and UI/adapter contracts unless explicitly approved.
- Minimize cost, dependencies, and operational complexity.

## Requirements (public summary)
| ID | Requirement | Acceptance principle |
|---|---|---|
| RES-01 | Current visibility evidence | Only positively verified eligible public sources may enter a public publication. |
| RES-02 | Stable cohort identity | Exact approved membership, unique stable identities, transparent provenance. |
| RES-03 | Bounded collection | Mandatory safety checks fit the existing request budget; insufficient budget stops safely. |
| RES-04 | Production build safety | Publication requires current, complete validation evidence; no implicit authorization from historical data. |
| RES-05 | Publication and rollback integrity | Reject unsafe, corrupt or stale candidates; ensure approved output and evidence correspond. |
| RES-06 | Analytics compatibility | Preserve offline contracts, metric precision, denominators and honest freshness. |
| RES-07 | Historical access governance | Assess all access surfaces; containment and retention decisions require owner authorization. |
| RES-08 | Cohort recovery | Revalidate and recover safely; any permanent replacement is reviewed, versioned and explicitly approved. |
| RES-09 | API resilience | Bounded retry/backoff, truthful partial results, no false success. |
| RES-10 | Automation resilience | Idempotent recovery, concurrency safety, freshness observability, protected scheduling. |
| RES-11 | Incident observability | Sanitized, deduplicated signals and evidence-based closure. |
| RES-12 | Runtime and release resilience | Isolate failures, verify runtime contracts, regressions and rollback; require hosted CI and approved Preview before release. |

## Gates
R0 handoff and baseline; R1 audit and risk register; R2 complete design/PRD approval; R3 isolated implementation/TDD; R4 failure injection and regression; R5 independent review and handoff. No implementation before approved design. Existing product gates and release approvals remain independent.

## Change control
Every finding receives an ID, severity, evidence, requirement, test, decision, owner role, and disposition. A critical finding stops the affected gate; reopen gates whose evidence is invalidated. Scope changes need explicit approval. No gate closes on undocumented or untested mandatory requirements. Reuse evidence only when candidate identity and conditions remain applicable.

## Authorization boundary
This branch is documentation only. No change to product code, dataset, membership, workflow, main, redesign branch, service settings, credentials, refresh dispatch, deployment or release. Any such action requires the applicable separate authorization. See internal PRD for exact acceptance tests, unresolved decisions and protected paths.
