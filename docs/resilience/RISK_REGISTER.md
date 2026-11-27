# Resilience risk register — public index

DRAFT. This is an audit coverage inventory, not a claim that a risk is currently exploitable or a control is absent. Exact evidence, likelihood, reproduction, ownership and dispositions are in the internal register. All unverified entries remain to be assessed; prioritize by evidence and impact.

| Area | Scenarios to audit | Control objective |
|---|---|---|
| Source identity/visibility | Access changes, transfer, identity changes, multiple unavailable sources | Verify eligibility, isolate uncertainty, controlled recovery |
| Historical access | Archives, caches, exports, static snapshots, old deployments | Inventory access, authorized containment, truthful availability |
| Data integrity | Duplicates, malformed/corrupt snapshots, partial data, clock skew | Schema, uniqueness, freshness and atomic publication |
| Collection | API outage, throttling, auth, budget, pagination, interruption | Bounded retries and recovery, honest coverage |
| Automation | Missed schedule, queue delays, competing runs, retry loops, quota | Observable, bounded, idempotent recovery |
| Security | Credential handling, log leakage, dependency and supply chain | Redaction, scans, approved remediation |
| Runtime | Database/TLS/connection failures, shared limiter, environment, deployment | Fail-closed where required, isolate affected feature, validate Preview |
| UX and analysis | Empty/stale/partial states, time boundaries, browser regression | Accurate claims, targeted parity and regression |
| Maintenance | Resource growth, cost, backup, documentation drift | Measured thresholds, verified recovery, no unauthorized spending |
| Combined failures | Concurrent outage, data uncertainty, resource exhaustion | Containment and escalation without false success |

Severity: P0 critical security/integrity; P1 material operational/accuracy; P2 localized; P3 optimization. Likelihood is evidence-based, not invented. Internal entries retain their K-series IDs.
