#!/usr/bin/env bash
set -euo pipefail

repo_root="${CHUMMER6_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

bash "$repo_root/scripts/verify_linux_source_build_docker_gate.sh"
python3 "$repo_root/scripts/test_verify_linux_source_build_docker_gate_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_linux_source_build_docker_gate_receipt.py" >/dev/null
bash "$repo_root/scripts/verify_public_guide.sh"
python3 "$repo_root/scripts/test_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_release_verification_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_release_verification_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_release_verification_receipt.py" >/dev/null
