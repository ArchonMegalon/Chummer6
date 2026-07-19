#!/usr/bin/env bash
set -euo pipefail

repo_root="${CHUMMER6_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
design_root=""
authority_current="${CHUMMER_RELEASE_AUTHORITY_CURRENT:-}"
registry_commit="${CHUMMER_REGISTRY_COMMIT:-}"
expected_decision_status="${CHUMMER_EXPECTED_RELEASE_DECISION_STATUS:-}"
served_mirror="${CHUMMER_RELEASE_SERVED_MIRROR:-https://chummer.run/downloads/RELEASE_CHANNEL.generated.json}"
expected_linux_archive_sha256="${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256:-}"
expected_linux_archive_python="${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION:-}"

usage() {
  echo "Usage: $0 --authority-current PATH --registry-commit SHA --expected-release-decision-status STATUS --expected-linux-archive-sha256 SHA256 --expected-linux-archive-python-version VERSION [--served-mirror URL]" >&2
}

while (($#)); do
  case "$1" in
    --authority-current)
      (($# >= 2)) || { echo "--authority-current requires a path" >&2; exit 2; }
      authority_current="$2"
      shift 2
      ;;
    --registry-commit)
      (($# >= 2)) || { echo "--registry-commit requires a SHA" >&2; exit 2; }
      registry_commit="$2"
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
    --expected-linux-archive-sha256)
      (($# >= 2)) || { echo "--expected-linux-archive-sha256 requires a digest" >&2; exit 2; }
      expected_linux_archive_sha256="$2"
      shift 2
      ;;
    --expected-linux-archive-python-version)
      (($# >= 2)) || { echo "--expected-linux-archive-python-version requires a version" >&2; exit 2; }
      expected_linux_archive_python="$2"
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
[[ -n "$authority_current" ]] || missing_authority+=(--authority-current)
[[ -n "$registry_commit" ]] || missing_authority+=(--registry-commit)
[[ -n "$expected_decision_status" ]] || missing_authority+=(--expected-release-decision-status)
[[ -n "$expected_linux_archive_sha256" ]] || missing_authority+=(--expected-linux-archive-sha256)
[[ -n "$expected_linux_archive_python" ]] || missing_authority+=(--expected-linux-archive-python-version)
if ((${#missing_authority[@]})); then
  echo "Immutable release authority is mandatory; missing: ${missing_authority[*]}" >&2
  exit 2
fi
[[ -f "$authority_current" ]] || { echo "Authority CURRENT pointer not found: $authority_current" >&2; exit 2; }
[[ "$registry_commit" =~ ^[0-9a-f]{40}$ ]] || { echo "Registry commit must be exact lowercase 40-hex" >&2; exit 2; }
case "$expected_decision_status" in
  review_required|preview_ready|stable_ready) ;;
  *) echo "Unsupported release decision status: $expected_decision_status" >&2; exit 2 ;;
esac
[[ -n "$served_mirror" ]] || { echo "Served mirror must be nonempty" >&2; exit 2; }
[[ "$expected_linux_archive_sha256" =~ ^[0-9a-f]{64}$ ]] || { echo "Expected Linux archive digest must be exact lowercase 64-hex" >&2; exit 2; }
[[ "$expected_linux_archive_python" =~ ^3\.([0-9]+)\.[0-9]+$ ]] || { echo "Expected Linux archive Python must satisfy >=3.11,<4" >&2; exit 2; }
((10#${BASH_REMATCH[1]} >= 11)) || { echo "Expected Linux archive Python must satisfy >=3.11,<4" >&2; exit 2; }

release_authority_args=(
  --release
  --authority-current "$authority_current"
  --registry-commit "$registry_commit"
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

CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256="$expected_linux_archive_sha256" \
CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION="$expected_linux_archive_python" \
  bash "$repo_root/scripts/verify_linux_source_build_docker_gate.sh"
python3 "$repo_root/scripts/test_verify_linux_source_build_docker_gate_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_linux_source_build_docker_gate_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/materialize_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/verify_macos_source_build_contract_receipt.py" >/dev/null
python3 "$repo_root/scripts/test_materialize_public_release_truth_packet.py" >/dev/null
python3 "$repo_root/scripts/materialize_public_release_truth_packet.py" "${release_authority_args[@]}" >/dev/null
if [[ -n "$design_root" ]]; then
  CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT="$repo_root" \
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
