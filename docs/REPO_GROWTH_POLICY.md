# Monitor Git repository growth without discarding source evidence

Public `Granbe1l/beta-test` contains a periodically updated compressed
real-data snapshot and archived reports for excluded repositories. Even
compressed binary snapshots can add substantial Git history over time,
so the repository size should be monitored, not silently cleaned.

This project uses one read-only call to GitHub's repository metadata API
and logs `size` (reported in KiB), plus the **current** compressed snapshot
file's byte count. `size` is approximate and can lag; it is not an exact
`.git` measurement or a linear forecast. The first warning threshold is
200 MiB, not an automated deletion threshold.

The [repository footprint workflow](../.github/workflows/repository-size-audit.yml)
runs after successful collectors and can also be manually dispatched.
It uploads a date-specific `repository-growth-audit.json`. The warning does
not block collection or change Verified source status.

If size grows: inspect the actual size trend across reports; retain original
data archives; consider an external versioned object store for future
snapshots only after a public, independently verified read path is ready.
**Do not rewrite existing Git history or delete audits automatically.**
