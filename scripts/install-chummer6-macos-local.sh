#!/usr/bin/env bash
set -Eeuo pipefail

DEFAULT_BASE="${CHUMMER_BUILD_BASE:-$HOME/chummer6-source-build-macos}"
DEFAULT_DESTINATION="${CHUMMER_MAC_INSTALL_DESTINATION:-$HOME/Applications/Chummer6 Source Build.app}"
BASE_PATH=""
ARTIFACT_PATH=""
ARCHIVE_PATH=""
DESTINATION_PATH=""
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
Install an already built local Chummer6 macOS binary into a personal .app bundle.

Usage:
  ./install-chummer6-macos-local.sh [options]

Options:
  --base PATH         Build workspace root. Default: $HOME/chummer6-source-build-macos
  --artifact PATH     Published artifact directory to install.
  --archive PATH      .tar.gz archive created by build-chummer6-macos-local.sh.
  --destination PATH  Final .app path. Default: $HOME/Applications/Chummer6 Source Build.app
  --force             Replace an existing install at the destination.
  --help, -h          Show this help.

If neither --artifact nor --archive is given, the script looks under:
  <base>/artifacts/chummer6-osx-arm64
  <base>/artifacts/chummer6-osx-x64

This is a local personal install helper. It only installs an already built
artifact into an unsigned .app bundle and does not claim any public macOS
support or release readiness.
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

[[ "$(uname -s)" == "Darwin" ]] || { echo "This installer script runs only on macOS." >&2; exit 1; }

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
    arm64|aarch64) preferred="$BASE_PATH/artifacts/chummer6-osx-arm64" ;;
    x86_64|amd64) preferred="$BASE_PATH/artifacts/chummer6-osx-x64" ;;
  esac
  if [[ -n "$preferred" && -d "$preferred" ]]; then
    cd "$preferred" && pwd -P
    return
  fi

  local fallback=""
  fallback="$(find "$BASE_PATH/artifacts" -maxdepth 1 -mindepth 1 -type d -name 'chummer6-osx-*' -print 2>/dev/null | sort | tail -n 1 || true)"
  if [[ -n "$fallback" && -d "$fallback" ]]; then
    cd "$fallback" && pwd -P
    return
  fi

  echo "Could not find a macOS artifact directory under $BASE_PATH/artifacts." >&2
  echo "Build first with scripts/build-chummer6-macos-local.sh or pass --artifact/--archive explicitly." >&2
  exit 1
}

SOURCE_DIR="$(resolve_source_dir)"
[[ -f "$SOURCE_DIR/Chummer.Avalonia" ]] || { echo "Source artifact is missing Chummer.Avalonia: $SOURCE_DIR" >&2; exit 1; }

if [[ -e "$DESTINATION_PATH" && "$FORCE_INSTALL" != "1" ]]; then
  echo "Destination already exists: $DESTINATION_PATH" >&2
  echo "Rerun with --force to replace it." >&2
  exit 1
fi

TEMP_ROOT="${TEMP_ROOT:-$(mktemp -d)}"
STAGE_BUNDLE="$TEMP_ROOT/Chummer6 Source Build.app"
PAYLOAD_DIR="$STAGE_BUNDLE/Contents/Resources/app"
MACOS_DIR="$STAGE_BUNDLE/Contents/MacOS"
RESOURCES_DIR="$STAGE_BUNDLE/Contents/Resources"

mkdir -p "$PAYLOAD_DIR" "$MACOS_DIR" "$RESOURCES_DIR"
cp -R "$SOURCE_DIR"/. "$PAYLOAD_DIR"/

ICON_SOURCE=""
for candidate in \
  "$SOURCE_DIR/chummer.icns" \
  "$BASE_PATH/chummer6-ui/Chummer/Resources/chummer.icns"; do
  if [[ -f "$candidate" ]]; then
    ICON_SOURCE="$candidate"
    break
  fi
done

if [[ -n "$ICON_SOURCE" ]]; then
  cp "$ICON_SOURCE" "$RESOURCES_DIR/chummer.icns"
fi

cat > "$MACOS_DIR/launch-chummer6" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  HERE="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$HERE/$SOURCE"
done
HERE="$(cd -P "$(dirname "$SOURCE")" && pwd)"
PAYLOAD_DIR="$HERE/../Resources/app"
export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"
export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"
exec "$PAYLOAD_DIR/Chummer.Avalonia" "$@"
LAUNCHER
chmod +x "$MACOS_DIR/launch-chummer6"

cat > "$STAGE_BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleDisplayName</key>
  <string>Chummer6 Source Build</string>
  <key>CFBundleExecutable</key>
  <string>launch-chummer6</string>
  <key>CFBundleIdentifier</key>
  <string>run.chummer.sourcebuild</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>Chummer6 Source Build</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>source-build</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

if [[ -n "$ICON_SOURCE" ]]; then
  /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string chummer.icns" "$STAGE_BUNDLE/Contents/Info.plist" >/dev/null 2>&1 || true
fi

if [[ -f "$SOURCE_DIR/BUILD-MANIFEST.txt" ]]; then
  cp "$SOURCE_DIR/BUILD-MANIFEST.txt" "$RESOURCES_DIR/BUILD-MANIFEST.txt"
fi

mkdir -p "$(dirname "$DESTINATION_PATH")"
if [[ -e "$DESTINATION_PATH" ]]; then
  rm -rf "$DESTINATION_PATH"
fi
mv "$STAGE_BUNDLE" "$DESTINATION_PATH"

if command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$DESTINATION_PATH" >/dev/null 2>&1 || true
fi

echo "Installed local source build:"
echo "  App bundle: $DESTINATION_PATH"
echo "  Source:     $SOURCE_DIR"
echo
echo "Open it with:"
echo "  open \"$DESTINATION_PATH\""
