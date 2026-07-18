from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify_public_guide.sh"
CONVERGENCE_SCRIPT = REPO_ROOT / "scripts" / "release" / "verify_guide_convergence.sh"


def _authority_env(root: Path) -> dict[str, str]:
    snapshot = root / "SNAPSHOT.json"
    decision = root / "RELEASE_DECISION.json"
    snapshot.write_text("{}\n", encoding="utf-8")
    decision.write_text("{}\n", encoding="utf-8")
    return {
        "CHUMMER_RELEASE_AUTHORITY_SNAPSHOT": str(snapshot),
        "CHUMMER_REGISTRY_COMMIT": "a" * 40,
        "CHUMMER_RELEASE_DECISION_RECEIPT": str(decision),
        "CHUMMER_EXPECTED_RELEASE_DECISION_STATUS": "preview_ready",
    }


def _fake_python(root: Path, log_path: Path) -> Path:
    fake_bin = root / "bin"
    fake_bin.mkdir(parents=True)
    python = fake_bin / "python3"
    python.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            printf 'python %s\n' "$*" >> "$CALL_LOG"
            """
        ),
        encoding="utf-8",
    )
    python.chmod(0o755)
    return fake_bin


def test_verify_public_guide_forwards_authority_only_to_truth_verifiers() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        log_path = root / "calls.log"
        fake_bin = _fake_python(root, log_path)
        authority_env = _authority_env(root)
        env = {
            **os.environ,
            **authority_env,
            "CALL_LOG": str(log_path),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        }

        completed = subprocess.run(
            ["bash", str(VERIFY_SCRIPT), "--source", str(root / "guide"), "--skip-http", "--release"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )

        assert completed.returncode == 0, completed.stdout
        calls = log_path.read_text(encoding="utf-8").splitlines()
        sync_call = next(line for line in calls if "sync_public_guide_from_design.py" in line)
        assert "--authority-snapshot" not in sync_call
        expected_tail = (
            f"--authority-snapshot {authority_env['CHUMMER_RELEASE_AUTHORITY_SNAPSHOT']} "
            f"--registry-commit {'a' * 40} "
            f"--release-decision {authority_env['CHUMMER_RELEASE_DECISION_RECEIPT']} "
            "--expected-release-decision-status preview_ready "
            "--served-mirror https://chummer.run/downloads/RELEASE_CHANNEL.generated.json --release"
        )
        downloads_call = next(
            line for line in calls if "verify_public_downloads_match_registry.py" in line and "test_" not in line
        )
        docs_call = next(
            line for line in calls if "verify_chummer6_docs_release_truth.py" in line and "test_" not in line
        )
        assert downloads_call.endswith(expected_tail)
        assert docs_call.endswith(expected_tail)


def test_verify_public_guide_missing_authority_fails_before_checks() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        log_path = root / "calls.log"
        fake_bin = _fake_python(root, log_path)
        env = {
            **os.environ,
            "CALL_LOG": str(log_path),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "CHUMMER_RELEASE_AUTHORITY_SNAPSHOT": "",
            "CHUMMER_REGISTRY_COMMIT": "",
            "CHUMMER_RELEASE_DECISION_RECEIPT": "",
            "CHUMMER_EXPECTED_RELEASE_DECISION_STATUS": "",
        }
        completed = subprocess.run(
            ["bash", str(VERIFY_SCRIPT), "--skip-http"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )

        assert completed.returncode == 2
        assert "immutable release authority is mandatory" in completed.stdout
        assert not log_path.exists()


def _write_fake_convergence_repo(root: Path) -> Path:
    repo = root / "chummer6"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    for relative in ("verify_linux_source_build_docker_gate.sh", "verify_public_guide.sh"):
        path = scripts / relative
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                printf '{relative} %s\n' "$*" >> "$CALL_LOG"
                """
            ),
            encoding="utf-8",
        )
        path.chmod(0o755)
    return repo


def test_convergence_entrypoint_forwards_one_exact_release_authority_tuple() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        log_path = root / "calls.log"
        fake_bin = _fake_python(root, log_path)
        fake_repo = _write_fake_convergence_repo(root)
        authority_env = _authority_env(root)
        env = {
            **os.environ,
            **authority_env,
            "CALL_LOG": str(log_path),
            "CHUMMER6_REPO_ROOT": str(fake_repo),
            "CHUMMER_DESIGN_REPO_ROOT": "",
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        }

        completed = subprocess.run(
            ["bash", str(CONVERGENCE_SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )

        assert completed.returncode == 0, completed.stdout
        calls = log_path.read_text(encoding="utf-8").splitlines()
        expected_args = (
            f"--release --authority-snapshot {authority_env['CHUMMER_RELEASE_AUTHORITY_SNAPSHOT']} "
            f"--registry-commit {'a' * 40} "
            f"--release-decision {authority_env['CHUMMER_RELEASE_DECISION_RECEIPT']} "
            "--expected-release-decision-status preview_ready "
            "--served-mirror https://chummer.run/downloads/RELEASE_CHANNEL.generated.json"
        )
        materialize = next(
            line for line in calls if "/scripts/materialize_public_release_truth_packet.py " in line
        )
        verify = next(line for line in calls if line.startswith("verify_public_guide.sh "))
        assert materialize.endswith(expected_args)
        assert verify == f"verify_public_guide.sh --skip-http {expected_args}"


def test_convergence_missing_authority_fails_before_receipt_mutation() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        log_path = root / "calls.log"
        fake_bin = _fake_python(root, log_path)
        fake_repo = _write_fake_convergence_repo(root)
        env = {
            **os.environ,
            "CALL_LOG": str(log_path),
            "CHUMMER6_REPO_ROOT": str(fake_repo),
            "CHUMMER_DESIGN_REPO_ROOT": "",
            "CHUMMER_RELEASE_AUTHORITY_SNAPSHOT": "",
            "CHUMMER_REGISTRY_COMMIT": "",
            "CHUMMER_RELEASE_DECISION_RECEIPT": "",
            "CHUMMER_EXPECTED_RELEASE_DECISION_STATUS": "",
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        }

        completed = subprocess.run(
            ["bash", str(CONVERGENCE_SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )

        assert completed.returncode == 2
        assert "Immutable release authority is mandatory" in completed.stdout
        assert not log_path.exists()
