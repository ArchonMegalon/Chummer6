#!/usr/bin/env bash
set -euo pipefail

repo_root="${CHUMMER6_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
design_root=""

for candidate in \
  "${CHUMMER_DESIGN_REPO_ROOT:-}" \
  "$repo_root/../chummer-design" \
  "$repo_root/../chummer6-design"
do
  if [[ -n "$candidate" && -f "$candidate/scripts/ai/materialize_public_guide_bundle.py" ]]; then
    design_root="$candidate"
    break
  fi
done

bash "$repo_root/scripts/verify_linux_source_build_docker_gate.sh"
python3 "$repo_root/scripts/test_verify_linux_source_build_docker_gate_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_linux_source_build_docker_gate_receipt.py" >/dev/null
if [[ -n "$design_root" ]]; then
  python3 "$design_root/scripts/ai/materialize_public_guide_bundle.py" --repo-root "$design_root" >/dev/null
  python3 "$repo_root/scripts/sync_public_guide_from_design.py" >/dev/null
fi
bash "$repo_root/scripts/verify_public_guide.sh"
python3 "$repo_root/scripts/test_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_release_verification_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_release_verification_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_release_verification_receipt.py" >/dev/null
