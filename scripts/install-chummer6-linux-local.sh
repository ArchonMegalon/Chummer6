#!/usr/bin/env bash
set -Eeuo pipefail

DEFAULT_BASE="${CHUMMER_BUILD_BASE:-$HOME/chummer6-source-build}"
DEFAULT_DESTINATION="${CHUMMER_LINUX_INSTALL_DESTINATION:-$HOME/.local/opt/chummer6-source-build}"
DEFAULT_COMMAND_LINK="${CHUMMER_LINUX_INSTALL_COMMAND_LINK:-$HOME/.local/bin/chummer6-source-build}"
BASE_PATH=""
ARTIFACT_PATH=""
ARCHIVE_PATH=""
DESTINATION_PATH=""
COMMAND_LINK_PATH=""
FORCE_INSTALL=0
TEMP_ROOT=""

cleanup() {
  if [[ -n "${TEMP_ROOT:-}" && -d "$TEMP_ROOT" ]]; then
    rm -rf "$TEMP_ROOT"
  fi
}
trap cleanup EXIT

usage() {
  cat <<'USAGE'
Install an already built local Chummer6 Linux binary into a user-local directory.

Usage:
  ./install-chummer6-linux-local.sh [options]

Options:
  --base PATH          Build workspace root. Default: $HOME/chummer6-source-build
  --artifact PATH      Published artifact directory to install.
  --archive PATH       .tar.gz archive created by build-chummer6-linux.sh.
  --destination PATH   Final install directory. Default: $HOME/.local/opt/chummer6-source-build
  --command-link PATH  Command symlink to create. Default: $HOME/.local/bin/chummer6-source-build
  --force              Replace an existing install at the destination.
  --help, -h           Show this help.

If neither --artifact nor --archive is given, the script looks under:
  <base>/artifacts/chummer6-linux-x64
  <base>/artifacts/chummer6-linux-arm64

This is a local personal install helper. It only installs an already built
artifact into your home directory, creates a user-local launcher, and does not
claim any public Linux release readiness.
USAGE
}

while (($#)); do
  case "$1" in
    --base)
      [[ $# -ge 2 ]] || { echo "--base requires a path" >&2; exit 2; }
      BASE_PATH="$2"
      shift 2
      ;;
    --artifact)
      [[ $# -ge 2 ]] || { echo "--artifact requires a path" >&2; exit 2; }
      ARTIFACT_PATH="$2"
      shift 2
      ;;
    --archive)
      [[ $# -ge 2 ]] || { echo "--archive requires a path" >&2; exit 2; }
      ARCHIVE_PATH="$2"
      shift 2
      ;;
    --destination)
      [[ $# -ge 2 ]] || { echo "--destination requires a path" >&2; exit 2; }
      DESTINATION_PATH="$2"
      shift 2
      ;;
    --command-link)
      [[ $# -ge 2 ]] || { echo "--command-link requires a path" >&2; exit 2; }
      COMMAND_LINK_PATH="$2"
      shift 2
      ;;
    --force)
      FORCE_INSTALL=1
      shift
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

[[ "$(uname -s)" == "Linux" ]] || { echo "This installer script runs only on Linux." >&2; exit 1; }

if [[ -z "$BASE_PATH" ]]; then
  BASE_PATH="$DEFAULT_BASE"
fi
if [[ "$BASE_PATH" == "~" ]]; then
  BASE_PATH="$HOME"
elif [[ "$BASE_PATH" == ~/* ]]; then
  BASE_PATH="$HOME/${BASE_PATH#~/}"
fi
BASE_PATH="$(mkdir -p "$BASE_PATH" && cd "$BASE_PATH" && pwd -P)"

if [[ -z "$DESTINATION_PATH" ]]; then
  DESTINATION_PATH="$DEFAULT_DESTINATION"
fi
if [[ "$DESTINATION_PATH" == "~" ]]; then
  DESTINATION_PATH="$HOME"
elif [[ "$DESTINATION_PATH" == ~/* ]]; then
  DESTINATION_PATH="$HOME/${DESTINATION_PATH#~/}"
fi
DESTINATION_PATH="$(python3 - "$DESTINATION_PATH" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"

if [[ -z "$COMMAND_LINK_PATH" ]]; then
  COMMAND_LINK_PATH="$DEFAULT_COMMAND_LINK"
fi
if [[ "$COMMAND_LINK_PATH" == "~" ]]; then
  COMMAND_LINK_PATH="$HOME"
elif [[ "$COMMAND_LINK_PATH" == ~/* ]]; then
  COMMAND_LINK_PATH="$HOME/${COMMAND_LINK_PATH#~/}"
fi
COMMAND_LINK_PATH="$(python3 - "$COMMAND_LINK_PATH" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"

resolve_source_dir() {
  if [[ -n "$ARTIFACT_PATH" && -n "$ARCHIVE_PATH" ]]; then
    echo "Use either --artifact or --archive, not both." >&2
    exit 2
  fi

  if [[ -n "$ARTIFACT_PATH" ]]; then
    cd "$ARTIFACT_PATH" && pwd -P
    return
  fi

  if [[ -n "$ARCHIVE_PATH" ]]; then
    [[ -f "$ARCHIVE_PATH" ]] || { echo "Archive not found: $ARCHIVE_PATH" >&2; exit 1; }
    TEMP_ROOT="$(mktemp -d)"
    local extracted="$TEMP_ROOT/extracted"
    mkdir -p "$extracted"
    tar -C "$extracted" -xzf "$ARCHIVE_PATH"
    cd "$extracted" && pwd -P
    return
  fi

  local preferred=""
  case "$(uname -m)" in
    x86_64|amd64) preferred="$BASE_PATH/artifacts/chummer6-linux-x64" ;;
    aarch64|arm64) preferred="$BASE_PATH/artifacts/chummer6-linux-arm64" ;;
  esac
  if [[ -n "$preferred" && -d "$preferred" ]]; then
    cd "$preferred" && pwd -P
    return
  fi

  local fallback=""
  fallback="$(find "$BASE_PATH/artifacts" -maxdepth 1 -mindepth 1 -type d -name 'chummer6-linux-*' -print 2>/dev/null | sort | tail -n 1 || true)"
  if [[ -n "$fallback" && -d "$fallback" ]]; then
    cd "$fallback" && pwd -P
    return
  fi

  echo "Could not find a Linux artifact directory under $BASE_PATH/artifacts." >&2
  echo "Build first with scripts/build-chummer6-linux.sh or pass --artifact/--archive explicitly." >&2
  exit 1
}

SOURCE_DIR="$(resolve_source_dir)"
[[ -f "$SOURCE_DIR/Chummer.Avalonia" ]] || { echo "Source artifact is missing Chummer.Avalonia: $SOURCE_DIR" >&2; exit 1; }

if [[ -e "$DESTINATION_PATH" && "$FORCE_INSTALL" != "1" ]]; then
  echo "Destination already exists: $DESTINATION_PATH" >&2
  echo "Rerun with --force to replace it." >&2
  exit 1
fi

if [[ -e "$COMMAND_LINK_PATH" && "$FORCE_INSTALL" != "1" ]]; then
  echo "Command link already exists: $COMMAND_LINK_PATH" >&2
  echo "Rerun with --force to replace it." >&2
  exit 1
fi

TEMP_ROOT="${TEMP_ROOT:-$(mktemp -d)}"
STAGE_DIR="$TEMP_ROOT/chummer6-source-build"
APP_DIR="$STAGE_DIR/app"
mkdir -p "$APP_DIR"
cp -R "$SOURCE_DIR"/. "$APP_DIR"/

cat > "$STAGE_DIR/run-chummer6.sh" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  HERE="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$HERE/$SOURCE"
done
HERE="$(cd -P "$(dirname "$SOURCE")" && pwd)"
APP_DIR="$HERE/app"
export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"
export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"
exec "$APP_DIR/Chummer.Avalonia" "$@"
LAUNCHER
chmod +x "$STAGE_DIR/run-chummer6.sh"

mkdir -p "$(dirname "$DESTINATION_PATH")"
if [[ -e "$DESTINATION_PATH" ]]; then
  rm -rf "$DESTINATION_PATH"
fi
mv "$STAGE_DIR" "$DESTINATION_PATH"

mkdir -p "$(dirname "$COMMAND_LINK_PATH")"
if [[ -L "$COMMAND_LINK_PATH" || -f "$COMMAND_LINK_PATH" ]]; then
  rm -f "$COMMAND_LINK_PATH"
fi
ln -s "$DESTINATION_PATH/run-chummer6.sh" "$COMMAND_LINK_PATH"

echo "Installed local source build:"
echo "  Install directory: $DESTINATION_PATH"
echo "  Command link:      $COMMAND_LINK_PATH"
echo "  Source:            $SOURCE_DIR"
echo
echo "Run it with:"
echo "  \"$COMMAND_LINK_PATH\""
