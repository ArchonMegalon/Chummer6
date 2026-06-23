#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
BUILD_SCRIPT="$SCRIPT_DIR/build-chummer6-linux.sh"

usage() {
  cat <<'USAGE'
Check whether this Linux host is ready for a Chummer6 source build.

Usage:
  ./check-host-chummer6-linux.sh [options]

Options:
  --base PATH    Workspace base path used for the audit. Default: $HOME/chummer6-source-build
  --help, -h     Show this help.

This wrapper never installs packages and never builds Chummer. It syntax-checks the
checked-in build script, then runs that script in --audit-only mode.

If you only need the package names first, run:
  ./list-chummer6-linux-prereqs.sh
USAGE
}

ARGS=()
while (($#)); do
  case "$1" in
    --base)
      [[ $# -ge 2 ]] || { echo "--base requires a path" >&2; exit 2; }
      ARGS+=("$1" "$2")
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

[[ -f "$BUILD_SCRIPT" ]] || {
  echo "Missing build script: $BUILD_SCRIPT" >&2
  exit 1
}

echo "Checking build script syntax..."
bash -n "$BUILD_SCRIPT"

echo "Running host audit..."
exec bash "$BUILD_SCRIPT" --audit-only "${ARGS[@]}"
