# Runtime reproduction — measured, not assumed

The project is tested with **Python 3.12** in GitHub Actions. The direct
runtime requirements are declared in [requirements.txt](../requirements.txt)
and pinned to broad compatible ranges; **there is no transitive lockfile**.
Do not claim byte-for-byte identical dependencies on every future install.

## Verify locally

```bash
python --version
python -m venv .venv
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/audit_comparison_readiness.py
python scripts/audit_case_studies.py
python scripts/record_runtime_environment.py
```

The last command writes `tested-runtime.json` with only the runtime Python
version, installed **direct** dependency versions, the SHA-256 of requirements,
the GitHub commit (in CI) and the UTC measurement date. It does not record
tokens, home directories, system secrets, installation paths or network data.

The GitHub [Quality Checks workflow](../.github/workflows/ci.yml) uploads a
`tested-python-runtime` artifact from the same run as tests and SQL audits.
Use that artifact to explain exactly which versions passed, rather than
inventing a locked environment.

**Future option:** Generate and validate a fully pinned requirements lock
against multiple Python/Linux environments before adopting it. Pinning
unsourced versions today would only simulate reproducibility. Testing a
deployment or a real user browser is a separate task.
