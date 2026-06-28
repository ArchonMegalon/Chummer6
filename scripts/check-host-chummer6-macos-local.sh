#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
BUILD_SCRIPT="$SCRIPT_DIR/build-chummer6-macos-local.sh"

usage() {
  cat <<'USAGE'
Check whether this macOS host is ready for a local Chummer6 source build.

Usage:
  ./check-host-chummer6-macos-local.sh [options]

Options:
  --base PATH    Workspace base path used for the audit. Default: $HOME/chummer6-source-build-macos
  --help, -h     Show this help.

This wrapper never installs packages and never builds Chummer. It syntax-checks the
checked-in build script, then runs that script in --audit-only mode.
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
CHUMMER_MIN_FREE_GIB="${CHUMMER_MIN_FREE_GIB:-0}" \
  exec bash "$BUILD_SCRIPT" --audit-only "${ARGS[@]}"
