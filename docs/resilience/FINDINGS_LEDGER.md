# Findings ledger — public index

DRAFT. The internal ledger contains twelve initial F-series items with mixed evidence states (reported tests, source observations, design risks, existing controls and open decisions). They are not twelve confirmed defects. Details of unresolved security-sensitive findings are intentionally retained outside this public branch.

For each finding record: ID, discovery date, component, evidence status, severity, requirement, test, affected gate, owner role, disposition and evidence reference. Distinguish observed failures from hypotheses. New findings must be assessed before closing affected gates. P0 stops affected work; P1 blocks the affected gate; P2/P3 require an explicit disposition. If later evidence invalidates a passed gate, reopen that gate and any dependent evidence. No silent deletion or deferral.

Public status: audit/design incomplete; no product implementation or recovery verified by this document.
