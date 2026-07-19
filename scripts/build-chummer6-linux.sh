#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_VERSION="3.1.0"
SCRIPT_SOURCE_DIR="${BASH_SOURCE[0]%/*}"
[[ "$SCRIPT_SOURCE_DIR" != "${BASH_SOURCE[0]}" ]] || SCRIPT_SOURCE_DIR="."
SCRIPT_ROOT="$(cd -- "$SCRIPT_SOURCE_DIR" && pwd -P)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_ROOT/.." && pwd -P)"
RELEASE_LOCK_PATH="${CHUMMER_RELEASE_LOCK:-$REPOSITORY_ROOT/RELEASE.lock.json}"
REPO_BASE_URL="${CHUMMER_REPO_BASE_URL:-https://github.com/ArchonMegalon}"
REPO_BASE_URL="${REPO_BASE_URL%/}"
DEFAULT_BASE="${CHUMMER_BUILD_BASE:-${HOME:-/tmp}/chummer6-source-build}"
BASE_PATH=""
TARGET_RID=""
AUDIT_ONLY=0
ALLOW_MOVING_REF=0
MOVING_REF=""
MIN_FREE_GIB="${CHUMMER_MIN_FREE_GIB:-25}"
RUN_ROOT=""
LOG_FILE=""
LOCK_OUTPUT_FILE=""
PYTHON_RUNTIME=""
PYTHON_VERSION=""

usage() {
  cat <<'EOF'
Build the Chummer6 Avalonia client from one immutable Linux source lock.

Usage:
  scripts/build-chummer6-linux.sh [options]

Options:
  --base PATH          Workspace for logs and final artifacts.
  --lock PATH          Immutable RELEASE.lock.json authority.
  --target-rid RID     linux-x64 (native) or linux-arm64 (x64 cross-target).
  --audit-only         Validate the host and complete checked authority graph only.
  --ref REF            A moving ref; requires --allow-moving-ref.
  --allow-moving-ref   Acknowledge a non-reproducible, evidence-ineligible request.
  --yes, -y            Compatibility no-op; this script never installs system packages.
  --skip-system-deps   Compatibility no-op; this script never installs system packages.
  --help, -h           Show this help.

The locked flow clones every repository at its exact 40-character commit, downloads
an exact authenticated SDK archive without executing dotnet-install.sh, composes one
same-run local package feed, restores with no network package sources or siblings,
and keeps releaseEvidenceEligible=false. A moving-ref request is never evidence and
must be converted into a new reviewed lock before a full build can run.

Python is selected deterministically from CHUMMER_PYTHON (when set), then
python3.13, python3.12, python3.11, and python3. The selected runtime must report
Python >=3.11,<4. A discovered compatible path is logged; no host path is hard-coded.
EOF
}

while (($#)); do
  case "$1" in
    --base)
      [[ $# -ge 2 ]] || { echo "--base requires a path" >&2; exit 2; }
      BASE_PATH="$2"; shift 2 ;;
    --lock)
      [[ $# -ge 2 ]] || { echo "--lock requires a path" >&2; exit 2; }
      RELEASE_LOCK_PATH="$2"; shift 2 ;;
    --target-rid)
      [[ $# -ge 2 ]] || { echo "--target-rid requires a value" >&2; exit 2; }
      TARGET_RID="$2"; shift 2 ;;
    --ref)
      [[ $# -ge 2 ]] || { echo "--ref requires a value" >&2; exit 2; }
      MOVING_REF="$2"; shift 2 ;;
    --allow-moving-ref) ALLOW_MOVING_REF=1; shift ;;
    --audit-only) AUDIT_ONLY=1; shift ;;
    --yes|-y|--skip-system-deps) shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -n "$MOVING_REF" && "$ALLOW_MOVING_REF" != "1" ]]; then
  echo "--ref requires --allow-moving-ref; locked builds never resolve a branch." >&2
  exit 2
fi
if [[ "$ALLOW_MOVING_REF" == "1" ]]; then
  MOVING_REF="${MOVING_REF:-main}"
fi
case "${TARGET_RID:-linux-x64}" in
  linux-x64|linux-arm64) ;;
  *) echo "--target-rid must be linux-x64 or linux-arm64" >&2; exit 2 ;;
esac
[[ "$MIN_FREE_GIB" =~ ^[0-9]+$ ]] || {
  echo "CHUMMER_MIN_FREE_GIB must be a whole number of GiB." >&2
  exit 2
}

select_python() {
  local candidates=()
  local candidate resolved version
  if [[ -n "${CHUMMER_PYTHON:-}" ]]; then
    candidates=("$CHUMMER_PYTHON")
  elif [[ -n "${CHUMMER_PYTHON_CANDIDATES:-}" ]]; then
    # Test/automation override; words are still checked in the declared order.
    read -r -a candidates <<<"$CHUMMER_PYTHON_CANDIDATES"
  else
    candidates=(python3.13 python3.12 python3.11 python3)
  fi
  for candidate in "${candidates[@]}"; do
    resolved="$(command -v -- "$candidate" 2>/dev/null || true)"
    [[ -n "$resolved" && -x "$resolved" ]] || continue
    version="$($resolved -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null || true)"
    [[ "$version" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]] || continue
    if ((10#${BASH_REMATCH[1]} == 3 && 10#${BASH_REMATCH[2]} >= 11)); then
      PYTHON_RUNTIME="$resolved"
      PYTHON_VERSION="$version"
      return 0
    fi
  done
  echo "Python >=3.11,<4 is required; no declared candidate passed explicit version validation." >&2
  return 1
}

select_python
printf 'Selected Python %s at discovered path %s\n' "$PYTHON_VERSION" "$PYTHON_RUNTIME"

if [[ -z "$BASE_PATH" ]]; then
  BASE_PATH="$DEFAULT_BASE"
fi
if [[ "$BASE_PATH" == "~" ]]; then
  BASE_PATH="${HOME:-/tmp}"
elif [[ "$BASE_PATH" == ~/* ]]; then
  BASE_PATH="${HOME:-/tmp}/${BASE_PATH#~/}"
fi
mkdir -p -- "$BASE_PATH"
BASE_PATH="$(cd -- "$BASE_PATH" && pwd -P)"
mkdir -p -- "$BASE_PATH/logs" "$BASE_PATH/artifacts"
LOG_FILE="$BASE_PATH/logs/linux-source-build-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
exec > >(tee -a "$LOG_FILE") 2>&1

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
download_https() {
  local output="$1" url="$2"
  curl --disable --fail --location --retry 5 --retry-delay 2 \
    --proto '=https' --tlsv1.2 --output "$output" "$url"
}
emit_sanitized_phase_failure() {
  local phase="$1" status="$2" diagnostic="$3"
  local diagnostic_bytes bounded_diagnostic
  local diagnostic_limit_bytes=131072
  if ! diagnostic_bytes="$(wc -c <"$diagnostic")"; then
    printf 'PHASE_FAILURE phase=%s exit=%s diagnostic_status=unreadable\n' \
      "$phase" "$status" >&2
    return 1
  fi
  printf 'PHASE_FAILURE phase=%s exit=%s diagnostic_bytes=%s diagnostic_limit_bytes=%s\n' \
    "$phase" "$status" "$diagnostic_bytes" "$diagnostic_limit_bytes" >&2
  if ((diagnostic_bytes == 0)); then
    printf 'ERROR: phase %s emitted no diagnostic output.\n' "$phase" >&2
    return 0
  fi
  bounded_diagnostic="$diagnostic"
  if ((diagnostic_bytes > diagnostic_limit_bytes)); then
    bounded_diagnostic="$RUN_ROOT/${phase}.diagnostic.bounded"
    if ! tail -c "$diagnostic_limit_bytes" "$diagnostic" >"$bounded_diagnostic"; then
      printf 'ERROR: could not bound diagnostic output for phase %s.\n' "$phase" >&2
      return 1
    fi
    printf 'PHASE_DIAGNOSTIC phase=%s truncated=true retained=tail\n' "$phase" >&2
  fi
  if ! "$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" sanitize-diagnostics \
    --input "$bounded_diagnostic" --redact-path "$RUN_ROOT" \
    --redact-path "$BASE_PATH" --redact-path "$REPOSITORY_ROOT" >&2; then
    printf 'ERROR: could not sanitize diagnostic output for phase %s.\n' "$phase" >&2
    return 1
  fi
}

cleanup() {
  local code=$?
  trap - EXIT
  if [[ -n "${LOCK_OUTPUT_FILE:-}" && "$LOCK_OUTPUT_FILE" == "$BASE_PATH"/.source-lock-inspect.* && -f "$LOCK_OUTPUT_FILE" ]]; then
    rm -f -- "$LOCK_OUTPUT_FILE"
  fi
  if [[ -n "${RUN_ROOT:-}" && "$RUN_ROOT" == "$BASE_PATH"/.source-run.* && -d "$RUN_ROOT" ]]; then
    rm -rf -- "$RUN_ROOT"
  fi
  return "$code"
}
on_error() {
  local code=$?
  printf 'Build failed at line %s (exit %s). Sanitized diagnostics remain in %s.\n' "$1" "$code" "$LOG_FILE" >&2
  exit "$code"
}
on_signal() {
  printf 'Build interrupted by %s; removing ephemeral configuration and workspaces.\n' "$1" >&2
  case "$1" in HUP) exit 129 ;; INT) exit 130 ;; TERM) exit 143 ;; *) exit 1 ;; esac
}
trap cleanup EXIT
trap 'on_error "$LINENO"' ERR
trap 'on_signal HUP' HUP
trap 'on_signal INT' INT
trap 'on_signal TERM' TERM

log "Python runtime: $PYTHON_VERSION (requirement >=3.11,<4)"

LOCK_OUTPUT_FILE="$(mktemp "$BASE_PATH/.source-lock-inspect.XXXXXX")"
chmod 600 "$LOCK_OUTPUT_FILE"
if [[ "${CHUMMER_SOURCE_BUILD_TEST_MODE:-0}" == "1" && "${CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION:-}" == "prelock-wait" ]]; then
  printf 'PRELOCK_CLEANUP_TEST_READY %s\n' "$LOCK_OUTPUT_FILE"
  while :; do sleep 1; done
fi
if ! "$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" inspect \
  --lock "$RELEASE_LOCK_PATH" --repo-root "$REPOSITORY_ROOT" >"$LOCK_OUTPUT_FILE" 2>&1; then
  "$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" sanitize-diagnostics \
    --input "$LOCK_OUTPUT_FILE" --redact-path "$BASE_PATH" --redact-path "$REPOSITORY_ROOT" >&2 || true
  rm -f -- "$LOCK_OUTPUT_FILE"
  exit 1
fi
LOCK_OUTPUT="$(<"$LOCK_OUTPUT_FILE")"
rm -f -- "$LOCK_OUTPUT_FILE"
LOCK_OUTPUT_FILE=""

REPO_DIRS=(); REPO_NAMES=(); REPO_COMMITS=()
SDK_ARCHIVE_RIDS=(); SDK_ARCHIVE_URLS=(); SDK_ARCHIVE_NAMES=()
SDK_ARCHIVE_SHA256S=(); SDK_ARCHIVE_SHA512S=(); SDK_ARCHIVE_SIZES=()
NUGET_RIDS=()
NUGET_CACHE_PATHS=(); NUGET_CACHE_SHA256S=(); NUGET_RID_FEED_PATHS=()
NUGET_PROJECT_LOCK_RIDS=(); NUGET_PROJECT_LOCK_PROJECTS=()
NUGET_PROJECT_LOCK_PATHS=(); NUGET_PROJECT_LOCK_SHA256S=()
SOURCE_LOCK_SHA256=""; SDK_VERSION=""; SDK_AUTHORITY_PATH=""; SDK_AUTHORITY_SHA256=""
RELEASE_MANIFEST_SHA256=""; RELEASE_MANIFEST_STATUS=""; RELEASE_EVIDENCE_ELIGIBLE=""
UI_LOCK_PATH=""; UI_LOCK_SHA256=""; UI_VERIFIER_PATH=""; UI_VERIFIER_SHA256=""
UI_COMMIT=""; UI_RECEIPT_PATH=""; UI_RECEIPT_SHA256=""
COMPOSER_PATH=""; COMPOSER_SHA256=""; FEED_INVENTORY_PATH=""; NORMALIZATION_PROOF_PATH=""
RUNTIME_AUTHORITY_PATH=""; SOURCE_LOCK_VERIFIER_PATH=""; SOURCE_LOCK_VERIFIER_SHA256=""
while IFS=$'\t' read -r record first second third fourth fifth sixth; do
  case "$record" in
    LOCK_SHA256) SOURCE_LOCK_SHA256="$first" ;;
    SDK_VERSION) SDK_VERSION="$first" ;;
    SDK_AUTHORITY) SDK_AUTHORITY_PATH="$first"; SDK_AUTHORITY_SHA256="$second" ;;
    SDK_ARCHIVE)
      SDK_ARCHIVE_RIDS+=("$first"); SDK_ARCHIVE_URLS+=("$second"); SDK_ARCHIVE_NAMES+=("$third")
      SDK_ARCHIVE_SHA256S+=("$fourth"); SDK_ARCHIVE_SHA512S+=("$fifth"); SDK_ARCHIVE_SIZES+=("$sixth") ;;
    RELEASE_MANIFEST_SHA256) RELEASE_MANIFEST_SHA256="$first" ;;
    RELEASE_MANIFEST_STATUS) RELEASE_MANIFEST_STATUS="$first" ;;
    RELEASE_EVIDENCE_ELIGIBLE) RELEASE_EVIDENCE_ELIGIBLE="$first" ;;
    REPOSITORY) REPO_DIRS+=("$first"); REPO_NAMES+=("$second"); REPO_COMMITS+=("$third") ;;
    UI_PACKAGE_PLANE)
      UI_LOCK_PATH="$first"; UI_LOCK_SHA256="$second"; UI_VERIFIER_PATH="$third"; UI_VERIFIER_SHA256="$fourth" ;;
    UI_CONSUMER) UI_COMMIT="$first"; UI_RECEIPT_PATH="$second"; UI_RECEIPT_SHA256="$third" ;;
    PACKAGE_COMPOSER) COMPOSER_PATH="$first"; COMPOSER_SHA256="$second" ;;
    PACKAGE_AUTHORITIES)
      FEED_INVENTORY_PATH="$first"; NORMALIZATION_PROOF_PATH="$second"; RUNTIME_AUTHORITY_PATH="$third" ;;
    SOURCE_LOCK_VERIFIER)
      SOURCE_LOCK_VERIFIER_PATH="$first"; SOURCE_LOCK_VERIFIER_SHA256="$second" ;;
    NUGET_PROJECT_LOCK)
      NUGET_PROJECT_LOCK_RIDS+=("$first"); NUGET_PROJECT_LOCK_PROJECTS+=("$second")
      NUGET_PROJECT_LOCK_PATHS+=("$third"); NUGET_PROJECT_LOCK_SHA256S+=("$fourth") ;;
    NUGET_PACKAGE_PLANE)
      NUGET_RIDS+=("$first"); NUGET_CACHE_PATHS+=("$second"); NUGET_CACHE_SHA256S+=("$third")
      NUGET_RID_FEED_PATHS+=("$fourth") ;;
    "") ;;
    *) die "Unknown source-lock resolver record: $record" ;;
  esac
done <<<"$LOCK_OUTPUT"

[[ ${#REPO_DIRS[@]} -eq 5 ]] || die "Source lock did not resolve exactly five repositories."
[[ ${#SDK_ARCHIVE_RIDS[@]} -eq 2 ]] || die "Source lock did not resolve both SDK archives."
[[ ${#NUGET_RIDS[@]} -eq 2 ]] || die "Source lock did not resolve both RID package planes."
[[ ${#NUGET_PROJECT_LOCK_RIDS[@]} -eq 6 ]] || die "Source lock did not resolve the exact six project lock files."
[[ "$SOURCE_LOCK_VERIFIER_PATH" == "scripts/verify_linux_source_lock.py" ]] || \
  die "Source lock did not resolve the canonical verifier path."
[[ "$SOURCE_LOCK_VERIFIER_SHA256" =~ ^[0-9a-f]{64}$ ]] || \
  die "Source lock did not resolve the canonical verifier digest."
[[ "$(sha256sum "$REPOSITORY_ROOT/$SOURCE_LOCK_VERIFIER_PATH" | awk '{print $1}')" == "$SOURCE_LOCK_VERIFIER_SHA256" ]] || \
  die "Resolved source-lock verifier bytes differ from their exact authority."
[[ "$RELEASE_EVIDENCE_ELIGIBLE" == "false" ]] || die "Review-only source lock unexpectedly claimed release evidence eligibility."
for commit in "${REPO_COMMITS[@]}"; do
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]] || die "Repository authority contains a mutable or malformed revision."
done

HOST_MACHINE="$(uname -m)"
case "$HOST_MACHINE" in
  x86_64|amd64) HOST_RID="linux-x64" ;;
  aarch64|arm64) HOST_RID="linux-arm64" ;;
  *) die "Unsupported host architecture: $HOST_MACHINE" ;;
esac
TARGET_RID="${TARGET_RID:-$HOST_RID}"
if [[ "$HOST_RID" != "linux-x64" && "$AUDIT_ONLY" != "1" ]]; then
  die "Native linux-arm64 cache execution is not yet observed. Use audit-only; do not claim native ARM evidence."
fi
if [[ "$TARGET_RID" == "linux-x64" && "$HOST_RID" != "linux-x64" ]]; then
  die "linux-x64 cross-target execution is not an authorized model."
fi

log "Source lock SHA256: $SOURCE_LOCK_SHA256"
log "Release posture: $RELEASE_MANIFEST_STATUS; release evidence eligible: false"
log "Host/target: $HOST_RID -> $TARGET_RID"
if [[ "$ALLOW_MOVING_REF" == "1" ]]; then
  log "NON-REPRODUCIBLE REQUEST: moving ref '$MOVING_REF'; NOT RELEASE EVIDENCE."
  if [[ "$AUDIT_ONLY" != "1" ]]; then
    die "A moving ref cannot consume the checked immutable package plane. Generate and review a new lock first."
  fi
fi

AVAILABLE_KIB="$(df -Pk "$BASE_PATH" | awk 'NR==2 {print $4}')"
[[ "$AVAILABLE_KIB" =~ ^[0-9]+$ ]] || die "Could not determine free disk space."
if ((AVAILABLE_KIB < MIN_FREE_GIB * 1024 * 1024)); then
  die "At least $MIN_FREE_GIB GiB free is required."
fi
for command_name in git curl tar gzip sha256sum; do
  command -v "$command_name" >/dev/null 2>&1 || die "Missing required build tool: $command_name"
done
if [[ "$AUDIT_ONLY" == "1" ]]; then
  printf 'Audit complete: immutable source lock, Python %s, %s -> %s, five exact commits.\n' \
    "$PYTHON_VERSION" "$HOST_RID" "$TARGET_RID"
  exit 0
fi

RUN_ROOT="$(mktemp -d "$BASE_PATH/.source-run.XXXXXXXX")"
chmod 700 "$RUN_ROOT"
while IFS= read -r ambient_git_config; do
  case "$ambient_git_config" in
    GIT_CONFIG_COUNT|GIT_CONFIG_KEY_*|GIT_CONFIG_VALUE_*) unset "$ambient_git_config" ;;
  esac
done < <(compgen -A variable GIT_CONFIG_ || true)
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0

# Behavioral trap harness for repository tests. It never creates credentials.
if [[ "${CHUMMER_SOURCE_BUILD_TEST_MODE:-0}" == "1" ]]; then
  printf '<configuration><packageSources><clear /></packageSources></configuration>\n' >"$RUN_ROOT/NuGet.Config"
  case "${CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION:-}" in
    normal) exit 0 ;;
    error) false ;;
    materializer-error|materializer-empty-error)
      MATERIALIZER_DIAGNOSTIC="$RUN_ROOT/materializer.diagnostic"
      MATERIALIZER_STATUS=0
      if [[ "${CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION}" == "materializer-error" ]]; then
        if "$PYTHON_RUNTIME" -c \
          'import sys; print("x" * 140000, file=sys.stderr); print(f"synthetic materializer failure at {sys.argv[1]} from {sys.argv[2]} Authorization:" + " Bearer phase-secret-sentinel", file=sys.stderr); raise SystemExit(23)' \
          "$RUN_ROOT" "$REPOSITORY_ROOT" >"$MATERIALIZER_DIAGNOSTIC" 2>&1; then
          MATERIALIZER_STATUS=0
        else
          MATERIALIZER_STATUS=$?
        fi
      elif "$PYTHON_RUNTIME" -c 'raise SystemExit(24)' \
        >"$MATERIALIZER_DIAGNOSTIC" 2>&1; then
        MATERIALIZER_STATUS=0
      else
        MATERIALIZER_STATUS=$?
      fi
      if ! emit_sanitized_phase_failure \
        "same-run-package-plane-materialization" "$MATERIALIZER_STATUS" "$MATERIALIZER_DIAGNOSTIC"; then
        die "could not emit sanitized package-plane failure diagnostics"
      fi
      die "same-run package-plane materialization failed (exit $MATERIALIZER_STATUS)"
      ;;
    curl-config)
      download_https "$RUN_ROOT/curl-test-output" "https://example.invalid/sdk.tar.gz"
      exit 0 ;;
    wait)
      printf 'CLEANUP_TEST_READY %s\n' "$RUN_ROOT"
      while :; do sleep 1; done ;;
  esac
fi

CHECKOUT_ROOT="$RUN_ROOT/checkouts"
PACKAGE_PLANE_ROOT="$RUN_ROOT/package-plane"
SDK_ROOT="$RUN_ROOT/sdk"
SDK_ARCHIVE="$RUN_ROOT/sdk.tar.gz"
RESTORE_CACHE="$RUN_ROOT/nuget-packages"
PUBLISH_ROOT="$RUN_ROOT/publish"
mkdir -p "$CHECKOUT_ROOT" "$RESTORE_CACHE" "$PUBLISH_ROOT"

normalize_git_url() {
  local value="$1"
  value="${value%.git}"; value="${value%/}"
  printf '%s' "$value"
}
clone_exact() {
  local directory="$1" repository="$2" commit="$3"
  local target="$CHECKOUT_ROOT/$directory" expected="$REPO_BASE_URL/$repository.git"
  mkdir -p "$target"
  git -c gc.auto=0 -c maintenance.auto=0 -C "$target" init -q
  git -C "$target" remote add origin "$expected"
  git -c protocol.file.allow=always -C "$target" fetch --depth 1 origin "$commit"
  git -C "$target" checkout -q --detach FETCH_HEAD
  [[ "$(git -C "$target" rev-parse HEAD)" == "$commit" ]] || die "$repository did not resolve exact commit $commit"
  [[ "$(normalize_git_url "$(git -C "$target" remote get-url origin)")" == "$(normalize_git_url "$expected")" ]] || die "$repository origin changed"
  [[ -z "$(git -C "$target" status --porcelain=v1 --untracked-files=all)" ]] || die "$repository checkout is dirty"
}

if [[ "${CHUMMER_SOURCE_BUILD_TEST_MODE:-0}" == "1" && "${CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION:-}" == "clone-exact" ]]; then
  [[ -n "${CHUMMER_SOURCE_BUILD_TEST_REPOSITORY:-}" && -n "${CHUMMER_SOURCE_BUILD_TEST_COMMIT:-}" ]] || die "clone-exact test requires repository and commit"
  clone_exact test-locked-clone "$CHUMMER_SOURCE_BUILD_TEST_REPOSITORY" "$CHUMMER_SOURCE_BUILD_TEST_COMMIT"
  printf 'CLONE_EXACT_HEAD %s\n' "$(git -C "$CHECKOUT_ROOT/test-locked-clone" rev-parse HEAD)"
  exit 0
fi

log "Cloning five exact repository commits (never branch heads)."
for index in "${!REPO_DIRS[@]}"; do
  clone_exact "${REPO_DIRS[$index]}" "${REPO_NAMES[$index]}" "${REPO_COMMITS[$index]}"
done
"$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" verify-checkouts \
  --lock "$RELEASE_LOCK_PATH" --repo-root "$REPOSITORY_ROOT" --base "$CHECKOUT_ROOT"

SDK_INDEX=-1
for index in "${!SDK_ARCHIVE_RIDS[@]}"; do
  [[ "${SDK_ARCHIVE_RIDS[$index]}" == "$HOST_RID" ]] && SDK_INDEX="$index"
done
((SDK_INDEX >= 0)) || die "No SDK archive authority exists for $HOST_RID"
if [[ -n "${CHUMMER_SDK_ARCHIVE:-}" ]]; then
  cp -- "$CHUMMER_SDK_ARCHIVE" "$SDK_ARCHIVE"
else
  download_https "$SDK_ARCHIVE" "${SDK_ARCHIVE_URLS[$SDK_INDEX]}"
fi
"$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" install-sdk \
  --lock "$RELEASE_LOCK_PATH" --repo-root "$REPOSITORY_ROOT" --rid "$HOST_RID" \
  --archive "$SDK_ARCHIVE" --output "$SDK_ROOT"
DOTNET="$SDK_ROOT/dotnet"

export DOTNET_ROOT="$SDK_ROOT"
export PATH="$SDK_ROOT:$PATH"
export DOTNET_MULTILEVEL_LOOKUP=0 DOTNET_NOLOGO=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1 AVALONIA_TELEMETRY_OPTOUT=1
export DOTNET_CLI_HOME="$RUN_ROOT/dotnet-home" XDG_CACHE_HOME="$RUN_ROOT/xdg-cache"
export XDG_CONFIG_HOME="$RUN_ROOT/xdg-config" XDG_DATA_HOME="$RUN_ROOT/xdg-data"
export NUGET_HTTP_CACHE_PATH="$RUN_ROOT/nuget-http" NUGET_PLUGINS_CACHE_PATH="$RUN_ROOT/nuget-plugins"
export NUGET_SCRATCH="$RUN_ROOT/nuget-scratch" NUGET_PACKAGES="$RESTORE_CACHE"
unset CHUMMER_PUBLISHED_FEED_SOURCES CHUMMER_LOCAL_CONTRACTS_PROJECT \
  CHUMMER_LOCAL_CAMPAIGN_CONTRACTS_PROJECT CHUMMER_LOCAL_PLAY_CONTRACTS_PROJECT \
  CHUMMER_LOCAL_RUN_CONTRACTS_PROJECT CHUMMER_LOCAL_HUB_REGISTRY_CONTRACTS_PROJECT \
  CHUMMER_LOCAL_UI_KIT_PROJECT RestoreSources RestoreAdditionalProjectSources \
  RestoreFallbackFolders NUGET_CONFIG_FILE

MATERIALIZER_DIAGNOSTIC="$RUN_ROOT/materializer.diagnostic"
if "$PYTHON_RUNTIME" "$REPOSITORY_ROOT/$COMPOSER_PATH" \
    --ui-root "$CHECKOUT_ROOT/chummer6-ui" --owners-root "$CHECKOUT_ROOT" \
    --sdk-root "$SDK_ROOT" --sdk-authority "$REPOSITORY_ROOT/$SDK_AUTHORITY_PATH" \
    --runtime-authority "$REPOSITORY_ROOT/$RUNTIME_AUTHORITY_PATH" \
    --upstream-verification-receipt "$REPOSITORY_ROOT/$UI_RECEIPT_PATH" \
    --output-root "$PACKAGE_PLANE_ROOT" --host-rid "$HOST_RID" --ui-commit "$UI_COMMIT" \
    --ui-lock-path "$UI_LOCK_PATH" --ui-lock-sha256 "$UI_LOCK_SHA256" \
    --ui-verifier-path "$UI_VERIFIER_PATH" --ui-verifier-sha256 "$UI_VERIFIER_SHA256" \
    --expected-feed-inventory "$REPOSITORY_ROOT/$FEED_INVENTORY_PATH" \
    --expected-normalization-proof "$REPOSITORY_ROOT/$NORMALIZATION_PROOF_PATH" \
    --expected-x64-inventory "$REPOSITORY_ROOT/release-locks/linux-x64-restore-feed.inventory.json" \
    --expected-arm64-inventory "$REPOSITORY_ROOT/release-locks/linux-arm64-restore-feed.inventory.json" \
    >"$MATERIALIZER_DIAGNOSTIC" 2>&1; then
  MATERIALIZER_STATUS=0
else
  MATERIALIZER_STATUS=$?
fi
if ((MATERIALIZER_STATUS != 0)); then
  if ! emit_sanitized_phase_failure \
    "same-run-package-plane-materialization" "$MATERIALIZER_STATUS" "$MATERIALIZER_DIAGNOSTIC"; then
    die "could not emit sanitized package-plane failure diagnostics"
  fi
  die "same-run package-plane materialization failed (exit $MATERIALIZER_STATUS)"
fi
"$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" sanitize-diagnostics \
  --input "$MATERIALIZER_DIAGNOSTIC" --redact-path "$RUN_ROOT" \
  --redact-path "$BASE_PATH" --redact-path "$REPOSITORY_ROOT"

RID_INDEX=-1
for index in "${!NUGET_RIDS[@]}"; do
  [[ "${NUGET_RIDS[$index]}" == "$TARGET_RID" ]] && RID_INDEX="$index"
done
((RID_INDEX >= 0)) || die "No exact NuGet package plane exists for $TARGET_RID"
FEED="$PACKAGE_PLANE_ROOT/rid-feeds/$TARGET_RID"

ISOLATED_ROOT="$RUN_ROOT/consumer"
mkdir -p "$ISOLATED_ROOT"
mv -- "$CHECKOUT_ROOT/chummer6-ui" "$ISOLATED_ROOT/chummer6-ui"
UI_ROOT="$ISOLATED_ROOT/chummer6-ui"
NUGET_CONFIG="$UI_ROOT/NuGet.Config"
"$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" write-nuget-config \
  --feed "$FEED" --packages-root "$RESTORE_CACHE" --output "$NUGET_CONFIG"

PROJECT_RELATIVE="Chummer.Avalonia/Chummer.Avalonia.csproj"
PROJECT_LOCK_COUNT=0
for index in "${!NUGET_PROJECT_LOCK_RIDS[@]}"; do
  [[ "${NUGET_PROJECT_LOCK_RIDS[$index]}" == "$TARGET_RID" ]] || continue
  project="${NUGET_PROJECT_LOCK_PROJECTS[$index]}"
  case "$project" in
    Chummer.Avalonia/Chummer.Avalonia.csproj|\
    Chummer.Desktop.Runtime/Chummer.Desktop.Runtime.csproj|\
    Chummer.Presentation/Chummer.Presentation.csproj) ;;
    *) die "Source lock emitted an unsupported project lock target: $project" ;;
  esac
  project_directory="$UI_ROOT/${project%/*}"
  [[ -d "$project_directory" && ! -L "$project_directory" ]] || \
    die "Project lock destination is missing or unsafe: $project"
  package_lock="$project_directory/packages.lock.json"
  [[ ! -e "$package_lock" && ! -L "$package_lock" ]] || \
    die "Refusing to replace a project package lock: $project"
  cp -- "$REPOSITORY_ROOT/${NUGET_PROJECT_LOCK_PATHS[$index]}" "$package_lock"
  [[ "$(sha256sum "$package_lock" | awk '{print $1}')" == \
    "${NUGET_PROJECT_LOCK_SHA256S[$index]}" ]] || \
    die "Copied project package lock differs: $project"
  ((PROJECT_LOCK_COUNT += 1))
done
[[ "$PROJECT_LOCK_COUNT" -eq 3 ]] || \
  die "Target package plane did not install exactly three project lock files."

(
  cd "$UI_ROOT"
  "$DOTNET" restore "$PROJECT_RELATIVE" --runtime "$TARGET_RID" --locked-mode \
    --configfile NuGet.Config --packages "$RESTORE_CACHE" \
    -p:ChummerUseLocalCompatibilityTree=false
)
"$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" verify-nuget-cache \
  --lock "$RELEASE_LOCK_PATH" --repo-root "$REPOSITORY_ROOT" --rid "$TARGET_RID" \
  --feed "$FEED" --packages-root "$RESTORE_CACHE"

(
  cd "$UI_ROOT"
  "$DOTNET" publish "$PROJECT_RELATIVE" --configuration Release --framework net10.0 \
    --runtime "$TARGET_RID" --no-restore --output "$PUBLISH_ROOT" \
    -p:ChummerUseLocalCompatibilityTree=false -p:ContinuousIntegrationBuild=true \
    -p:Deterministic=true -p:PathMap="$RUN_ROOT=/_/src" \
    -p:DebugType=None -p:DebugSymbols=false
)
"$PYTHON_RUNTIME" "$SCRIPT_ROOT/verify_linux_source_lock.py" verify-nuget-cache \
  --lock "$RELEASE_LOCK_PATH" --repo-root "$REPOSITORY_ROOT" --rid "$TARGET_RID" \
  --feed "$FEED" --packages-root "$RESTORE_CACHE"
[[ ! -e "$PUBLISH_ROOT/Chummer.Avalonia.pdb" ]] || \
  die "Source artifact unexpectedly contains a path-bearing application PDB."

SOURCE_DATE_EPOCH=0
for index in "${!REPO_DIRS[@]}"; do
  revision_root="$CHECKOUT_ROOT/${REPO_DIRS[$index]}"
  [[ "${REPO_DIRS[$index]}" != "chummer6-ui" ]] || revision_root="$UI_ROOT"
  commit_epoch="$(git -C "$revision_root" show -s --format=%ct "${REPO_COMMITS[$index]}")"
  ((commit_epoch > SOURCE_DATE_EPOCH)) && SOURCE_DATE_EPOCH="$commit_epoch"
done
export SOURCE_DATE_EPOCH
ARTIFACT_DIR="$BASE_PATH/artifacts/chummer6-$TARGET_RID"
[[ ! -e "$ARTIFACT_DIR" ]] || die "Refusing to replace existing artifact authority: $ARTIFACT_DIR"
STAGE="$RUN_ROOT/artifact-stage"
mkdir -p "$STAGE"
cp -a "$PUBLISH_ROOT/." "$STAGE/"
{
  printf 'contract=chummer6.linux-source-build/v2\n'
  printf 'scriptVersion=%s\n' "$SCRIPT_VERSION"
  printf 'sourceLockSha256=%s\n' "$SOURCE_LOCK_SHA256"
  printf 'sdkVersion=%s\n' "$SDK_VERSION"
  printf 'pythonRequirement=>=3.11,<4\n'
  printf 'pythonRole=authenticated-orchestrator\n'
  printf 'targetRid=%s\n' "$TARGET_RID"
  printf 'releaseManifestStatus=%s\n' "$RELEASE_MANIFEST_STATUS"
  printf 'releaseManifestSha256=%s\n' "$RELEASE_MANIFEST_SHA256"
  printf 'releaseEvidenceEligible=false\n'
  printf 'debugSymbols=none\n'
  printf 'artifactPathPortability=passed\n'
  printf 'artifactModeNormalization=passed\n'
  for index in "${!REPO_DIRS[@]}"; do
    printf 'repository.%s=%s\n' "${REPO_DIRS[$index]}" "${REPO_COMMITS[$index]}"
  done
} >"$STAGE/BUILD-MANIFEST.txt"

"$PYTHON_RUNTIME" - "$STAGE" "$RUN_ROOT" "$BASE_PATH" "$REPOSITORY_ROOT" "$UI_ROOT" <<'PY'
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

stage = Path(sys.argv[1])
actual_roots = [Path(value).resolve() for value in sys.argv[2:]]
home = os.environ.get("HOME")
if home and Path(home).is_absolute():
    actual_roots.append(Path(home).resolve())

forbidden = {
    b"/tmp/",
    b"/var/tmp/",
    b"/docker/",
    b"/workspace/",
    b".source-run.",
}
for root in actual_roots:
    encoded = os.fsencode(root)
    if len(encoded) > 1:
        forbidden.add(encoded)
    if root.name.startswith(".source-run."):
        forbidden.add(os.fsencode(root.name))

violations: list[str] = []
stage.chmod(0o755)
for path in sorted(stage.rglob("*")):
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        violations.append(f"{path.relative_to(stage)}: symbolic links are not portable")
        continue
    if stat.S_ISDIR(metadata.st_mode):
        path.chmod(0o755)
        continue
    if not stat.S_ISREG(metadata.st_mode):
        violations.append(f"{path.relative_to(stage)}: special files are not portable")
        continue
    path.chmod(0o644)
    payload = path.read_bytes()
    matched = sorted(token for token in forbidden if token in payload)
    if matched:
        rendered = ", ".join(os.fsdecode(token) for token in matched)
        violations.append(f"{path.relative_to(stage)}: {rendered}")

main_executable = stage / "Chummer.Avalonia"
try:
    main_metadata = main_executable.lstat()
except OSError:
    violations.append("Chummer.Avalonia: main executable is missing")
else:
    if not stat.S_ISREG(main_metadata.st_mode) or stat.S_ISLNK(main_metadata.st_mode):
        violations.append("Chummer.Avalonia: main executable is not a regular file")
    else:
        main_executable.chmod(0o755)

if violations:
    print("Published source artifact contains machine-local path bytes:", file=sys.stderr)
    for violation in violations:
        print(f"  {violation}", file=sys.stderr)
    raise SystemExit(1)

for path in [stage, *sorted(stage.rglob("*"))]:
    metadata = path.lstat()
    if stat.S_ISDIR(metadata.st_mode):
        expected_mode = 0o755
    elif stat.S_ISREG(metadata.st_mode):
        expected_mode = 0o755 if path == main_executable else 0o644
    else:
        continue
    actual_mode = stat.S_IMODE(metadata.st_mode)
    if actual_mode != expected_mode:
        raise SystemExit(
            f"artifact mode normalization failed: {path.relative_to(stage)} "
            f"has {actual_mode:04o}, expected {expected_mode:04o}"
        )

print(
    "Artifact path portability and modes verified: "
    f"{sum(1 for path in stage.rglob('*') if path.is_file())} files"
)
PY

ARCHIVE_NAME="chummer6-$TARGET_RID-source-lock.tar.gz"
ARCHIVE_TEMP="$RUN_ROOT/$ARCHIVE_NAME"
(cd "$STAGE" && tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner -cf - .) | gzip -n >"$ARCHIVE_TEMP"
(cd "$RUN_ROOT" && sha256sum "$ARCHIVE_NAME" >"$ARCHIVE_NAME.sha256")
mv -- "$ARCHIVE_TEMP" "$RUN_ROOT/$ARCHIVE_NAME.sha256" "$STAGE/"
mv -- "$STAGE" "$ARTIFACT_DIR"
ARCHIVE="$ARTIFACT_DIR/$ARCHIVE_NAME"

printf '\nBuild complete (review-only; never release evidence).\n'
printf 'Artifact: %s\nArchive:  %s\nSHA256:   %s\nLog:      %s\n' \
  "$ARTIFACT_DIR" "$ARCHIVE" "$(sha256sum "$ARCHIVE" | awk '{print $1}')" "$LOG_FILE"
