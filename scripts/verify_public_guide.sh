#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$repo_root/scripts/sync_public_guide_from_design.py" --check "$@"
python3 -m unittest discover -s "$repo_root/tests" -p 'test_sync_public_guide_from_design.py' >/dev/null
python3 -m unittest "$repo_root/scripts/test_verify_chummer6_docs_release_truth.py" >/dev/null
python3 "$repo_root/scripts/verify_chummer6_docs_release_truth.py" >/dev/null
