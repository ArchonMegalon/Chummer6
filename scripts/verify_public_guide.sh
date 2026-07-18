#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_root="$repo_root"
skip_http=0
release_mode=0
authority_current="${CHUMMER_RELEASE_AUTHORITY_CURRENT:-}"
registry_commit="${CHUMMER_REGISTRY_COMMIT:-}"
expected_decision_status="${CHUMMER_EXPECTED_RELEASE_DECISION_STATUS:-}"
served_mirror="${CHUMMER_RELEASE_SERVED_MIRROR:-https://chummer.run/downloads/RELEASE_CHANNEL.generated.json}"
sync_args=()

while (($#)); do
  case "$1" in
    --source)
      if (($# < 2)); then
        echo "verify_public_guide.sh: --source requires a path" >&2
        exit 2
      fi
      source_root="$2"
      sync_args+=("$1" "$2")
      shift 2
      ;;
    --source=*)
      source_root="${1#--source=}"
      sync_args+=("$1")
      shift
      ;;
    --skip-http)
      skip_http=1
      shift
      ;;
    --release)
      release_mode=1
      shift
      ;;
    --authority-current)
      (($# >= 2)) || { echo "verify_public_guide.sh: --authority-current requires a path" >&2; exit 2; }
      authority_current="$2"
      shift 2
      ;;
    --registry-commit)
      (($# >= 2)) || { echo "verify_public_guide.sh: --registry-commit requires a SHA" >&2; exit 2; }
      registry_commit="$2"
      shift 2
      ;;
    --expected-release-decision-status)
      (($# >= 2)) || { echo "verify_public_guide.sh: --expected-release-decision-status requires a value" >&2; exit 2; }
      expected_decision_status="$2"
      shift 2
      ;;
    --served-mirror)
      (($# >= 2)) || { echo "verify_public_guide.sh: --served-mirror requires a URL" >&2; exit 2; }
      served_mirror="$2"
      shift 2
      ;;
    *)
      echo "verify_public_guide.sh: unknown option: $1" >&2
      exit 2
      ;;
  esac
done

missing_authority=()
[[ -n "$authority_current" ]] || missing_authority+=(--authority-current)
[[ -n "$registry_commit" ]] || missing_authority+=(--registry-commit)
[[ -n "$expected_decision_status" ]] || missing_authority+=(--expected-release-decision-status)
if ((${#missing_authority[@]})); then
  echo "verify_public_guide.sh: immutable release authority is mandatory; missing: ${missing_authority[*]}" >&2
  exit 2
fi
[[ -f "$authority_current" ]] || { echo "verify_public_guide.sh: authority CURRENT pointer not found: $authority_current" >&2; exit 2; }
[[ "$registry_commit" =~ ^[0-9a-f]{40}$ ]] || { echo "verify_public_guide.sh: Registry commit must be exact lowercase 40-hex" >&2; exit 2; }
case "$expected_decision_status" in
  review_required|preview_ready|stable_ready) ;;
  *) echo "verify_public_guide.sh: unsupported release decision status: $expected_decision_status" >&2; exit 2 ;;
esac
[[ -n "$served_mirror" ]] || { echo "verify_public_guide.sh: served mirror must be nonempty" >&2; exit 2; }

authority_args=(
  --authority-current "$authority_current"
  --registry-commit "$registry_commit"
  --expected-release-decision-status "$expected_decision_status"
  --served-mirror "$served_mirror"
)
if [[ "$release_mode" == "1" ]]; then
  authority_args+=(--release)
fi

python3 "$repo_root/scripts/sync_public_guide_from_design.py" --check "${sync_args[@]}"
python3 -m unittest discover -s "$repo_root/tests" -p 'test_sync_public_guide_from_design.py' >/dev/null
python3 -m unittest discover -s "$repo_root/tests" -p 'test_linux_source_build_script.py' >/dev/null
python3 "$repo_root/scripts/test_verify_linux_source_build_surface.py" >/dev/null
python3 "$repo_root/scripts/test_verify_public_guide_links.py" >/dev/null
link_args=(--root "$source_root" --source-root "$repo_root")
if [[ "$skip_http" == "1" ]]; then
  link_args+=(--skip-http)
fi
python3 "$repo_root/scripts/verify_public_guide_links.py" "${link_args[@]}"
python3 "$repo_root/scripts/verify_public_guide_video_audio.py" --root "$source_root"
python3 "$repo_root/scripts/test_verify_chummer6_docs_release_truth.py" >/dev/null
python3 "$repo_root/scripts/test_verify_public_downloads_match_registry.py" >/dev/null
python3 "$repo_root/scripts/verify_public_guide_first_impression.py" >/dev/null
python3 "$repo_root/scripts/verify_public_downloads_match_registry.py" "${authority_args[@]}" >/dev/null
python3 "$repo_root/scripts/verify_chummer6_docs_release_truth.py" "${authority_args[@]}" >/dev/null
python3 "$repo_root/scripts/verify_origin_dossier_public_guide_surface.py" >/dev/null
python3 "$repo_root/scripts/verify_runbook_press_public_guide_surface.py" >/dev/null
