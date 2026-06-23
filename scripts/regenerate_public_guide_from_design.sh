#!/usr/bin/env bash
set -euo pipefail

repo_root="${CHUMMER6_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
design_root="${CHUMMER_DESIGN_REPO_ROOT:-$repo_root/../chummer-design}"
out_path="${CHUMMER_PUBLIC_GUIDE_OUT:-$design_root/products/chummer/public-guide}"
generator_script="${CHUMMER_PUBLIC_GUIDE_GENERATOR:-$design_root/scripts/ai/materialize_public_guide_bundle.py}"
sync_script="${CHUMMER_PUBLIC_GUIDE_SYNC:-$repo_root/scripts/sync_public_guide_from_design.py}"
verify_script="${CHUMMER_PUBLIC_GUIDE_VERIFY:-$repo_root/scripts/verify_public_guide.sh}"
check_mode=0

usage() {
  cat <<'USAGE'
Regenerate the Chummer6 public guide from the design repo, sync it into Chummer6, and verify the result.

Usage:
  ./scripts/regenerate_public_guide_from_design.sh [options]

Options:
  --check             Validate the generated output and sync state without modifying files.
  --out PATH          Override the generated public-guide output directory.
  --design-repo PATH  Override the chummer-design repository root.
  --help, -h          Show this help.

Environment overrides:
  CHUMMER6_REPO_ROOT
  CHUMMER_DESIGN_REPO_ROOT
  CHUMMER_PUBLIC_GUIDE_OUT
  CHUMMER_PUBLIC_GUIDE_GENERATOR
  CHUMMER_PUBLIC_GUIDE_SYNC
  CHUMMER_PUBLIC_GUIDE_VERIFY
USAGE
}

while (($#)); do
  case "$1" in
    --check)
      check_mode=1
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

if [[ "$out_path" != /* ]]; then
  out_path="$design_root/$out_path"
fi

[[ -d "$repo_root" ]] || { echo "Chummer6 repo root not found: $repo_root" >&2; exit 2; }
[[ -d "$design_root" ]] || { echo "Design repo root not found: $design_root" >&2; exit 2; }
[[ -f "$generator_script" ]] || { echo "Generator script not found: $generator_script" >&2; exit 2; }
[[ -f "$sync_script" ]] || { echo "Sync script not found: $sync_script" >&2; exit 2; }
[[ -f "$verify_script" ]] || { echo "Verify script not found: $verify_script" >&2; exit 2; }

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

if [[ "$check_mode" == "1" ]]; then
  generator_args+=(--check)
  sync_args+=(--check)
fi

CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT="$repo_root" python3 "${generator_args[@]}"
python3 "${sync_args[@]}"
bash "${verify_args[@]}"
