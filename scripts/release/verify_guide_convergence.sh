#!/usr/bin/env bash
set -euo pipefail

repo_root="${CHUMMER6_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
design_root=""
authority_snapshot="${CHUMMER_RELEASE_AUTHORITY_SNAPSHOT:-}"
registry_commit="${CHUMMER_REGISTRY_COMMIT:-}"
release_decision="${CHUMMER_RELEASE_DECISION_RECEIPT:-}"
expected_decision_status="${CHUMMER_EXPECTED_RELEASE_DECISION_STATUS:-}"
served_mirror="${CHUMMER_RELEASE_SERVED_MIRROR:-https://chummer.run/downloads/RELEASE_CHANNEL.generated.json}"

usage() {
  echo "Usage: $0 --authority-snapshot PATH --registry-commit SHA --release-decision PATH --expected-release-decision-status STATUS [--served-mirror URL]" >&2
}

while (($#)); do
  case "$1" in
    --authority-snapshot)
      (($# >= 2)) || { echo "--authority-snapshot requires a path" >&2; exit 2; }
      authority_snapshot="$2"
      shift 2
      ;;
    --registry-commit)
      (($# >= 2)) || { echo "--registry-commit requires a SHA" >&2; exit 2; }
      registry_commit="$2"
      shift 2
      ;;
    --release-decision)
      (($# >= 2)) || { echo "--release-decision requires a path" >&2; exit 2; }
      release_decision="$2"
      shift 2
      ;;
    --expected-release-decision-status)
      (($# >= 2)) || { echo "--expected-release-decision-status requires a value" >&2; exit 2; }
      expected_decision_status="$2"
      shift 2
      ;;
    --served-mirror)
      (($# >= 2)) || { echo "--served-mirror requires a URL" >&2; exit 2; }
      served_mirror="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

missing_authority=()
[[ -n "$authority_snapshot" ]] || missing_authority+=(--authority-snapshot)
[[ -n "$registry_commit" ]] || missing_authority+=(--registry-commit)
[[ -n "$release_decision" ]] || missing_authority+=(--release-decision)
[[ -n "$expected_decision_status" ]] || missing_authority+=(--expected-release-decision-status)
if ((${#missing_authority[@]})); then
  echo "Immutable release authority is mandatory; missing: ${missing_authority[*]}" >&2
  exit 2
fi
[[ -f "$authority_snapshot" ]] || { echo "Authority snapshot not found: $authority_snapshot" >&2; exit 2; }
[[ -f "$release_decision" ]] || { echo "Release decision not found: $release_decision" >&2; exit 2; }
[[ "$registry_commit" =~ ^[0-9a-f]{40}$ ]] || { echo "Registry commit must be exact lowercase 40-hex" >&2; exit 2; }
case "$expected_decision_status" in
  review_required|preview_ready|stable_ready) ;;
  *) echo "Unsupported release decision status: $expected_decision_status" >&2; exit 2 ;;
esac
[[ -n "$served_mirror" ]] || { echo "Served mirror must be nonempty" >&2; exit 2; }

release_authority_args=(
  --release
  --authority-snapshot "$authority_snapshot"
  --registry-commit "$registry_commit"
  --release-decision "$release_decision"
  --expected-release-decision-status "$expected_decision_status"
  --served-mirror "$served_mirror"
)

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
python3 "$repo_root/scripts/test_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_materialize_public_release_truth_packet.py" >/dev/null
python3 "$repo_root/scripts/materialize_public_release_truth_packet.py" "${release_authority_args[@]}" >/dev/null
if [[ -n "$design_root" ]]; then
  python3 "$design_root/scripts/ai/materialize_public_guide_bundle.py" --repo-root "$design_root" >/dev/null
  python3 "$repo_root/scripts/sync_public_guide_from_design.py" >/dev/null
fi
bash "$repo_root/scripts/verify_public_guide.sh" --skip-http "${release_authority_args[@]}"
python3 "$repo_root/scripts/test_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_installer_update_truth_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_desktop_update_runtime_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_release_verification_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_release_verification_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_release_verification_receipt.py" >/dev/null
