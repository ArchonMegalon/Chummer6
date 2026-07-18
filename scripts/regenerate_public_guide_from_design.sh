#!/usr/bin/env bash
set -euo pipefail

repo_root="${CHUMMER6_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
design_root="${CHUMMER_DESIGN_REPO_ROOT:-$repo_root/../chummer-design}"
out_path="${CHUMMER_PUBLIC_GUIDE_OUT:-$design_root/products/chummer/public-guide}"
generator_script="${CHUMMER_PUBLIC_GUIDE_GENERATOR:-$design_root/scripts/ai/materialize_public_guide_bundle.py}"
sync_script="${CHUMMER_PUBLIC_GUIDE_SYNC:-$repo_root/scripts/sync_public_guide_from_design.py}"
verify_script="${CHUMMER_PUBLIC_GUIDE_VERIFY:-$repo_root/scripts/verify_public_guide.sh}"
release_truth_script="${CHUMMER_PUBLIC_RELEASE_TRUTH_PACKET_MATERIALIZER:-$repo_root/scripts/materialize_public_release_truth_packet.py}"
authority_current="${CHUMMER_RELEASE_AUTHORITY_CURRENT:-}"
registry_commit="${CHUMMER_REGISTRY_COMMIT:-}"
expected_decision_status="${CHUMMER_EXPECTED_RELEASE_DECISION_STATUS:-}"
served_mirror="${CHUMMER_RELEASE_SERVED_MIRROR:-https://chummer.run/downloads/RELEASE_CHANNEL.generated.json}"
check_mode=0
release_mode=0

usage() {
  cat <<'USAGE'
Regenerate the Chummer6 public guide from the design repo, sync it into Chummer6, and verify the result.

Usage:
  ./scripts/regenerate_public_guide_from_design.sh [options]

Options:
  --check             Validate the generated output and sync state without modifying files.
  --release           Mark the strict authority checks as a release invocation.
  --out PATH          Override the generated public-guide output directory.
  --design-repo PATH  Override the chummer-design repository root.
  --authority-current PATH
                      Registry CURRENT.json; the immutable generation is derived from it.
  --registry-commit SHA
                      Exact Registry commit bound by the snapshot.
  --expected-release-decision-status STATUS
                      Exact review_required, preview_ready, or stable_ready posture.
  --served-mirror URL Public served mirror recorded separately from authority.
  --help, -h          Show this help.

Environment overrides:
  CHUMMER6_REPO_ROOT
  CHUMMER_DESIGN_REPO_ROOT
  CHUMMER_PUBLIC_GUIDE_OUT
  CHUMMER_PUBLIC_GUIDE_GENERATOR
  CHUMMER_PUBLIC_GUIDE_SYNC
  CHUMMER_PUBLIC_GUIDE_VERIFY
  CHUMMER_RELEASE_AUTHORITY_CURRENT
  CHUMMER_REGISTRY_COMMIT
  CHUMMER_EXPECTED_RELEASE_DECISION_STATUS
  CHUMMER_RELEASE_SERVED_MIRROR
USAGE
}

while (($#)); do
  case "$1" in
    --check)
      check_mode=1
      shift
      ;;
    --release)
      release_mode=1
      shift
      ;;
    --out)
      [[ $# -ge 2 ]] || { echo "--out requires a path" >&2; exit 2; }
      out_path="$2"
      shift 2
      ;;
    --design-repo)
      [[ $# -ge 2 ]] || { echo "--design-repo requires a path" >&2; exit 2; }
      design_root="$2"
      shift 2
      ;;
    --authority-current)
      [[ $# -ge 2 ]] || { echo "--authority-current requires a path" >&2; exit 2; }
      authority_current="$2"
      shift 2
      ;;
    --registry-commit)
      [[ $# -ge 2 ]] || { echo "--registry-commit requires a SHA" >&2; exit 2; }
      registry_commit="$2"
      shift 2
      ;;
    --expected-release-decision-status)
      [[ $# -ge 2 ]] || { echo "--expected-release-decision-status requires a value" >&2; exit 2; }
      expected_decision_status="$2"
      shift 2
      ;;
    --served-mirror)
      [[ $# -ge 2 ]] || { echo "--served-mirror requires a URL" >&2; exit 2; }
      served_mirror="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

missing_authority=()
[[ -n "$authority_current" ]] || missing_authority+=(--authority-current)
[[ -n "$registry_commit" ]] || missing_authority+=(--registry-commit)
[[ -n "$expected_decision_status" ]] || missing_authority+=(--expected-release-decision-status)
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

if [[ "$out_path" != /* ]]; then
  out_path="$design_root/$out_path"
fi

[[ -d "$repo_root" ]] || { echo "Chummer6 repo root not found: $repo_root" >&2; exit 2; }
[[ -d "$design_root" ]] || { echo "Design repo root not found: $design_root" >&2; exit 2; }
[[ -f "$generator_script" ]] || { echo "Generator script not found: $generator_script" >&2; exit 2; }
[[ -f "$sync_script" ]] || { echo "Sync script not found: $sync_script" >&2; exit 2; }
[[ -f "$verify_script" ]] || { echo "Verify script not found: $verify_script" >&2; exit 2; }
[[ -f "$release_truth_script" ]] || { echo "Release truth materializer not found: $release_truth_script" >&2; exit 2; }

generator_args=(
  "$generator_script"
  --repo-root "$design_root"
  --out "$out_path"
)

sync_args=(
  "$sync_script"
  --source "$out_path"
)

verify_args=(
  "$verify_script"
  --source "$out_path"
)

release_truth_args=(
  --authority-current "$authority_current"
  --registry-commit "$registry_commit"
  --expected-release-decision-status "$expected_decision_status"
  --served-mirror "$served_mirror"
)

verify_args+=("${release_truth_args[@]}")

if [[ "$release_mode" == "1" ]]; then
  release_truth_args+=(--release)
  verify_args+=(--release)
fi

if [[ "$check_mode" == "1" ]]; then
  generator_args+=(--check)
  sync_args+=(--check)
  release_truth_args+=(--check)
fi

python3 "$release_truth_script" "${release_truth_args[@]}" >/dev/null
CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT="$repo_root" python3 "${generator_args[@]}"
python3 "${sync_args[@]}"
bash "${verify_args[@]}"
