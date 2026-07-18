#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_VERSION="2.1.0"
SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPOSITORY_ROOT="$(cd "$SCRIPT_ROOT/.." && pwd -P)"
GITHUB_ORG="${CHUMMER_GITHUB_ORG:-ArchonMegalon}"
REPO_BASE_URL="${CHUMMER_REPO_BASE_URL:-https://github.com/$GITHUB_ORG}"
REPO_BASE_URL="${REPO_BASE_URL%/}"
GIT_REF="${CHUMMER_GIT_REF:-}"
RELEASE_LOCK_PATH="${CHUMMER_RELEASE_LOCK:-$REPOSITORY_ROOT/RELEASE.lock.json}"
ALLOW_MOVING_REF=0
SOURCE_MODE="locked"
MIN_FREE_GIB="${CHUMMER_MIN_FREE_GIB:-25}"
DEFAULT_HOME="${HOME:-/tmp}"
DEFAULT_BASE="${CHUMMER_BUILD_BASE:-$DEFAULT_HOME/chummer6-source-build}"
BASE_PATH=""
ASSUME_YES=0
AUDIT_ONLY=0
TOTAL_STEPS=11
CURRENT_STEP=0
START_SECONDS=$SECONDS
LOG_FILE=""
KEEP_BUILD_TEMP="${CHUMMER_KEEP_BUILD_TEMP:-0}"

usage() {
  cat <<'USAGE'
Build the Chummer6 Avalonia desktop client from source for this Linux computer.

Usage:
  ./build-chummer6-linux.sh [options]

Options:
  --base PATH          Workspace base path. Prompts when omitted.
  --lock PATH          Immutable source lock. Default: repository RELEASE.lock.json.
  --ref REF            Moving Git branch or tag. Requires --allow-moving-ref.
  --allow-moving-ref   Permit a non-reproducible moving-ref build. Never release evidence.
  --yes, -y            Accepted for compatibility; no longer changes behavior.
  --skip-system-deps   Accepted for compatibility; the script never installs Linux system packages.
  --audit-only         Check this host and script setup without cloning or building.
  --help, -h           Show this help.

Environment overrides:
  CHUMMER_BUILD_BASE, CHUMMER_RELEASE_LOCK, CHUMMER_GIT_REF,
  CHUMMER_MIN_FREE_GIB, CHUMMER_GITHUB_ORG, CHUMMER_REPO_BASE_URL,
  CHUMMER_KEEP_BUILD_TEMP

By default every owner repository, the .NET SDK installer, NuGet service
index, and per-RID resolved package graph are selected from RELEASE.lock.json.
A branch such as main is accepted only with --allow-moving-ref and is always
marked as non-release evidence.

This script only builds the binary and archive artifacts. It never installs
the user-local copy. Install the result later with ./install-chummer6-linux-local.sh.
USAGE
}

while (($#)); do
  case "$1" in
    --base)
      [[ $# -ge 2 ]] || { echo "--base requires a path" >&2; exit 2; }
      BASE_PATH="$2"
      shift 2
      ;;
    --ref)
      [[ $# -ge 2 ]] || { echo "--ref requires a value" >&2; exit 2; }
      GIT_REF="$2"
      shift 2
      ;;
    --lock)
      [[ $# -ge 2 ]] || { echo "--lock requires a path" >&2; exit 2; }
      RELEASE_LOCK_PATH="$2"
      shift 2
      ;;
    --allow-moving-ref)
      ALLOW_MOVING_REF=1
      shift
      ;;
    --yes|-y)
      ASSUME_YES=1
      shift
      ;;
    --skip-system-deps)
      shift
      ;;
    --audit-only)
      AUDIT_ONLY=1
      TOTAL_STEPS=3
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

if [[ -n "$GIT_REF" && "$ALLOW_MOVING_REF" != "1" ]]; then
  echo "--ref and CHUMMER_GIT_REF require --allow-moving-ref; the default build uses immutable RELEASE.lock.json commits." >&2
  exit 2
fi
if [[ "$ALLOW_MOVING_REF" == "1" ]]; then
  SOURCE_MODE="moving_ref"
  GIT_REF="${GIT_REF:-main}"
fi

command -v python3 >/dev/null 2>&1 || { echo "python3 is required to validate RELEASE.lock.json." >&2; exit 1; }
LOCK_OUTPUT=""
if ! LOCK_OUTPUT="$(python3 "$SCRIPT_ROOT/verify_linux_source_lock.py" inspect --lock "$RELEASE_LOCK_PATH" --repo-root "$REPOSITORY_ROOT" 2>&1)"; then
  printf '%s\n' "$LOCK_OUTPUT" >&2
  exit 1
fi

REPO_DIRS=()
REPO_NAMES=()
LOCKED_COMMITS=()
NUGET_SERVICE_INDEX_URLS=()
NUGET_SERVICE_INDEX_SHA256S=()
NUGET_SERVICE_INDEX_KEYS=()
NUGET_PACKAGE_LOCK_RIDS=()
NUGET_PACKAGE_LOCK_PATHS=()
NUGET_PACKAGE_LOCK_SHA256S=()
SOURCE_LOCK_SHA256=""
SDK_VERSION=""
DOTNET_INSTALL_URL=""
DOTNET_INSTALL_SHA256=""
RELEASE_MANIFEST_SHA256=""
RELEASE_MANIFEST_STATUS=""
RELEASE_EVIDENCE_ELIGIBLE=""
while IFS=$'\t' read -r record first second third; do
  case "$record" in
    LOCK_SHA256) SOURCE_LOCK_SHA256="$first" ;;
    SDK_VERSION) SDK_VERSION="$first" ;;
    DOTNET_INSTALL_URL) DOTNET_INSTALL_URL="$first" ;;
    DOTNET_INSTALL_SHA256) DOTNET_INSTALL_SHA256="$first" ;;
    RELEASE_MANIFEST_SHA256) RELEASE_MANIFEST_SHA256="$first" ;;
    RELEASE_MANIFEST_STATUS) RELEASE_MANIFEST_STATUS="$first" ;;
    RELEASE_EVIDENCE_ELIGIBLE) RELEASE_EVIDENCE_ELIGIBLE="$first" ;;
    REPOSITORY)
      REPO_DIRS+=("$first")
      REPO_NAMES+=("$second")
      LOCKED_COMMITS+=("$third")
      ;;
    NUGET_SERVICE_INDEX)
      NUGET_SERVICE_INDEX_KEYS+=("$first")
      NUGET_SERVICE_INDEX_URLS+=("$second")
      NUGET_SERVICE_INDEX_SHA256S+=("$third")
      ;;
    NUGET_PACKAGE_LOCK)
      NUGET_PACKAGE_LOCK_RIDS+=("$first")
      NUGET_PACKAGE_LOCK_PATHS+=("$second")
      NUGET_PACKAGE_LOCK_SHA256S+=("$third")
      ;;
    "") ;;
    *) echo "Unknown source-lock resolver record: $record" >&2; exit 1 ;;
  esac
done <<< "$LOCK_OUTPUT"

[[ ${#REPO_DIRS[@]} -eq 5 ]] || { echo "Source lock did not resolve the exact five-repository build plane." >&2; exit 1; }
[[ ${#NUGET_SERVICE_INDEX_URLS[@]} -eq 1 ]] || { echo "Source lock did not resolve the exact approved NuGet service index." >&2; exit 1; }
[[ ${#NUGET_PACKAGE_LOCK_RIDS[@]} -eq 2 ]] || { echo "Source lock did not resolve both Linux NuGet package locks." >&2; exit 1; }
if [[ "$SOURCE_MODE" == "moving_ref" ]]; then
  RELEASE_EVIDENCE_ELIGIBLE="false"
fi

[[ "$MIN_FREE_GIB" =~ ^[0-9]+$ ]] || { echo "CHUMMER_MIN_FREE_GIB must be a whole number of GiB." >&2; exit 2; }

if [[ -z "$BASE_PATH" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "Base path for Chummer6 source and build files [$DEFAULT_BASE]: " BASE_PATH
    BASE_PATH="${BASE_PATH:-$DEFAULT_BASE}"
  else
    BASE_PATH="$DEFAULT_BASE"
  fi
fi

if [[ "$BASE_PATH" == "~" ]]; then
  BASE_PATH="$HOME"
elif [[ "$BASE_PATH" == ~/* ]]; then
  BASE_PATH="$HOME/${BASE_PATH#~/}"
fi
mkdir -p "$BASE_PATH"
BASE_PATH="$(cd "$BASE_PATH" && pwd -P)"

mkdir -p "$BASE_PATH/logs"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$BASE_PATH/logs/linux-desktop-build-$RUN_ID.log"
exec > >(tee -a "$LOG_FILE") 2>&1

if [[ -t 1 ]]; then
  BOLD=$'\033[1m'
  GREEN=$'\033[32m'
  YELLOW=$'\033[33m'
  RED=$'\033[31m'
  RESET=$'\033[0m'
else
  BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

log() {
  printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"
}

step() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  local percent=$((CURRENT_STEP * 100 / TOTAL_STEPS))
  printf '\n%s[%d/%d · %d%%] %s%s\n' "$BOLD" "$CURRENT_STEP" "$TOTAL_STEPS" "$percent" "$*" "$RESET"
}

warn() {
  printf '%sWARNING:%s %s\n' "$YELLOW" "$RESET" "$*" >&2
}

die() {
  printf '%sERROR:%s %s\n' "$RED" "$RESET" "$*" >&2
  exit 1
}

on_error() {
  local code=$?
  cleanup_build_temp || true
  printf '\n%sBuild failed%s at line %s with exit code %s.\n' "$RED" "$RESET" "$1" "$code" >&2
  printf 'Full log: %s\n' "$LOG_FILE" >&2
  exit "$code"
}
trap 'on_error "$LINENO"' ERR

cleanup_build_temp() {
  if [[ "${KEEP_BUILD_TEMP:-0}" == "1" || "${KEEP_BUILD_TEMP:-0}" == "true" || "${KEEP_BUILD_TEMP:-0}" == "yes" ]]; then
    return 0
  fi

  if [[ -n "${BASE_PATH:-}" && -d "$BASE_PATH/.tmp" ]]; then
    rm -rf "$BASE_PATH/.tmp"
  fi

  if [[ -n "${BASE_PATH:-}" && -d "$BASE_PATH" ]]; then
    find "$BASE_PATH" -mindepth 2 -maxdepth 2 -type d -name .tmp -prune -exec rm -rf {} +
  fi

  if [[ -n "${DOTNET_INSTALL:-}" && -f "$DOTNET_INSTALL" ]]; then
    rm -f "$DOTNET_INSTALL"
  fi
  if [[ -n "${NUGET_INDEX_PROBE:-}" && -f "$NUGET_INDEX_PROBE" ]]; then
    rm -f "$NUGET_INDEX_PROBE"
  fi
}

clear_ambient_restore_overrides() {
  unset \
    CHUMMER_PUBLISHED_FEED_SOURCES \
    CHUMMER_CONTRACTS_PACKAGE_VERSION \
    CHUMMER_CAMPAIGN_CONTRACTS_PACKAGE_VERSION \
    CHUMMER_RUN_CONTRACTS_PACKAGE_VERSION \
    CHUMMER_HUB_REGISTRY_CONTRACTS_PACKAGE_VERSION \
    CHUMMER_UI_KIT_PACKAGE_VERSION \
    CHUMMER_LOCAL_CONTRACTS_PROJECT \
    CHUMMER_LOCAL_CAMPAIGN_CONTRACTS_PROJECT \
    CHUMMER_LOCAL_PLAY_CONTRACTS_PROJECT \
    CHUMMER_LOCAL_RUN_CONTRACTS_PROJECT \
    CHUMMER_LOCAL_HUB_REGISTRY_CONTRACTS_PROJECT \
    CHUMMER_LOCAL_UI_KIT_PROJECT \
    CHUMMER_LOCAL_MEDIA_CONTRACTS_PROJECT \
    CHUMMER_BOOTSTRAP_ENGINE_CONTRACTS_SCRIPT \
    CHUMMER_ENGINE_CONTRACTS_FEED \
    CHUMMER_BOOTSTRAP_ENGINE_CONTRACTS_FEED \
    CHUMMER_PACKAGE_PLANE_LOCK_ROOT \
    CHUMMER_PACKAGE_PLANE_LOCK_FILE \
    CHUMMER_PACKAGE_PLANE_LOCK_WAIT_SECONDS \
    CHUMMER_PACKAGE_PLANE_LOCK_HELD \
    CHUMMER_PACKAGE_PLANE_SERIALIZE \
    CHUMMER_PACKAGE_PLANE_PREBUILD_CONFIGURATION \
    CHUMMER_UI_REPO_ROOT_ALIAS \
    NUGET_PACKAGES \
    NUGET_HTTP_CACHE_PATH \
    NUGET_PLUGINS_CACHE_PATH \
    NUGET_SCRATCH \
    NUGET_CONFIG_FILE \
    RestoreConfigFile \
    RestoreSources \
    RestoreAdditionalProjectSources \
    RestoreFallbackFolders \
    RestorePackagesPath \
    RestoreLockedMode \
    RestorePackagesWithLockFile \
    RestoreForceEvaluate \
    ChummerContractsPackageVersion \
    ChummerCampaignContractsPackageVersion \
    ChummerRunContractsPackageVersion \
    ChummerHubRegistryContractsPackageVersion \
    ChummerUiKitPackageVersion
}

read_host_information() {
  DISTRO_ID="unknown"
  DISTRO_ID_LIKE=""
  DISTRO_VERSION="unknown"
  DISTRO_PRETTY="Unknown Linux"
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    DISTRO_ID="${ID:-unknown}"
    DISTRO_ID_LIKE="${ID_LIKE:-}"
    DISTRO_VERSION="${VERSION_ID:-unknown}"
    DISTRO_PRETTY="${PRETTY_NAME:-$DISTRO_ID $DISTRO_VERSION}"
  fi

  CPU_ARCH="$(uname -m)"
  case "$CPU_ARCH" in
    x86_64|amd64) RID="linux-x64" ;;
    aarch64|arm64) RID="linux-arm64" ;;
    *) die "Unsupported CPU architecture '$CPU_ARCH'. Supported: x86_64 and aarch64." ;;
  esac

  CPU_MODEL="unknown"
  if command -v lscpu >/dev/null 2>&1; then
    CPU_MODEL="$(lscpu | awk -F: '/Model name/ {sub(/^[ \t]+/, "", $2); print $2; exit}')"
  elif [[ -r /proc/cpuinfo ]]; then
    CPU_MODEL="$(awk -F: '/model name|Hardware/ {sub(/^[ \t]+/, "", $2); print $2; exit}' /proc/cpuinfo)"
  fi
  CPU_MODEL="${CPU_MODEL:-unknown}"
  CPU_CORES="$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null || echo 1)"
  MEMORY_KIB="$(awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
  MEMORY_GIB=$((MEMORY_KIB / 1024 / 1024))

  if command -v getconf >/dev/null 2>&1 && getconf GNU_LIBC_VERSION >/dev/null 2>&1; then
    LIBC_INFO="$(getconf GNU_LIBC_VERSION)"
  else
    LIBC_INFO="$(ldd --version 2>&1 | head -1 || true)"
  fi
  if grep -qi musl <<<"$LIBC_INFO" || [[ -f /etc/alpine-release ]]; then
    die "This host uses musl/Alpine. The current Chummer6 desktop build targets glibc Linux."
  fi
}

choose_package_manager() {
  local all_ids=" $DISTRO_ID $DISTRO_ID_LIKE "
  if [[ "$all_ids" == *" debian "* || "$all_ids" == *" ubuntu "* || "$all_ids" == *" linuxmint "* ]] && command -v apt-get >/dev/null 2>&1; then
    printf 'apt'
  elif [[ "$all_ids" == *" fedora "* || "$all_ids" == *" rhel "* || "$all_ids" == *" centos "* || "$all_ids" == *" rocky "* || "$all_ids" == *" almalinux "* ]] && command -v dnf >/dev/null 2>&1; then
    printf 'dnf'
  elif [[ "$all_ids" == *" arch "* || "$all_ids" == *" manjaro "* ]] && command -v pacman >/dev/null 2>&1; then
    printf 'pacman'
  elif [[ "$all_ids" == *" suse "* || "$all_ids" == *" opensuse "* ]] && command -v zypper >/dev/null 2>&1; then
    printf 'zypper'
  elif command -v apt-get >/dev/null 2>&1; then printf 'apt'
  elif command -v dnf >/dev/null 2>&1; then printf 'dnf'
  elif command -v pacman >/dev/null 2>&1; then printf 'pacman'
  elif command -v zypper >/dev/null 2>&1; then printf 'zypper'
  else printf ''
  fi
}

check_required_commands() {
  local missing=()
  for command_name in git git-lfs curl tar gzip flock sha256sum file python3; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      missing+=("$command_name")
    fi
  done
  if ((${#missing[@]} == 0)); then
    return 0
  fi
  local manager
  manager="$(choose_package_manager)"
  local hint=""
  case "$manager" in
    apt) hint="Install them first, for example: apt-get install git git-lfs curl tar gzip unzip xz-utils util-linux file" ;;
    dnf) hint="Install them first, for example: dnf install git git-lfs curl tar gzip unzip xz util-linux file" ;;
    pacman) hint="Install them first, for example: pacman -S --needed git git-lfs curl tar gzip unzip xz util-linux file" ;;
    zypper) hint="Install them first, for example: zypper install git git-lfs curl tar gzip unzip xz util-linux file" ;;
    *) hint="Install the missing tools with your package manager, then rerun the script." ;;
  esac
  die "Missing required build tools: ${missing[*]}. $hint"
}

check_git_lfs_ready() {
  if ! git lfs version >/dev/null 2>&1; then
    die "Git LFS is required but not ready. Install git-lfs with your package manager, run 'git lfs install', then rerun the script."
  fi
}

dotnet_runtime_hint() {
  local manager
  manager="$(choose_package_manager)"
  case "$manager" in
    apt) printf '%s' "Install ICU first, for example: apt-get install libicu72 or the current libicu package for your distro." ;;
    dnf) printf '%s' "Install ICU first, for example: dnf install libicu." ;;
    pacman) printf '%s' "Install ICU first, for example: pacman -S --needed icu." ;;
    zypper) printf '%s' "Install ICU first, for example: zypper install libicu." ;;
    *) printf '%s' "Install the ICU runtime package for your distro, then rerun the script." ;;
  esac
}

check_local_dotnet_runtime() {
  local info_output=""
  if info_output="$(dotnet --info 2>&1)"; then
    printf '%s\n' "$info_output"
    return 0
  fi
  if grep -qi "Couldn't find a valid ICU package installed" <<<"$info_output"; then
    die "The local .NET SDK started, but this host is missing the ICU runtime needed by dotnet. $(dotnet_runtime_hint)"
  fi
  printf '%s\n' "$info_output" >&2
  die "The local .NET SDK could not start on this host. Check the log above, install the required runtime libraries, and rerun the script."
}

step "Inspecting this Linux host"
[[ "$(uname -s)" == "Linux" ]] || die "This script builds only the Linux desktop client."
read_host_information
NUGET_PACKAGE_LOCK_RELATIVE=""
NUGET_PACKAGE_LOCK_SHA256=""
for index in "${!NUGET_PACKAGE_LOCK_RIDS[@]}"; do
  if [[ "${NUGET_PACKAGE_LOCK_RIDS[$index]}" == "$RID" ]]; then
    NUGET_PACKAGE_LOCK_RELATIVE="${NUGET_PACKAGE_LOCK_PATHS[$index]}"
    NUGET_PACKAGE_LOCK_SHA256="${NUGET_PACKAGE_LOCK_SHA256S[$index]}"
    break
  fi
done
[[ -n "$NUGET_PACKAGE_LOCK_RELATIVE" && -n "$NUGET_PACKAGE_LOCK_SHA256" ]] || die "No locked NuGet graph exists for $RID."
NUGET_PACKAGE_LOCK_SOURCE="$REPOSITORY_ROOT/$NUGET_PACKAGE_LOCK_RELATIVE"
log "Distribution: $DISTRO_PRETTY"
log "CPU: $CPU_MODEL"
log "Architecture: $CPU_ARCH → $RID"
log "Logical CPUs: $CPU_CORES"
log "Memory: ${MEMORY_GIB} GiB"
log "C library: $LIBC_INFO"
if (( MEMORY_GIB > 0 && MEMORY_GIB < 8 )); then
  warn "Less than 8 GiB RAM is available. The build may be slow or fail under memory pressure."
fi

step "Checking workspace permissions and free disk space"
mkdir -p "$BASE_PATH"
WRITE_TEST="$BASE_PATH/.chummer-write-test-$$"
printf 'ok\n' > "$WRITE_TEST"
rm -f "$WRITE_TEST"
EXEC_TEST="$BASE_PATH/.chummer-exec-test-$$.sh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$EXEC_TEST"
chmod +x "$EXEC_TEST"
if ! "$EXEC_TEST"; then
  rm -f "$EXEC_TEST"
  die "The selected base path is mounted noexec or cannot execute files: $BASE_PATH"
fi
rm -f "$EXEC_TEST"

AVAILABLE_KIB="$(df -Pk "$BASE_PATH" | awk 'NR==2 {print $4}')"
REQUIRED_KIB=$((MIN_FREE_GIB * 1024 * 1024))
[[ "$AVAILABLE_KIB" =~ ^[0-9]+$ ]] || die "Could not determine free disk space for $BASE_PATH"
if (( AVAILABLE_KIB < REQUIRED_KIB )); then
  AVAILABLE_GIB=$((AVAILABLE_KIB / 1024 / 1024))
  die "At least ${MIN_FREE_GIB} GiB free is required; only ${AVAILABLE_GIB} GiB is available at $BASE_PATH."
fi
log "Workspace: $BASE_PATH"
if [[ "$SOURCE_MODE" == "locked" ]]; then
  log "Source mode: immutable lock $RELEASE_LOCK_PATH"
  log "Source lock SHA256: $SOURCE_LOCK_SHA256"
else
  warn "NON-REPRODUCIBLE BUILD: moving ref '$GIT_REF' was explicitly allowed. This output is NOT release evidence."
  log "Source mode: explicitly allowed moving ref $GIT_REF"
fi
log "Free space: $((AVAILABLE_KIB / 1024 / 1024)) GiB"

step "Checking Linux build prerequisites"
PACKAGE_MANAGER="$(choose_package_manager)"
if [[ -n "$PACKAGE_MANAGER" ]]; then
  log "Detected package manager: $PACKAGE_MANAGER"
else
  warn "No supported package manager detected. Install prerequisites manually before the full build."
fi

if [[ "$AUDIT_ONLY" == "1" ]]; then
  for command_name in git git-lfs curl tar gzip flock sha256sum file python3; do
    if command -v "$command_name" >/dev/null 2>&1; then
      log "Found command: $command_name"
    else
      warn "Missing command for full build: $command_name"
    fi
  done
  ELAPSED=$((SECONDS - START_SECONDS))
  printf '\n%sAudit complete.%s\n' "$GREEN$BOLD" "$RESET"
  printf 'Host:      %s · %s · %s\n' "$DISTRO_PRETTY" "$CPU_ARCH" "$CPU_MODEL"
  printf 'Workspace: %s\n' "$BASE_PATH"
  printf 'Log:       %s\n' "$LOG_FILE"
  printf 'Elapsed:   %dm %ds\n' "$((ELAPSED / 60))" "$((ELAPSED % 60))"
  exit 0
fi

if [[ "$ASSUME_YES" == "1" ]]; then
  warn "--yes is accepted for compatibility, but the script no longer installs system packages."
fi
check_required_commands
check_git_lfs_ready
git lfs install --skip-repo >/dev/null

step "Cloning or updating the Chummer6 build repositories"

normalize_git_url() {
  local value="$1"
  value="${value%.git}"
  value="${value%/}"
  printf '%s' "$value"
}

git_automation() {
  git -c gc.auto=0 -c maintenance.auto=0 "$@"
}

sync_repo() {
  local directory_name="$1"
  local repository_name="$2"
  local locked_commit="$3"
  local target="$BASE_PATH/$directory_name"
  local expected_url="$REPO_BASE_URL/$repository_name.git"

  if [[ ! -e "$target" ]]; then
    log "Cloning $repository_name into $directory_name"
    if [[ "$SOURCE_MODE" == "locked" ]]; then
      mkdir -p "$target"
      git_automation -C "$target" init -q
      git_automation -C "$target" remote add origin "$expected_url"
      git_automation -C "$target" fetch --depth 1 origin "$locked_commit"
      git_automation -C "$target" checkout -q --detach FETCH_HEAD
    else
      git_automation clone --depth 1 --filter=blob:none --branch "$GIT_REF" "$expected_url" "$target"
    fi
  else
    [[ -d "$target/.git" ]] || die "$target exists but is not a Git repository."
    local current_url
    current_url="$(git_automation -C "$target" remote get-url origin)"
    if [[ "$(normalize_git_url "$current_url")" != "$(normalize_git_url "$expected_url")" ]]; then
      die "$target has unexpected origin '$current_url'; expected '$expected_url'."
    fi
    if [[ -n "$(git_automation -C "$target" status --porcelain)" ]]; then
      die "$target has local changes. Commit, stash, or remove them before rerunning."
    fi
    log "Updating $repository_name"
    if [[ "$SOURCE_MODE" == "locked" ]]; then
      git_automation -C "$target" fetch --depth 1 origin "$locked_commit"
    else
      git_automation -C "$target" fetch --depth 1 origin "$GIT_REF"
    fi
    git_automation -C "$target" checkout -q --detach FETCH_HEAD
  fi

  if [[ "$SOURCE_MODE" == "locked" ]]; then
    local actual_commit
    actual_commit="$(git_automation -C "$target" rev-parse HEAD)"
    [[ "$actual_commit" == "$locked_commit" ]] || die "$repository_name resolved to $actual_commit; lock requires $locked_commit."
  fi

  if [[ -f "$target/.gitattributes" ]] && grep -q 'filter=lfs' "$target/.gitattributes"; then
    git_automation -C "$target" lfs install --local >/dev/null
    git_automation -C "$target" lfs pull
  fi
  if [[ -f "$target/.gitmodules" ]]; then
    git_automation -C "$target" submodule update --init --recursive --depth 1
  fi
}

for index in "${!REPO_DIRS[@]}"; do
  sync_repo "${REPO_DIRS[$index]}" "${REPO_NAMES[$index]}" "${LOCKED_COMMITS[$index]}"
done
CHECKOUT_VERIFY_ARGS=(
  verify-checkouts
  --lock "$RELEASE_LOCK_PATH"
  --repo-root "$REPOSITORY_ROOT"
  --base "$BASE_PATH"
)
if [[ "$SOURCE_MODE" == "moving_ref" ]]; then
  CHECKOUT_VERIFY_ARGS+=(--moving)
fi
python3 "$SCRIPT_ROOT/verify_linux_source_lock.py" "${CHECKOUT_VERIFY_ARGS[@]}"

step "Checking the cloned compatibility tree"
REQUIRED_FILES=(
  "$BASE_PATH/chummer6-ui/Chummer.Avalonia/Chummer.Avalonia.csproj"
  "$BASE_PATH/chummer6-ui/scripts/ai/with-package-plane.sh"
  "$BASE_PATH/chummer6-ui/scripts/ai/restore.sh"
  "$BASE_PATH/chummer6-ui/global.json"
  "$BASE_PATH/chummer-core-engine/Chummer.Contracts/Chummer.Contracts.csproj"
  "$BASE_PATH/chummer-core-engine/Chummer.Application/Chummer.Application.csproj"
  "$BASE_PATH/chummer-core-engine/Chummer.Infrastructure/Chummer.Infrastructure.csproj"
  "$BASE_PATH/chummer-core-engine/Chummer.Rulesets.Hosting/Chummer.Rulesets.Hosting.csproj"
  "$BASE_PATH/chummer-core-engine/Chummer.Rulesets.Sr4/Chummer.Rulesets.Sr4.csproj"
  "$BASE_PATH/chummer-core-engine/Chummer.Rulesets.Sr5/Chummer.Rulesets.Sr5.csproj"
  "$BASE_PATH/chummer-core-engine/Chummer.Rulesets.Sr6/Chummer.Rulesets.Sr6.csproj"
  "$BASE_PATH/chummer.run-services/Chummer.Campaign.Contracts/Chummer.Campaign.Contracts.csproj"
  "$BASE_PATH/chummer.run-services/Chummer.Play.Contracts/Chummer.Play.Contracts.csproj"
  "$BASE_PATH/chummer.run-services/Chummer.Run.Contracts/Chummer.Run.Contracts.csproj"
  "$BASE_PATH/chummer-hub-registry/Chummer.Hub.Registry.Contracts/Chummer.Hub.Registry.Contracts.csproj"
  "$BASE_PATH/chummer-ui-kit/src/Chummer.Ui.Kit/Chummer.Ui.Kit.csproj"
)
for required_file in "${REQUIRED_FILES[@]}"; do
  [[ -f "$required_file" ]] || die "Required project file is missing: $required_file"
done
log "All required owner projects are present."

step "Installing the repository-pinned .NET SDK locally"
DOTNET_DIR="$BASE_PATH/.tools/dotnet"
DOTNET_INSTALL="$BASE_PATH/.tools/dotnet-install.sh"
mkdir -p "$BASE_PATH/.tools"

if [[ ! -x "$DOTNET_DIR/dotnet" ]] || ! "$DOTNET_DIR/dotnet" --list-sdks 2>/dev/null | awk '{print $1}' | grep -Fxq "$SDK_VERSION"; then
  log "Installing .NET SDK $SDK_VERSION locally into $DOTNET_DIR"
  curl --fail --location --retry 5 --retry-delay 2 --proto '=https' --tlsv1.2 \
    "$DOTNET_INSTALL_URL" -o "$DOTNET_INSTALL"
  python3 "$SCRIPT_ROOT/verify_linux_source_lock.py" verify-file \
    --path "$DOTNET_INSTALL" \
    --sha256 "$DOTNET_INSTALL_SHA256" \
    --label "dotnet-install.sh"
  bash -n "$DOTNET_INSTALL"
  bash "$DOTNET_INSTALL" --version "$SDK_VERSION" --install-dir "$DOTNET_DIR" --no-path
else
  log ".NET SDK $SDK_VERSION is already installed in the workspace."
fi

export DOTNET_ROOT="$DOTNET_DIR"
export PATH="$DOTNET_DIR:$PATH"
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export DOTNET_NOLOGO=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export AVALONIA_TELEMETRY_OPTOUT=1
clear_ambient_restore_overrides
export WRITABLE_STATE_ROOT="$BASE_PATH/.state"
export DOTNET_CLI_HOME="$BASE_PATH/.state/dotnet-cli"
export XDG_CACHE_HOME="$BASE_PATH/.cache/xdg"
export XDG_DATA_HOME="$BASE_PATH/.local/share"
export TMPDIR="$BASE_PATH/.tmp/runtime"
NUGET_LOCK_ROOT="$BASE_PATH/.tmp/nuget-locked-$SOURCE_LOCK_SHA256-$RID"
if [[ -L "$BASE_PATH/.tmp" ]]; then
  die "Refusing a symlinked build temporary root: $BASE_PATH/.tmp"
fi
mkdir -p "$BASE_PATH/.tmp"
if [[ -e "$NUGET_LOCK_ROOT" || -L "$NUGET_LOCK_ROOT" ]]; then
  die "Refusing to reuse a pre-existing locked NuGet workspace: $NUGET_LOCK_ROOT"
fi
umask 077
if ! mkdir "$NUGET_LOCK_ROOT"; then
  die "Could not atomically create the locked NuGet workspace: $NUGET_LOCK_ROOT"
fi
export NUGET_PACKAGES="$NUGET_LOCK_ROOT/packages"
export NUGET_HTTP_CACHE_PATH="$NUGET_LOCK_ROOT/http-cache"
export NUGET_PLUGINS_CACHE_PATH="$NUGET_LOCK_ROOT/plugins-cache"
export NUGET_SCRATCH="$NUGET_LOCK_ROOT/scratch"
NUGET_CONFIG="$NUGET_LOCK_ROOT/NuGet.Config"
NUGET_PACKAGE_LOCK_COPY="$NUGET_LOCK_ROOT/packages.lock.json"
export RestoreConfigFile="$NUGET_CONFIG"
export RestoreSources="${NUGET_SERVICE_INDEX_URLS[0]}"
export RestoreAdditionalProjectSources=""
export RestoreFallbackFolders=""
export RestorePackagesPath="$NUGET_PACKAGES"
export CHUMMER_PACKAGE_PLANE_LOCK_ROOT="$NUGET_LOCK_ROOT/package-plane"
export CHUMMER_PACKAGE_PLANE_LOCK_FILE="$CHUMMER_PACKAGE_PLANE_LOCK_ROOT/with-package-plane.lock"
export CHUMMER_PACKAGE_PLANE_SERIALIZE=1
export CHUMMER_BOOTSTRAP_ENGINE_CONTRACTS_FEED=0
export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"
export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"
mkdir -p \
  "$DOTNET_CLI_HOME" \
  "$NUGET_PACKAGES" \
  "$NUGET_HTTP_CACHE_PATH" \
  "$NUGET_PLUGINS_CACHE_PATH" \
  "$NUGET_SCRATCH" \
  "$XDG_CACHE_HOME" \
  "$XDG_DATA_HOME" \
  "$TMPDIR" \
  "$CHUMMER_PACKAGE_PLANE_LOCK_ROOT"
python3 "$SCRIPT_ROOT/verify_linux_source_lock.py" write-nuget-config \
  --lock "$RELEASE_LOCK_PATH" \
  --repo-root "$REPOSITORY_ROOT" \
  --rid "$RID" \
  --packages-root "$NUGET_PACKAGES" \
  --output "$NUGET_CONFIG"
cp -- "$NUGET_PACKAGE_LOCK_SOURCE" "$NUGET_PACKAGE_LOCK_COPY"
python3 "$SCRIPT_ROOT/verify_linux_source_lock.py" verify-file \
  --path "$NUGET_PACKAGE_LOCK_COPY" \
  --sha256 "$NUGET_PACKAGE_LOCK_SHA256" \
  --label "Avalonia $RID packages.lock.json"
check_local_dotnet_runtime

for index in "${!NUGET_SERVICE_INDEX_URLS[@]}"; do
  NUGET_INDEX_PROBE="$BASE_PATH/.tools/nuget-service-index-$index.json"
  curl --fail --location --retry 5 --retry-delay 2 --proto '=https' --tlsv1.2 \
    "${NUGET_SERVICE_INDEX_URLS[$index]}" -o "$NUGET_INDEX_PROBE"
  python3 "$SCRIPT_ROOT/verify_linux_source_lock.py" verify-file \
    --path "$NUGET_INDEX_PROBE" \
    --sha256 "${NUGET_SERVICE_INDEX_SHA256S[$index]}" \
    --label "NuGet service index ${NUGET_SERVICE_INDEX_URLS[$index]}"
  rm -f "$NUGET_INDEX_PROBE"
done

step "Recording source revisions"
MANIFEST_DIR="$BASE_PATH/artifacts"
mkdir -p "$MANIFEST_DIR"
SOURCE_MANIFEST="$MANIFEST_DIR/source-revisions-$RUN_ID.txt"
{
  printf 'Chummer6 Linux desktop source build\n'
  printf 'Generated UTC: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'Script version: %s\n' "$SCRIPT_VERSION"
  printf 'Distribution: %s\n' "$DISTRO_PRETTY"
  printf 'CPU: %s\n' "$CPU_MODEL"
  printf 'Architecture: %s\n' "$CPU_ARCH"
  printf 'RID: %s\n' "$RID"
  printf '.NET SDK: %s\n' "$SDK_VERSION"
  printf 'Source mode: %s\n' "$SOURCE_MODE"
  printf 'Source lock SHA256: %s\n' "$SOURCE_LOCK_SHA256"
  printf 'NuGet package resolution: locked-mode contentHash graph\n'
  printf 'NuGet package lock: %s\n' "$NUGET_PACKAGE_LOCK_RELATIVE"
  printf 'NuGet package lock SHA256: %s\n' "$NUGET_PACKAGE_LOCK_SHA256"
  printf 'NuGet config SHA256: %s\n' "$(sha256sum "$NUGET_CONFIG" | awk '{print $1}')"
  printf 'NuGet source: %s=%s\n' "${NUGET_SERVICE_INDEX_KEYS[0]}" "${NUGET_SERVICE_INDEX_URLS[0]}"
  printf 'Release manifest status: %s\n' "$RELEASE_MANIFEST_STATUS"
  printf 'Release manifest SHA256: %s\n' "$RELEASE_MANIFEST_SHA256"
  printf 'Release evidence eligible: %s\n' "$RELEASE_EVIDENCE_ELIGIBLE"
  if [[ "$SOURCE_MODE" == "moving_ref" ]]; then
    printf 'Moving Git ref: %s\n' "$GIT_REF"
    printf 'Release evidence warning: NOT RELEASE EVIDENCE; source revisions came from an explicitly allowed moving ref.\n'
  fi
  printf '\n'
  for index in "${!REPO_DIRS[@]}"; do
    printf '%-24s %s\n' "${REPO_NAMES[$index]}" "$(git -C "$BASE_PATH/${REPO_DIRS[$index]}" rev-parse HEAD)"
  done
} | tee "$SOURCE_MANIFEST"

step "Restoring NuGet packages and local compatibility contracts"
UI_ROOT="$BASE_PATH/chummer6-ui"
PROJECT="$UI_ROOT/Chummer.Avalonia/Chummer.Avalonia.csproj"
cd "$UI_ROOT"
bash scripts/ai/restore.sh "$PROJECT" \
  -r "$RID" \
  --configfile "$NUGET_CONFIG" \
  -p:TargetFramework=net10.0 \
  -p:ChummerUseLocalCompatibilityTree=true \
  -p:RestoreConfigFile="$NUGET_CONFIG" \
  -p:RestoreSources="${NUGET_SERVICE_INDEX_URLS[0]}" \
  -p:RestoreAdditionalProjectSources= \
  -p:RestoreFallbackFolders= \
  -p:RestorePackagesPath="$NUGET_PACKAGES"

dotnet restore "$PROJECT" \
  -r "$RID" \
  --no-dependencies \
  --locked-mode \
  --lock-file-path "$NUGET_PACKAGE_LOCK_COPY" \
  --configfile "$NUGET_CONFIG" \
  -p:TargetFramework=net10.0 \
  -p:ChummerUseLocalCompatibilityTree=true \
  -p:RestoreConfigFile="$NUGET_CONFIG" \
  -p:RestoreSources="${NUGET_SERVICE_INDEX_URLS[0]}" \
  -p:RestoreAdditionalProjectSources= \
  -p:RestoreFallbackFolders= \
  -p:RestorePackagesPath="$NUGET_PACKAGES"

python3 "$SCRIPT_ROOT/verify_linux_source_lock.py" verify-nuget-cache \
  --lock "$RELEASE_LOCK_PATH" \
  --repo-root "$REPOSITORY_ROOT" \
  --rid "$RID" \
  --packages-root "$NUGET_PACKAGES"

step "Publishing the self-contained desktop client for this host"
PUBLISH_DIR="$BASE_PATH/artifacts/chummer6-$RID"
rm -rf "$PUBLISH_DIR"
mkdir -p "$PUBLISH_DIR"
UI_SHA="$(git -C "$UI_ROOT" rev-parse --short=12 HEAD)"
SOURCE_VERSION="source-$UI_SHA-$RUN_ID"

dotnet publish "$PROJECT" \
  -c Release \
  -r "$RID" \
  --no-restore \
  --self-contained true \
  --verbosity minimal \
  -p:TargetFramework=net10.0 \
  -p:ChummerUseLocalCompatibilityTree=true \
  -p:PublishSingleFile=false \
  -p:PublishTrimmed=false \
  -p:PublishReadyToRun=false \
  -p:DebugType=None \
  -p:DebugSymbols=false \
  -p:ProduceReferenceAssembly=true \
  -p:UseAppHost=true \
  -p:ChummerDesktopReleaseChannel=source-build \
  -p:ChummerDesktopReleaseVersion="$SOURCE_VERSION" \
  -p:RestoreConfigFile="$NUGET_CONFIG" \
  -p:RestoreSources="${NUGET_SERVICE_INDEX_URLS[0]}" \
  -p:RestoreAdditionalProjectSources= \
  -p:RestoreFallbackFolders= \
  -p:RestorePackagesPath="$NUGET_PACKAGES" \
  -o "$PUBLISH_DIR"

python3 "$SCRIPT_ROOT/verify_linux_source_lock.py" verify-nuget-cache \
  --lock "$RELEASE_LOCK_PATH" \
  --repo-root "$REPOSITORY_ROOT" \
  --rid "$RID" \
  --packages-root "$NUGET_PACKAGES"

step "Verifying the published client and native library links"
BINARY="$PUBLISH_DIR/Chummer.Avalonia"
[[ -f "$BINARY" ]] || die "Publish completed but the executable was not created: $BINARY"
chmod +x "$BINARY"
file "$BINARY"
if command -v ldd >/dev/null 2>&1; then
  LDD_OUTPUT="$(ldd "$BINARY" 2>&1 || true)"
  printf '%s\n' "$LDD_OUTPUT"
  if grep -q 'not found' <<<"$LDD_OUTPUT"; then
    die "The client was built, but one or more native runtime libraries are missing. See the ldd output above."
  fi
fi

BINARY_SHA="$(sha256sum "$BINARY" | awk '{print $1}')"
BUILD_MANIFEST="$PUBLISH_DIR/BUILD-MANIFEST.txt"
{
  cat "$SOURCE_MANIFEST"
  printf '\nExecutable: Chummer.Avalonia\n'
  printf 'Executable SHA256: %s\n' "$BINARY_SHA"
  printf 'Output directory: %s\n' "$PUBLISH_DIR"
} > "$BUILD_MANIFEST"

cat > "$PUBLISH_DIR/run-chummer6.sh" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  HERE="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$HERE/$SOURCE"
done
HERE="$(cd -P "$(dirname "$SOURCE")" && pwd)"
export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"
export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"
exec "$HERE/Chummer.Avalonia" "$@"
LAUNCHER
chmod +x "$PUBLISH_DIR/run-chummer6.sh"

step "Creating a portable source-build archive"
TARBALL="$BASE_PATH/artifacts/chummer6-$RID-$RUN_ID.tar.gz"
tar -C "$PUBLISH_DIR" -czf "$TARBALL" .
TARBALL_SHA="$(sha256sum "$TARBALL" | awk '{print $1}')"
printf '%s  %s\n' "$TARBALL_SHA" "$(basename "$TARBALL")" > "$TARBALL.sha256"
cleanup_build_temp

ELAPSED=$((SECONDS - START_SECONDS))
printf '\n%sBuild complete.%s\n' "$GREEN$BOLD" "$RESET"
printf 'Host:        %s · %s · %s\n' "$DISTRO_PRETTY" "$CPU_ARCH" "$CPU_MODEL"
printf 'Executable: %s\n' "$BINARY"
printf 'Launcher:   %s\n' "$PUBLISH_DIR/run-chummer6.sh"
printf 'Executable SHA256: %s\n' "$BINARY_SHA"
printf 'Archive:    %s\n' "$TARBALL"
printf 'Archive SHA256:    %s\n' "$TARBALL_SHA"
printf 'Manifest:   %s\n' "$BUILD_MANIFEST"
printf 'Log:        %s\n' "$LOG_FILE"
printf 'Elapsed:    %dm %ds\n' "$((ELAPSED / 60))" "$((ELAPSED % 60))"
if [[ "$SOURCE_MODE" == "moving_ref" || "$RELEASE_EVIDENCE_ELIGIBLE" != "true" ]]; then
  printf '%s\n' 'Release evidence: INELIGIBLE (moving source or unbound release authority).'
fi
printf '\nNo install was performed. Install it afterwards with:\n'
printf '  %s --archive %q --force\n' "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/install-chummer6-linux-local.sh" "$TARBALL"
