#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_root="$repo_root"
forward_args=("$@")

while (($#)); do
  case "$1" in
    --source)
      if (($# < 2)); then
        echo "verify_public_guide.sh: --source requires a path" >&2
        exit 2
      fi
      source_root="$2"
      shift 2
      ;;
    --source=*)
      source_root="${1#--source=}"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

python3 "$repo_root/scripts/sync_public_guide_from_design.py" --check "${forward_args[@]}"
python3 -m unittest discover -s "$repo_root/tests" -p 'test_sync_public_guide_from_design.py' >/dev/null
python3 "$repo_root/scripts/verify_public_guide_links.py" --root "$source_root"
python3 "$repo_root/scripts/verify_public_guide_video_audio.py" --root "$source_root"
python3 "$repo_root/scripts/test_verify_chummer6_docs_release_truth.py" >/dev/null
python3 "$repo_root/scripts/verify_public_guide_first_impression.py" >/dev/null
python3 "$repo_root/scripts/verify_chummer6_docs_release_truth.py" >/dev/null
python3 "$repo_root/scripts/verify_origin_dossier_public_guide_surface.py" >/dev/null
