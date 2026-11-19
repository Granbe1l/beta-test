"""Publication must be bound to the data actually restored, not event history."""
import subprocess
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import textwrap

import pytest

from scripts import verify_collection as gate

ROOT = Path(__file__).resolve().parents[1]


def workflow_block(name):
    source = (ROOT / ".github/workflows/public-snapshot.yml").read_text(encoding="utf-8")
    step = source.split("      - name: " + name + "\n", 1)[1].split("      - name:", 1)[0]
    return textwrap.dedent(step.split("        run: |\n", 1)[1]).strip()


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "data").mkdir()
    (tmp_path / "data/snapshot.gz").write_bytes(b"old snapshot")
    (tmp_path / "data/manifest.json").write_text("pinned cohort")
    (tmp_path / "data/github_public_snapshot.json.gz").write_bytes(b"source")
    for name in ("curated_50_manifest.json", "curated_50_transition_receipt.json",
                 "archived_75_to_50_reports.json.gz"):
        (tmp_path / "data" / name).write_bytes(b"committed provenance fixture")
    (tmp_path / "scripts").mkdir()
    shutil.copyfile(ROOT / "scripts/verify_collection.py", tmp_path / "scripts/verify_collection.py")
    git(tmp_path, "add", "data", "scripts")
    git(tmp_path, "commit", "-m", "fixture baseline")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path


def test_non_main_dispatch_cannot_capture_publishable_baseline(repo):
    with pytest.raises(ValueError, match="main"):
        gate.capture_publication_baseline(repo, "refs/heads/candidate")


def test_untracked_archive_and_receipt_cannot_authorize_publication(repo):
    names = ("curated_50_transition_receipt.json", "archived_75_to_50_reports.json.gz")
    for name in names:
        git(repo, "rm", "data/" + name)
    git(repo, "commit", "-m", "fixture missing provenance")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    for name in names:
        (repo / "data" / name).write_bytes(b"untracked local recovery")
    with pytest.raises(ValueError, match="committed.*provenance"):
        gate.capture_publication_baseline(repo, "refs/heads/main")


@pytest.mark.parametrize("changed", ["snapshot.gz", "manifest.json"])
def test_newer_main_data_refuses_old_collector_output(repo, changed):
    baseline = gate.capture_publication_baseline(repo, "refs/heads/main")
    (repo / "data" / changed).write_text("newer approved data")
    git(repo, "add", "data")
    git(repo, "commit", "-m", "fixture concurrent publication")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    with pytest.raises(ValueError, match="baseline changed"):
        gate.verify_publication_baseline(repo, baseline)


def test_generated_working_snapshot_and_unrelated_main_code_do_not_conflict(repo):
    baseline = gate.capture_publication_baseline(repo, "refs/heads/main")
    (repo / "README.md").write_text("new documentation")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "fixture documentation update")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    (repo / "data/snapshot.gz").write_bytes(b"new collector output")
    gate.verify_publication_baseline(repo, baseline)


def test_queued_event_checkout_is_rejected_before_collection(repo):
    old = git(repo, "rev-parse", "HEAD")
    (repo / "data/snapshot.gz").write_bytes(b"newer snapshot")
    git(repo, "add", "data")
    git(repo, "commit", "-m", "fixture next snapshot")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "checkout", "--detach", old)
    # Actual queued-run case: HEAD is old, fetched origin/main is newer.
    with pytest.raises(ValueError, match="baseline changed"):
        gate.capture_publication_baseline(repo, "refs/heads/main")


@pytest.mark.parametrize("changed_on_attempt", [1, 2, 3])
def test_actual_publication_workflow_rechecks_baseline_on_retry(repo, changed_on_attempt):
    bash = Path("C:/Program Files/Git/bin/bash.exe") if os.name == "nt" else shutil.which("bash")
    if not bash or not Path(bash).exists():
        pytest.skip("Bash is required to execute the real Actions publication block")
    baseline = gate.capture_publication_baseline(repo, "refs/heads/main")
    original = git(repo, "rev-parse", "HEAD")
    (repo / "data/manifest.json").write_text("newer approved cohort manifest")
    git(repo, "add", "data")
    git(repo, "commit", "-m", "fixture concurrent data change")
    newer = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "--detach", original)
    receipt = repo / "publication-baseline.json"
    receipt.write_text(json.dumps(baseline))
    (repo / "data/github_public_snapshot.json.gz").write_bytes(b"collector output")
    script = workflow_block("Publish newest snapshot without binary rebase conflicts")
    script = script.replace("/tmp/publication-baseline.json", shlex.quote(receipt.as_posix()))
    script = script.replace("/tmp/new_public_snapshot.json.gz", shlex.quote((repo / "output.gz").as_posix()))
    # Only external fetch/push are simulated. Execute real reset, commit and
    # production Python validation inside this disposable repository.
    harness = f'''
python() {{ {shlex.quote(Path(sys.executable).as_posix())} "$@"; }}
sleep() {{ :; }}
git() {{
  if [ "$1" = fetch ]; then
    echo fetched >> fetches
    if [ "$(wc -l < fetches)" -eq {changed_on_attempt} ]; then
      command git update-ref refs/remotes/origin/main {newer}
    fi
  elif [ "$1" = push ]; then
    echo attempted >> pushes
    return 1
  else
    command git "$@"
  fi
}}
'''
    result = subprocess.run([str(bash), "-c", harness + script], cwd=repo,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "baseline changed" in result.stderr, result.stdout + result.stderr
    pushes = (repo / "pushes").read_text().splitlines() if (repo / "pushes").exists() else []
    assert pushes == ["attempted"] * (changed_on_attempt - 1)
    assert git(repo, "rev-parse", "origin/main") == newer
    # Retry must abort before resetting the checkout to new main or overwriting it.
    assert git(repo, "show", "HEAD:data/manifest.json") == "pinned cohort"
