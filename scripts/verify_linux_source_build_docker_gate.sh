#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE="${CHUMMER_LINUX_SOURCE_BUILD_GATE_IMAGE:-debian:bookworm-slim}"
HOST_WORK_ROOT="${CHUMMER_LINUX_SOURCE_BUILD_GATE_WORK_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/chummer6-linux-source-gate.XXXXXX")}"
KEEP_WORK_ROOT="${CHUMMER_KEEP_DOCKER_GATE_WORKDIR:-0}"
TRACKED_RECEIPT_PATH="$REPO_ROOT/.guide-internal/receipts/LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
RECEIPT_PATH="${CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH:-$TRACKED_RECEIPT_PATH}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
CONTAINER_WORK_ROOT="/work"

usage() {
  cat <<'USAGE'
Run the checked-in Chummer6 Linux source-build script inside a fresh slim Docker container.

Usage:
  ./verify_linux_source_build_docker_gate.sh

Environment overrides:
  CHUMMER_LINUX_SOURCE_BUILD_GATE_IMAGE      Docker image to use. Default: debian:bookworm-slim
  CHUMMER_LINUX_SOURCE_BUILD_GATE_WORK_ROOT  Host work directory for logs and build outputs
  CHUMMER_KEEP_DOCKER_GATE_WORKDIR           Keep the host work directory after success or failure
  CHUMMER_LINUX_SOURCE_BUILD_GATE_MIN_FREE_GIB
                                            Disk threshold passed to the inner build script. Default: 0
  CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH
                                            Receipt output path. Default: .guide-internal/receipts/LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json
  CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256
                                            Independent host archive digest. Required when writing
                                            the tracked receipt; container output must match exactly.
  CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION
                                            Exact host Python version. Required with the digest and
                                            when writing the tracked receipt.
  CHUMMER_GITHUB_ORG                         GitHub org for the inner source-build script
  CHUMMER_REPO_BASE_URL                      Mirror base URL for the inner source-build script

The v2 gate always consumes immutable RELEASE.lock.json authority and preserves
releaseEvidenceEligible=false. Moving refs are rejected before Docker starts.
Without independent host proof, only an explicit custom diagnostic receipt path
is accepted; a weaker run cannot replace the tracked current receipt.
USAGE
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

log() {
  printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

assert_build_script_no_privilege_escalation() {
  python3 - "$REPO_ROOT/scripts/build-chummer6-linux.sh" <<'PY'
from __future__ import annotations
import re
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
text = script_path.read_text(encoding="utf-8")
violations: list[str] = []

for index, raw_line in enumerate(text.splitlines(), start=1):
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue
    if re.search(r"(^|[;&|({]\s*)(sudo|pkexec|doas)\b", line):
        violations.append(f"{index}: privilege escalation command: {raw_line}")
    if re.search(r"(^|[;&|({]\s*)(apt-get|apt|dnf|pacman|zypper)\s+(install|update|upgrade|refresh|-S)\b", line):
        violations.append(f"{index}: package-manager mutation command: {raw_line}")

if violations:
    print("The public Linux source-build script must not install packages or ask for elevated privileges.", file=sys.stderr)
    for violation in violations:
        print(violation, file=sys.stderr)
    raise SystemExit(1)
PY
}

cleanup() {
  if [[ "$KEEP_WORK_ROOT" == "1" || "$KEEP_WORK_ROOT" == "true" || "$KEEP_WORK_ROOT" == "yes" ]]; then
    return 0
  fi
  if [[ -d "$HOST_WORK_ROOT" ]]; then
    docker run --rm -v "$HOST_WORK_ROOT:/cleanup" "$IMAGE" bash -lc 'rm -rf /cleanup/* /cleanup/.[!.]* /cleanup/..?* 2>/dev/null || true' >/dev/null 2>&1 || true
    rm -rf "$HOST_WORK_ROOT" || true
  fi
}
trap cleanup EXIT

[[ -f "$REPO_ROOT/scripts/build-chummer6-linux.sh" ]] || die "build script missing: $REPO_ROOT/scripts/build-chummer6-linux.sh"
[[ -f "$REPO_ROOT/scripts/install-chummer6-linux-local.sh" ]] || die "install script missing: $REPO_ROOT/scripts/install-chummer6-linux-local.sh"
[[ -f "$REPO_ROOT/scripts/check-host-chummer6-linux.sh" ]] || die "audit wrapper missing: $REPO_ROOT/scripts/check-host-chummer6-linux.sh"
assert_build_script_no_privilege_escalation

receipt_path_absolute="$(python3 - "$RECEIPT_PATH" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).resolve(strict=False))
PY
)"
tracked_receipt_path_absolute="$(python3 - "$TRACKED_RECEIPT_PATH" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).resolve(strict=False))
PY
)"
expected_archive_sha256="${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256:-}"
expected_archive_python="${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION:-}"
if [[ -n "$expected_archive_sha256" || -n "$expected_archive_python" ]]; then
  [[ "$expected_archive_sha256" =~ ^[0-9a-f]{64}$ ]] || \
    die "Expected independent archive SHA256 must be 64 lowercase hexadecimal characters."
  [[ "$expected_archive_python" =~ ^3\.([0-9]+)\.[0-9]+$ ]] || \
    die "Expected independent archive Python version must satisfy >=3.11,<4."
  ((10#${BASH_REMATCH[1]} >= 11)) || \
    die "Expected independent archive Python version must satisfy >=3.11,<4."
elif [[ "$receipt_path_absolute" == "$tracked_receipt_path_absolute" ]]; then
  die "The tracked Docker-gate receipt requires independent host archive SHA256 and Python version."
fi

GATE_SDK_VERSION=""
GATE_SDK_AUTHORITY_PATH=""
GATE_SDK_AUTHORITY_SHA256=""
GATE_SDK_ARCHIVE_URL=""
GATE_SDK_ARCHIVE_NAME=""
GATE_SDK_ARCHIVE_SHA256=""
GATE_SDK_ARCHIVE_SHA512=""
GATE_SDK_ARCHIVE_SIZE=""
GATE_SDK_ARCHIVE_COUNT=0
while IFS=$'\t' read -r record first second third fourth fifth sixth; do
  case "$record" in
    SDK_VERSION) GATE_SDK_VERSION="$first" ;;
    SDK_AUTHORITY)
      GATE_SDK_AUTHORITY_PATH="$first"
      GATE_SDK_AUTHORITY_SHA256="$second"
      ;;
    SDK_ARCHIVE)
      if [[ "$first" == "linux-x64" ]]; then
        ((GATE_SDK_ARCHIVE_COUNT += 1))
        GATE_SDK_ARCHIVE_URL="$second"
        GATE_SDK_ARCHIVE_NAME="$third"
        GATE_SDK_ARCHIVE_SHA256="$fourth"
        GATE_SDK_ARCHIVE_SHA512="$fifth"
        GATE_SDK_ARCHIVE_SIZE="$sixth"
      fi
      ;;
  esac
done < <(
  python3 "$REPO_ROOT/scripts/verify_linux_source_lock.py" inspect \
    --lock "$REPO_ROOT/RELEASE.lock.json" --repo-root "$REPO_ROOT"
)
[[ "$GATE_SDK_ARCHIVE_COUNT" == "1" ]] || die "Source lock must resolve one linux-x64 gate SDK archive."
[[ "$GATE_SDK_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "Gate SDK version is malformed."
[[ "$GATE_SDK_AUTHORITY_PATH" == release-locks/* && "$GATE_SDK_AUTHORITY_PATH" != *..* ]] || \
  die "Gate SDK authority path is not canonical."
[[ "$GATE_SDK_AUTHORITY_SHA256" =~ ^[0-9a-f]{64}$ ]] || die "Gate SDK authority digest is malformed."
[[ "$GATE_SDK_ARCHIVE_URL" == https://builds.dotnet.microsoft.com/* ]] || die "Gate SDK archive URL is not approved HTTPS."
[[ "$GATE_SDK_ARCHIVE_NAME" =~ ^[A-Za-z0-9._-]+$ ]] || die "Gate SDK archive name is malformed."
[[ "$GATE_SDK_ARCHIVE_SHA256" =~ ^[0-9a-f]{64}$ ]] || die "Gate SDK archive SHA256 is malformed."
[[ "$GATE_SDK_ARCHIVE_SHA512" =~ ^[0-9a-f]{128}$ ]] || die "Gate SDK archive SHA512 is malformed."
[[ "$GATE_SDK_ARCHIVE_SIZE" =~ ^[1-9][0-9]*$ ]] || die "Gate SDK archive size is malformed."

mkdir -p "$HOST_WORK_ROOT"
HOST_WORK_ROOT="$(cd "$HOST_WORK_ROOT" && pwd -P)"

log "Docker image: $IMAGE"
log "Host work root: $HOST_WORK_ROOT"

write_receipt() {
  local execution_mode="${1:?receipt execution mode is required}"
  local artifacts_root="$HOST_WORK_ROOT/base/artifacts"
  local repro_artifacts_root="$HOST_WORK_ROOT/repro-base/artifacts"
  local publish_dir=""
  local repro_publish_dir=""
  local archive_path=""
  local repro_archive_path=""
  local checksum_path=""
  local repro_checksum_path=""
  local manifest_path=""
  local repro_manifest_path=""
  local launcher_path=""
  local binary_path=""
  local build_log_path=""
  local repro_build_log_path=""
  local startup_smoke_receipt_path=""
  local startup_smoke_failure_path=""
  local install_startup_smoke_receipt_path=""
  local install_startup_smoke_failure_path=""
  local updater_special_mode_receipt_path=""
  local updater_special_mode_success_receipt_path=""
  local rid=""
  local executable_sha=""
  local archive_sha=""

  publish_dir="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type d -name 'chummer6-linux-*' | sort | head -n 1)"
  [[ -n "$publish_dir" ]] || die "Could not locate published artifact directory under $artifacts_root"
  repro_publish_dir="$(find "$repro_artifacts_root" -mindepth 1 -maxdepth 1 -type d -name 'chummer6-linux-*' | sort | head -n 1)"
  [[ -n "$repro_publish_dir" ]] || die "Could not locate repeat artifact directory under $repro_artifacts_root"
  archive_path="$(find "$publish_dir" -mindepth 1 -maxdepth 1 -type f -name 'chummer6-linux-*-source-lock.tar.gz' | sort | head -n 1)"
  [[ -n "$archive_path" ]] || die "Could not locate published archive under $publish_dir"
  repro_archive_path="$(find "$repro_publish_dir" -mindepth 1 -maxdepth 1 -type f -name 'chummer6-linux-*-source-lock.tar.gz' | sort | head -n 1)"
  [[ -n "$repro_archive_path" ]] || die "Could not locate repeat archive under $repro_publish_dir"
  checksum_path="$archive_path.sha256"
  repro_checksum_path="$repro_archive_path.sha256"
  manifest_path="$publish_dir/BUILD-MANIFEST.txt"
  repro_manifest_path="$repro_publish_dir/BUILD-MANIFEST.txt"
  launcher_path="$HOST_WORK_ROOT/base/installed/chummer6-source-build/run-chummer6.sh"
  binary_path="$publish_dir/Chummer.Avalonia"
  build_log_path="$(find "$HOST_WORK_ROOT/base/logs" -mindepth 1 -maxdepth 1 -type f -name 'linux-source-build-*.log' | sort | tail -n 1)"
  repro_build_log_path="$(find "$HOST_WORK_ROOT/repro-base/logs" -mindepth 1 -maxdepth 1 -type f -name 'linux-source-build-*.log' | sort | tail -n 1)"
  startup_smoke_receipt_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'startup-smoke-*.receipt.json' | sort | head -n 1)"
  startup_smoke_failure_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'startup-smoke-*.failure.json' | sort | head -n 1)"
  install_startup_smoke_receipt_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'installed-startup-smoke-*.receipt.json' | sort | head -n 1)"
  install_startup_smoke_failure_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'installed-startup-smoke-*.failure.json' | sort | head -n 1)"
  updater_special_mode_receipt_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'updater-special-mode-*.receipt.json' | sort | head -n 1)"
  updater_special_mode_success_receipt_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'updater-dispatch-simulation-*.receipt.json' | sort | head -n 1)"

  [[ -f "$manifest_path" ]] || die "Missing build manifest: $manifest_path"
  [[ -f "$repro_manifest_path" ]] || die "Missing repeat build manifest: $repro_manifest_path"
  [[ -f "$checksum_path" ]] || die "Missing archive checksum: $checksum_path"
  [[ -f "$repro_checksum_path" ]] || die "Missing repeat archive checksum: $repro_checksum_path"
  [[ -x "$launcher_path" ]] || die "Missing installed launcher: $launcher_path"
  [[ -f "$binary_path" ]] || die "Missing published binary: $binary_path"
  [[ -n "$build_log_path" && -f "$build_log_path" ]] || die "Missing build log under $HOST_WORK_ROOT/base/logs"
  [[ -n "$repro_build_log_path" && -f "$repro_build_log_path" ]] || die "Missing repeat build log under $HOST_WORK_ROOT/repro-base/logs"
  [[ -n "$startup_smoke_receipt_path" && -f "$startup_smoke_receipt_path" ]] || die "Missing startup smoke receipt under $artifacts_root"
  [[ -n "$install_startup_smoke_receipt_path" && -f "$install_startup_smoke_receipt_path" ]] || die "Missing installed startup smoke receipt under $artifacts_root"
  [[ -n "$updater_special_mode_receipt_path" && -f "$updater_special_mode_receipt_path" ]] || die "Missing updater special-mode receipt under $artifacts_root"
  [[ -n "$updater_special_mode_success_receipt_path" && -f "$updater_special_mode_success_receipt_path" ]] || die "Missing updater special-mode success receipt under $artifacts_root"
  if [[ -n "$startup_smoke_failure_path" && -f "$startup_smoke_failure_path" ]]; then
    die "Startup smoke failure packet was emitted: $startup_smoke_failure_path"
  fi
  if [[ -n "$install_startup_smoke_failure_path" && -f "$install_startup_smoke_failure_path" ]]; then
    die "Installed startup smoke failure packet was emitted: $install_startup_smoke_failure_path"
  fi

  (cd "$publish_dir" && sha256sum -c "$(basename "$checksum_path")") >/dev/null
  (cd "$repro_publish_dir" && sha256sum -c "$(basename "$repro_checksum_path")") >/dev/null
  cmp -s "$archive_path" "$repro_archive_path" || \
    die "Two clean source builds produced different normalized archive bytes."
  cmp -s "$manifest_path" "$repro_manifest_path" || \
    die "Two clean source builds produced different BUILD-MANIFEST bytes."
  tar -tzf "$archive_path" ./BUILD-MANIFEST.txt >/dev/null
  tar -tzf "$archive_path" ./Chummer.Avalonia >/dev/null
  cmp -s "$manifest_path" <(tar -xOzf "$archive_path" ./BUILD-MANIFEST.txt) || \
    die "Archived BUILD-MANIFEST differs from the published manifest."
  cmp -s "$binary_path" <(tar -xOzf "$archive_path" ./Chummer.Avalonia) || \
    die "Archived Chummer.Avalonia differs from the published binary."

  rid="$(basename "$publish_dir" | sed 's/^chummer6-//')"
  executable_sha="$(sha256sum "$binary_path" | awk '{print $1}')"
  archive_sha="$(sha256sum "$archive_path" | awk '{print $1}')"
  if [[ -n "${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256:-}" ]]; then
    [[ "${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256}" =~ ^[0-9a-f]{64}$ ]] || \
      die "Expected independent archive SHA256 must be 64 lowercase hexadecimal characters."
    [[ "${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION:-}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || \
      die "Expected independent archive Python version must accompany the digest."
    [[ "$archive_sha" == "${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256}" ]] || \
      die "Clean-container archive differs from the independent host archive digest."
  elif [[ -n "${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION:-}" ]]; then
    die "Expected independent archive Python version requires its archive digest."
  fi

  mkdir -p "$(dirname "$RECEIPT_PATH")"
  python3 - "$RECEIPT_PATH" "$RUN_ID" "$IMAGE" "${CHUMMER_GIT_REF:-locked:RELEASE.lock.json}" "${CHUMMER_GITHUB_ORG:-ArchonMegalon}" "${CHUMMER_REPO_BASE_URL:-}" "$rid" "$executable_sha" "$archive_sha" "$manifest_path" "$build_log_path" "$binary_path" "$archive_path" "$checksum_path" "$repro_manifest_path" "$repro_build_log_path" "$repro_archive_path" "$repro_checksum_path" "$launcher_path" "$startup_smoke_receipt_path" "$install_startup_smoke_receipt_path" "$updater_special_mode_receipt_path" "$updater_special_mode_success_receipt_path" "${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256:-}" "${CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION:-}" "$execution_mode" "$GATE_SDK_VERSION" "$GATE_SDK_AUTHORITY_PATH" "$GATE_SDK_AUTHORITY_SHA256" "$GATE_SDK_ARCHIVE_URL" "$GATE_SDK_ARCHIVE_NAME" "$GATE_SDK_ARCHIVE_SHA256" "$GATE_SDK_ARCHIVE_SHA512" "$GATE_SDK_ARCHIVE_SIZE" "$REPO_ROOT" <<'PY'
from __future__ import annotations
import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path

receipt_path = Path(sys.argv[1])
run_id = sys.argv[2]
image = sys.argv[3]
source_selector = sys.argv[4]
github_org = sys.argv[5]
repo_base_url = sys.argv[6]
rid = sys.argv[7]
executable_sha = sys.argv[8]
archive_sha = sys.argv[9]
manifest_path = Path(sys.argv[10])
build_log_path = Path(sys.argv[11])
binary_path = Path(sys.argv[12])
archive_path = Path(sys.argv[13])
checksum_path = Path(sys.argv[14])
repro_manifest_path = Path(sys.argv[15])
repro_build_log_path = Path(sys.argv[16])
repro_archive_path = Path(sys.argv[17])
repro_checksum_path = Path(sys.argv[18])
launcher_path = Path(sys.argv[19])
startup_smoke_receipt_path = Path(sys.argv[20])
install_startup_smoke_receipt_path = Path(sys.argv[21])
updater_special_mode_receipt_path = Path(sys.argv[22])
updater_special_mode_success_receipt_path = Path(sys.argv[23])
expected_independent_archive_sha = sys.argv[24]
expected_independent_python_version = sys.argv[25]
execution_mode = sys.argv[26]
gate_sdk_version = sys.argv[27]
gate_sdk_authority_path = sys.argv[28]
gate_sdk_authority_sha256 = sys.argv[29]
gate_sdk_archive_url = sys.argv[30]
gate_sdk_archive_name = sys.argv[31]
gate_sdk_archive_sha256 = sys.argv[32]
gate_sdk_archive_sha512 = sys.argv[33]
gate_sdk_archive_size = int(sys.argv[34])
repo_root = Path(sys.argv[35]).resolve()
if execution_mode not in {"fresh_container", "synthetic_fixture"}:
    raise SystemExit("unsupported Docker-gate receipt execution mode")

proof_producer_paths = {
    "docker_gate_script": "scripts/verify_linux_source_build_docker_gate.sh",
    "host_audit_wrapper": "scripts/check-host-chummer6-linux.sh",
    "build_script": "scripts/build-chummer6-linux.sh",
    "package_composer": "scripts/materialize_linux_package_plane.py",
    "install_script": "scripts/install-chummer6-linux-local.sh",
    "identity_validator": "scripts/validate_linux_source_build_gate_identity.sh",
    "source_lock_verifier": "scripts/verify_linux_source_lock.py",
}
proof_producers = {}
for name, relative in proof_producer_paths.items():
    candidate = repo_root / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise SystemExit(f"proof producer is missing or unsafe: {relative}")
    try:
        candidate.resolve().relative_to(repo_root)
    except ValueError as exc:
        raise SystemExit(f"proof producer escapes repository root: {relative}") from exc
    proof_producers[name] = {
        "path": relative,
        "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    }
source_lock = json.loads((repo_root / "RELEASE.lock.json").read_text(encoding="utf-8"))
if proof_producers["source_lock_verifier"] != source_lock.get("sourceLockVerifier"):
    raise SystemExit("source-lock verifier bytes differ from RELEASE.lock.json")
if proof_producers["build_script"] != source_lock.get("buildScript"):
    raise SystemExit("source-build script bytes differ from RELEASE.lock.json")
composer = source_lock.get("packagePlane", {}).get("composer", {})
if proof_producers["package_composer"] != {
    "path": composer.get("path"),
    "sha256": composer.get("sha256"),
}:
    raise SystemExit("package-composer bytes differ from RELEASE.lock.json")

manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
repro_manifest_lines = repro_manifest_path.read_text(encoding="utf-8").splitlines()
startup_smoke_receipt = json.loads(startup_smoke_receipt_path.read_text(encoding="utf-8-sig"))
install_startup_smoke_receipt = json.loads(install_startup_smoke_receipt_path.read_text(encoding="utf-8-sig"))
updater_special_mode_receipt = json.loads(updater_special_mode_receipt_path.read_text(encoding="utf-8-sig"))
updater_special_mode_success_receipt = json.loads(updater_special_mode_success_receipt_path.read_text(encoding="utf-8-sig"))
source_heads = {}
manifest_fields = {}
for line in manifest_lines:
    if "=" not in line:
        raise SystemExit(f"non-canonical BUILD-MANIFEST row: {line!r}")
    key, value = line.split("=", 1)
    if not key or key in manifest_fields:
        raise SystemExit(f"duplicate or empty BUILD-MANIFEST key: {key!r}")
    manifest_fields[key] = value
    if key.startswith("repository."):
        source_heads[key.removeprefix("repository.")] = value

required_fields = {
    "contract",
    "scriptVersion",
    "sourceLockSha256",
    "sdkVersion",
    "pythonRequirement",
    "pythonRole",
    "targetRid",
    "releaseManifestStatus",
    "releaseManifestSha256",
    "releaseEvidenceEligible",
    "debugSymbols",
    "artifactPathPortability",
    "artifactModeNormalization",
}
if not required_fields.issubset(manifest_fields):
    raise SystemExit("BUILD-MANIFEST is missing v2 authority fields")
expected_manifest_fields = required_fields | {
    "repository.chummer-core-engine",
    "repository.chummer.run-services",
    "repository.chummer-hub-registry",
    "repository.chummer-ui-kit",
    "repository.chummer6-ui",
}
if set(manifest_fields) != expected_manifest_fields:
    raise SystemExit("BUILD-MANIFEST property set differs from canonical v2 authority")
if (
    manifest_fields["contract"] != "chummer6.linux-source-build/v2"
    or manifest_fields["targetRid"] != rid
    or manifest_fields["pythonRequirement"] != ">=3.11,<4"
    or manifest_fields["pythonRole"] != "authenticated-orchestrator"
    or manifest_fields["releaseManifestStatus"] != "unbound_review_placeholder"
    or manifest_fields["releaseEvidenceEligible"] != "false"
    or manifest_fields["debugSymbols"] != "none"
    or manifest_fields["artifactPathPortability"] != "passed"
    or manifest_fields["artifactModeNormalization"] != "passed"
    or not re.fullmatch(r"[0-9a-f]{64}", manifest_fields["sourceLockSha256"])
    or not re.fullmatch(r"[0-9a-f]{64}", manifest_fields["releaseManifestSha256"])
):
    raise SystemExit("BUILD-MANIFEST v2 authority or review-only posture differs")
expected_repositories = {
    "chummer-core-engine",
    "chummer.run-services",
    "chummer-hub-registry",
    "chummer-ui-kit",
    "chummer6-ui",
}
if set(source_heads) != expected_repositories or any(
    not re.fullmatch(r"[0-9a-f]{40}", revision)
    for revision in source_heads.values()
):
    raise SystemExit("BUILD-MANIFEST repository authority set differs")
if not source_selector.startswith("locked:"):
    raise SystemExit("v2 fresh-container receipt requires immutable locked source")
if manifest_lines != repro_manifest_lines:
    raise SystemExit("repeat BUILD-MANIFEST differs from the first clean build")
if (
    gate_sdk_version != manifest_fields["sdkVersion"]
    or not re.fullmatch(r"release-locks/[A-Za-z0-9._/-]+", gate_sdk_authority_path)
    or ".." in Path(gate_sdk_authority_path).parts
    or not re.fullmatch(r"[0-9a-f]{64}", gate_sdk_authority_sha256)
    or not gate_sdk_archive_url.startswith("https://builds.dotnet.microsoft.com/")
    or not re.fullmatch(r"[A-Za-z0-9._-]+", gate_sdk_archive_name)
    or not re.fullmatch(r"[0-9a-f]{64}", gate_sdk_archive_sha256)
    or not re.fullmatch(r"[0-9a-f]{128}", gate_sdk_archive_sha512)
    or gate_sdk_archive_size <= 0
):
    raise SystemExit("gate runtime SDK authority is malformed or differs from the build")

archive_bytes = archive_path.read_bytes()
repro_archive_bytes = repro_archive_path.read_bytes()
if archive_bytes != repro_archive_bytes:
    raise SystemExit("two clean source-build archives are not byte-identical")
if hashlib.sha256(archive_bytes).hexdigest() != archive_sha:
    raise SystemExit("source archive digest changed while materializing the receipt")
if expected_independent_archive_sha and expected_independent_archive_sha != archive_sha:
    raise SystemExit("clean-container archive differs from independent host digest")

def observed_python_version(log_path: Path) -> str:
    matches = re.findall(
        r"^\[[0-9:]+\] Python runtime: ([0-9]+\.[0-9]+\.[0-9]+) "
        r"\(requirement >=3\.11,<4\)$",
        log_path.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if len(matches) != 1:
        raise SystemExit(f"build log does not contain one canonical Python observation: {log_path.name}")
    return matches[0]

python_version = observed_python_version(build_log_path)
repro_python_version = observed_python_version(repro_build_log_path)
cross_runtime_observed = bool(
    expected_independent_archive_sha
    and expected_independent_python_version not in {python_version, repro_python_version}
)

def require_runtime(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)

def require_portable_runtime(value: object, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            require_portable_runtime(item, f"{label}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            require_portable_runtime(item, f"{label}[{index}]")
        return
    if not isinstance(value, str):
        return
    forbidden_markers = (
        "/tmp/",
        "/var/tmp/",
        "/docker/",
        "/workspace/",
        "/work/",
        "/repo/",
        "/root/",
    )
    if any(marker in value for marker in forbidden_markers):
        raise SystemExit(f"{label} contains a machine-local path marker")
    if re.search(r"(?i)(?:^|[^a-z0-9])(?:[a-z]:[\\/])", value):
        raise SystemExit(f"{label} contains a Windows absolute path")
    if re.search(r"\\\\[^\\/\s]+[\\/][^\\/\s]+", value):
        raise SystemExit(f"{label} contains a Windows UNC path")
    if re.search(r"(?:^|[\s\"'=])/(?:home|Users)/[^/\s]+(?:/|$)", value):
        raise SystemExit(f"{label} contains a user-home path")

for runtime_label, runtime_payload in (
    ("startup receipt", startup_smoke_receipt),
    ("installed startup receipt", install_startup_smoke_receipt),
    ("missing-installer updater receipt", updater_special_mode_receipt),
    ("updater dispatch simulation receipt", updater_special_mode_success_receipt),
):
    require_portable_runtime(runtime_payload, runtime_label)

for label, payload, checkpoint in (
    ("startup", startup_smoke_receipt, "fresh_container_gate"),
    ("installed startup", install_startup_smoke_receipt, "fresh_container_installed_gate"),
):
    require_runtime(
        payload.get("status") == "pass"
        and payload.get("headId") == "avalonia"
        and payload.get("channelId") == "local"
        and payload.get("rid") == rid
        and payload.get("readyCheckpoint") == checkpoint
        and payload.get("artifactDigest") == f"sha256:{executable_sha}"
        and payload.get("artifactDigestSource") == "process_path"
        and bool(str(payload.get("recordedAtUtc") or "").strip()),
        f"{label} smoke runtime receipt differs from the passing v2 contract",
    )

updater_pkexec_invocation = updater_special_mode_success_receipt.get("pkexecInvocation")
updater_dpkg_invocation = updater_special_mode_success_receipt.get("dpkgInvocation")
retained_stage_inventory = updater_special_mode_success_receipt.get("retainedStageInventory")
retained_inventory_by_role = {
    item.get("role"): item
    for item in retained_stage_inventory
    if isinstance(item, dict)
} if isinstance(retained_stage_inventory, list) else {}
retained_stage_inventory_sha256 = (
    hashlib.sha256(
        json.dumps(
            retained_stage_inventory,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if isinstance(retained_stage_inventory, list)
    else ""
)
retained_inventory_valid = (
    isinstance(retained_stage_inventory, list)
    and len(retained_stage_inventory) == 2
    and set(retained_inventory_by_role) == {"installer_payload", "installer_request"}
    and retained_inventory_by_role["installer_payload"].get("fileName")
        == "chummer-avalonia-linux-x64-installer.deb"
    and retained_inventory_by_role["installer_payload"].get("sizeBytes") == 0
    and retained_inventory_by_role["installer_payload"].get("sha256")
        == hashlib.sha256(b"").hexdigest()
    and retained_inventory_by_role["installer_request"].get("fileName")
        == "installer-request.json"
    and isinstance(retained_inventory_by_role["installer_request"].get("sizeBytes"), int)
    and retained_inventory_by_role["installer_request"].get("sizeBytes") > 0
    and bool(re.fullmatch(
        r"[0-9a-f]{64}",
        str(retained_inventory_by_role["installer_request"].get("sha256") or ""),
    ))
)
require_runtime(
    set(updater_special_mode_receipt) == {
        "status",
        "mode",
        "headId",
        "channelId",
        "rid",
        "exitCode",
        "expectedExitCode",
        "failureReason",
        "lastError",
        "lastErrorSanitized",
        "pendingUpdateVersion",
        "pendingUpdateChannelId",
        "recordedAtUtc",
    }
    and updater_special_mode_receipt.get("status") == "pass"
    and updater_special_mode_receipt.get("mode") == "desktop_update_launch_installer"
    and updater_special_mode_receipt.get("headId") == "avalonia"
    and updater_special_mode_receipt.get("channelId") == "stable"
    and updater_special_mode_receipt.get("rid") == rid
    and updater_special_mode_receipt.get("exitCode") == 1
    and updater_special_mode_receipt.get("expectedExitCode") == 1
    and updater_special_mode_receipt.get("failureReason") == "installer_launch_failed"
    and updater_special_mode_receipt.get("lastError") == "Installer payload was not found."
    and updater_special_mode_receipt.get("lastErrorSanitized") is True
    and bool(str(updater_special_mode_receipt.get("pendingUpdateVersion") or "").strip())
    and updater_special_mode_receipt.get("pendingUpdateChannelId") == "stable"
    and bool(str(updater_special_mode_receipt.get("recordedAtUtc") or "").strip()),
    "missing-installer updater runtime receipt differs from the passing v2 contract",
)

require_runtime(
    set(updater_special_mode_success_receipt) == {
        "status",
        "mode",
        "headId",
        "channelId",
        "rid",
        "exitCode",
        "expectedExitCode",
        "failureReason",
        "lastError",
        "pendingUpdateVersion",
        "pendingUpdateChannelId",
        "executionModel",
        "privilegeEscalationPerformed",
        "nativePackageManagerExecutionProven",
        "invocationContractProven",
        "pkexecShimInvoked",
        "dpkgShimInvoked",
        "pkexecInvocation",
        "dpkgInvocation",
        "stageRetentionObserved",
        "stagedPayloadCleanupProven",
        "retainedStageInventoryExact",
        "retainedStageInventory",
        "retainedStageInventorySha256",
        "gateStageLocation",
        "deferredCleanupPhase",
        "deferredCleanupPolicy",
        "deferredCleanupExecutionProven",
        "recordedAtUtc",
    }
    and updater_special_mode_success_receipt.get("status") == "pass"
    and updater_special_mode_success_receipt.get("mode") == "desktop_update_dispatch_pending_state_clearing_simulation"
    and updater_special_mode_success_receipt.get("headId") == "avalonia"
    and updater_special_mode_success_receipt.get("channelId") == "stable"
    and updater_special_mode_success_receipt.get("rid") == rid
    and updater_special_mode_success_receipt.get("exitCode") == 0
    and updater_special_mode_success_receipt.get("expectedExitCode") == 0
    and updater_special_mode_success_receipt.get("failureReason") == ""
    and updater_special_mode_success_receipt.get("lastError") == ""
    and updater_special_mode_success_receipt.get("pendingUpdateVersion") == ""
    and updater_special_mode_success_receipt.get("pendingUpdateChannelId") == ""
    and updater_special_mode_success_receipt.get("executionModel") == "simulated_nonprivileged_pkexec_dpkg"
    and updater_special_mode_success_receipt.get("privilegeEscalationPerformed") is False
    and updater_special_mode_success_receipt.get("nativePackageManagerExecutionProven") is False
    and updater_special_mode_success_receipt.get("invocationContractProven") is True
    and updater_special_mode_success_receipt.get("pkexecShimInvoked") is True
    and updater_special_mode_success_receipt.get("dpkgShimInvoked") is True
    and isinstance(updater_pkexec_invocation, dict)
    and isinstance(updater_dpkg_invocation, dict)
    and updater_pkexec_invocation == {
        "argvCount": 3,
        "commandLabel": "dpkg",
        "installFlag": "-i",
        "installerArgumentBinding": "sha256_of_utf8_gate_stage_installer_path",
        "installerArgumentSha256": updater_pkexec_invocation.get("installerArgumentSha256"),
    }
    and updater_dpkg_invocation == {
        "argvCount": 2,
        "installFlag": "-i",
        "installerArgumentBinding": "sha256_of_utf8_gate_stage_installer_path",
        "installerArgumentSha256": updater_pkexec_invocation.get("installerArgumentSha256"),
    }
    and bool(re.fullmatch(
        r"[0-9a-f]{64}",
        str(updater_pkexec_invocation.get("installerArgumentSha256") or ""),
    ))
    and updater_special_mode_success_receipt.get("stageRetentionObserved") is True
    and updater_special_mode_success_receipt.get("stagedPayloadCleanupProven") is False
    and updater_special_mode_success_receipt.get("retainedStageInventoryExact") is True
    and retained_inventory_valid
    and updater_special_mode_success_receipt.get("retainedStageInventorySha256")
        == retained_stage_inventory_sha256
    and updater_special_mode_success_receipt.get("gateStageLocation")
        == "synthetic_gate_stage_outside_normal_ui_temp_root"
    and updater_special_mode_success_receipt.get("deferredCleanupPhase")
        == "outside_dispatch_simulation"
    and updater_special_mode_success_receipt.get("deferredCleanupPolicy")
        == "new_release_startup_or_two_day_stale_temp_pruning"
    and updater_special_mode_success_receipt.get("deferredCleanupExecutionProven") is False
    and bool(str(updater_special_mode_success_receipt.get("recordedAtUtc") or "").strip()),
    "updater dispatch/pending-state-clearing simulation receipt differs from the passing v2 contract",
)

forbidden = (b"/tmp/", b"/var/tmp/", b"/docker/", b"/workspace/", b".source-run.", b"/work/base", b"/work/repro-base")
for candidate in (archive_path, repro_archive_path):
    with tarfile.open(candidate, "r:gz") as archive:
        for member in archive.getmembers():
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise SystemExit(f"unsafe source archive member: {member.name}")
            if member.issym() or member.islnk():
                raise SystemExit(f"source archive link is not portable: {member.name}")
            normalized_name = member.name.removeprefix("./")
            if member.isdir():
                expected_mode = 0o755
            elif member.isfile():
                expected_mode = 0o755 if normalized_name == "Chummer.Avalonia" else 0o644
            else:
                raise SystemExit(f"source archive special member is not portable: {member.name}")
            if member.mode != expected_mode:
                raise SystemExit(
                    f"source archive member has non-canonical mode: {member.name} "
                    f"{member.mode:04o} != {expected_mode:04o}"
                )
            if not member.isfile():
                continue
            stream = archive.extractfile(member)
            payload = stream.read() if stream is not None else b""
            if any(token in payload for token in forbidden):
                raise SystemExit(f"machine-local path bytes remain in source archive member: {member.name}")

projected_retained_stage_inventory = [
    {
        "role": str(item.get("role") or "").strip(),
        "file_name": str(item.get("fileName") or "").strip(),
        "size_bytes": item.get("sizeBytes"),
        "sha256": str(item.get("sha256") or "").strip(),
    }
    for item in retained_stage_inventory
]
projected_retained_stage_inventory_sha256 = hashlib.sha256(
    json.dumps(
        projected_retained_stage_inventory,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()

receipt = {
    "contract_name": "ea.chummer6_linux_source_build_docker_gate.v2",
    "status": "passed" if execution_mode == "fresh_container" else "test_passed",
    "execution_mode": execution_mode,
    "generated_at_utc": run_id,
    "docker_image": image,
    "source_mode": "locked" if source_selector.startswith("locked:") else "moving_ref",
    "source_lock": "RELEASE.lock.json" if source_selector.startswith("locked:") else None,
    "source_lock_sha256": manifest_fields["sourceLockSha256"],
    "git_ref": None if source_selector.startswith("locked:") else source_selector,
    "release_manifest_status": manifest_fields["releaseManifestStatus"],
    "release_manifest_sha256": manifest_fields["releaseManifestSha256"],
    "release_evidence_eligible": False,
    "github_org": github_org,
    "repo_base_url": repo_base_url or f"https://github.com/{github_org}",
    "proof_producers": proof_producers,
    "runtime_authority": {
        "status": "passed",
        "source_lock": "RELEASE.lock.json",
        "rid": "linux-x64",
        "sdk_version": gate_sdk_version,
        "authority_path": gate_sdk_authority_path,
        "authority_sha256": gate_sdk_authority_sha256,
        "archive_url": gate_sdk_archive_url,
        "archive_name": gate_sdk_archive_name,
        "archive_sha256": gate_sdk_archive_sha256,
        "archive_sha512": gate_sdk_archive_sha512,
        "archive_size_bytes": gate_sdk_archive_size,
        "dotnet_root_mode": "gate-owned-authenticated-sdk",
        "dotnet_root_x64_bound": True,
        "dotnet_host_path_bound": True,
        "path_precedence": "gate-owned-sdk-first",
        "multilevel_lookup": False,
        "system_runtime_fallback_allowed": False,
        "archive_reused_by_clean_builds": True,
    },
    "gate": {
        "name": "linux_source_build_fresh_container",
        "host_audit_wrapper": "scripts/check-host-chummer6-linux.sh",
        "build_script": "scripts/build-chummer6-linux.sh",
        "install_script": "scripts/install-chummer6-linux-local.sh",
        "container_flow": "audit_then_two_clean_builds_then_direct_startup_then_local_install_then_updater_dispatch_pending_state_clearing_simulation",
        "public_script_requires_sudo": False,
        "public_script_installs_system_packages": False,
        "build_temp_cleanup_default": True,
        "source_build_update_mode_default": "notify",
        "source_build_analytics_default": "off",
        "source_build_is_explicitly_two_step": True,
    },
    "output": {
        "rid": rid,
        "binary_name": binary_path.name,
        "launcher_name": launcher_path.name,
        "archive_name": archive_path.name,
        "archive_checksum_name": checksum_path.name,
        "executable_sha256": executable_sha,
        "archive_sha256": archive_sha,
        "debug_symbols": manifest_fields["debugSymbols"],
        "artifact_path_portability": manifest_fields["artifactPathPortability"],
        "artifact_mode_normalization": manifest_fields["artifactModeNormalization"],
    },
    "reproducibility": {
        "status": "passed",
        "clean_build_count": 2,
        "python_requirement": manifest_fields["pythonRequirement"],
        "python_role": manifest_fields["pythonRole"],
        "observed_python_versions": [python_version, repro_python_version],
        "archive_sha256_first": archive_sha,
        "archive_sha256_repeat": hashlib.sha256(repro_archive_bytes).hexdigest(),
        "archives_byte_identical": True,
        "archive_payload_path_scan": "passed",
        "archive_member_modes": "passed",
        "independent_host_archive_sha256": expected_independent_archive_sha or None,
        "independent_host_python_version": expected_independent_python_version or None,
        "cross_compatible_runtime_archive_identical": (
            True if cross_runtime_observed else None
        ),
        "scope": (
            "cross-compatible-runtime-observed"
            if cross_runtime_observed
            else (
                "independent-host-same-runtime-observed"
                if expected_independent_archive_sha
                else "same-container-runtime-observed"
            )
        ),
        "release_evidence_eligible": False,
    },
    "artifacts": {
        "build_manifest_excerpt": manifest_lines[:20],
        "source_heads": source_heads,
        "build_log_name": build_log_path.name,
        "repeat_build_log_name": repro_build_log_path.name,
        "archive_checksum_name": checksum_path.name,
        "repeat_archive_checksum_name": repro_checksum_path.name,
        "startup_smoke_receipt_name": startup_smoke_receipt_path.name,
        "installed_startup_smoke_receipt_name": install_startup_smoke_receipt_path.name,
        "updater_special_mode_receipt_name": updater_special_mode_receipt_path.name,
        "updater_dispatch_simulation_receipt_name": updater_special_mode_success_receipt_path.name,
    },
    "runtime": {
        "startup_smoke": {
            "status": str(startup_smoke_receipt.get("status") or "").strip(),
            "head_id": str(startup_smoke_receipt.get("headId") or "").strip(),
            "channel_id": str(startup_smoke_receipt.get("channelId") or "").strip(),
            "rid": str(startup_smoke_receipt.get("rid") or "").strip(),
            "ready_checkpoint": str(startup_smoke_receipt.get("readyCheckpoint") or "").strip(),
            "artifact_digest": str(startup_smoke_receipt.get("artifactDigest") or "").strip(),
            "artifact_digest_source": str(startup_smoke_receipt.get("artifactDigestSource") or "").strip(),
            "recorded_at_utc": str(startup_smoke_receipt.get("recordedAtUtc") or "").strip(),
        },
        "installed_startup_smoke": {
            "status": str(install_startup_smoke_receipt.get("status") or "").strip(),
            "head_id": str(install_startup_smoke_receipt.get("headId") or "").strip(),
            "channel_id": str(install_startup_smoke_receipt.get("channelId") or "").strip(),
            "rid": str(install_startup_smoke_receipt.get("rid") or "").strip(),
            "ready_checkpoint": str(install_startup_smoke_receipt.get("readyCheckpoint") or "").strip(),
            "artifact_digest": str(install_startup_smoke_receipt.get("artifactDigest") or "").strip(),
            "artifact_digest_source": str(install_startup_smoke_receipt.get("artifactDigestSource") or "").strip(),
            "recorded_at_utc": str(install_startup_smoke_receipt.get("recordedAtUtc") or "").strip(),
        },
        "updater_special_mode": {
            "status": str(updater_special_mode_receipt.get("status") or "").strip(),
            "mode": str(updater_special_mode_receipt.get("mode") or "").strip(),
            "head_id": str(updater_special_mode_receipt.get("headId") or "").strip(),
            "channel_id": str(updater_special_mode_receipt.get("channelId") or "").strip(),
            "rid": str(updater_special_mode_receipt.get("rid") or "").strip(),
            "exit_code": updater_special_mode_receipt.get("exitCode"),
            "expected_exit_code": updater_special_mode_receipt.get("expectedExitCode"),
            "failure_reason": str(updater_special_mode_receipt.get("failureReason") or "").strip(),
            "last_error": str(updater_special_mode_receipt.get("lastError") or "").strip(),
            "last_error_sanitized": updater_special_mode_receipt.get("lastErrorSanitized") is True,
            "pending_update_version": str(updater_special_mode_receipt.get("pendingUpdateVersion") or "").strip(),
            "pending_update_channel_id": str(updater_special_mode_receipt.get("pendingUpdateChannelId") or "").strip(),
            "recorded_at_utc": str(updater_special_mode_receipt.get("recordedAtUtc") or "").strip(),
        },
        "updater_dispatch_simulation": {
            "status": str(updater_special_mode_success_receipt.get("status") or "").strip(),
            "mode": str(updater_special_mode_success_receipt.get("mode") or "").strip(),
            "head_id": str(updater_special_mode_success_receipt.get("headId") or "").strip(),
            "channel_id": str(updater_special_mode_success_receipt.get("channelId") or "").strip(),
            "rid": str(updater_special_mode_success_receipt.get("rid") or "").strip(),
            "exit_code": updater_special_mode_success_receipt.get("exitCode"),
            "expected_exit_code": updater_special_mode_success_receipt.get("expectedExitCode"),
            "failure_reason": str(updater_special_mode_success_receipt.get("failureReason") or "").strip(),
            "last_error": str(updater_special_mode_success_receipt.get("lastError") or "").strip(),
            "pending_update_version": str(updater_special_mode_success_receipt.get("pendingUpdateVersion") or "").strip(),
            "pending_update_channel_id": str(updater_special_mode_success_receipt.get("pendingUpdateChannelId") or "").strip(),
            "execution_model": str(updater_special_mode_success_receipt.get("executionModel") or "").strip(),
            "privilege_escalation_performed": updater_special_mode_success_receipt.get("privilegeEscalationPerformed"),
            "native_package_manager_execution_proven": updater_special_mode_success_receipt.get("nativePackageManagerExecutionProven"),
            "invocation_contract_proven": updater_special_mode_success_receipt.get("invocationContractProven"),
            "pkexec_shim_invoked": updater_special_mode_success_receipt.get("pkexecShimInvoked"),
            "dpkg_shim_invoked": updater_special_mode_success_receipt.get("dpkgShimInvoked"),
            "pkexec_invocation": {
                "argv_count": updater_pkexec_invocation.get("argvCount"),
                "command_label": updater_pkexec_invocation.get("commandLabel"),
                "install_flag": updater_pkexec_invocation.get("installFlag"),
                "installer_argument_binding": updater_pkexec_invocation.get("installerArgumentBinding"),
                "installer_argument_sha256": updater_pkexec_invocation.get("installerArgumentSha256"),
            },
            "dpkg_invocation": {
                "argv_count": updater_dpkg_invocation.get("argvCount"),
                "install_flag": updater_dpkg_invocation.get("installFlag"),
                "installer_argument_binding": updater_dpkg_invocation.get("installerArgumentBinding"),
                "installer_argument_sha256": updater_dpkg_invocation.get("installerArgumentSha256"),
            },
            "stage_retention_observed": updater_special_mode_success_receipt.get("stageRetentionObserved"),
            "staged_payload_cleanup_proven": updater_special_mode_success_receipt.get("stagedPayloadCleanupProven"),
            "retained_stage_inventory_exact": updater_special_mode_success_receipt.get("retainedStageInventoryExact"),
            "retained_stage_inventory": projected_retained_stage_inventory,
            "retained_stage_inventory_sha256": projected_retained_stage_inventory_sha256,
            "gate_stage_location": str(updater_special_mode_success_receipt.get("gateStageLocation") or "").strip(),
            "deferred_cleanup_phase": str(updater_special_mode_success_receipt.get("deferredCleanupPhase") or "").strip(),
            "deferred_cleanup_policy": str(updater_special_mode_success_receipt.get("deferredCleanupPolicy") or "").strip(),
            "deferred_cleanup_execution_proven": updater_special_mode_success_receipt.get("deferredCleanupExecutionProven"),
            "recorded_at_utc": str(updater_special_mode_success_receipt.get("recordedAtUtc") or "").strip(),
        },
    },
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

case "${CHUMMER_LINUX_SOURCE_BUILD_GATE_TEST_MODE:-}" in
  receipt)
    write_receipt synthetic_fixture
    exit 0
    ;;
  "") ;;
  *) die "Unsupported CHUMMER_LINUX_SOURCE_BUILD_GATE_TEST_MODE." ;;
esac

command -v docker >/dev/null 2>&1 || die "docker is required for the fresh-container gate."
[[ -z "${CHUMMER_GIT_REF:-}" ]] || \
  die "The v2 fresh-container gate requires immutable RELEASE.lock.json source."

ROOT_SETUP_COMMAND=$(cat <<'EOF'
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  bash ca-certificates coreutils curl dbus file findutils gawk git git-lfs gzip grep python3 sed \
  tar unzip util-linux xz-utils \
  libc6 libgcc-s1 libgssapi-krb5-2 libicu-dev libssl-dev libstdc++6 zlib1g \
  libx11-6 libx11-xcb1 libxcb1 libxkbcommon0 libfontconfig1 libfreetype6 \
  libgl1 libegl1 libglx0 libgbm1 libdrm2 libice6 libsm6 libxext6 libxfixes3 \
  libxi6 libxrandr2 libxcursor1 libxinerama1 libwayland-client0 libwayland-cursor0
(cd / && git lfs install --skip-repo >/dev/null)
repository_uid="$(stat -c %u /repo)"
repository_gid="$(stat -c %g /repo)"
((repository_uid > 0)) || {
  printf 'ERROR: the fresh-container gate refuses to run audited build steps as root.\n' >&2
  exit 1
}
((repository_gid > 0)) || {
  printf 'ERROR: the fresh-container gate refuses a root primary group.\n' >&2
  exit 1
}
mapfile -t repository_group_rows < <(getent group "$repository_gid" || true)
if ((${#repository_group_rows[@]} == 0)); then
  if getent group chummer-gate >/dev/null; then
    printf 'ERROR: chummer-gate already names a different primary group.\n' >&2
    exit 1
  fi
  printf 'chummer-gate:x:%s:\n' "$repository_gid" >>/etc/group
  mapfile -t repository_group_rows < <(getent group "$repository_gid" || true)
fi
((${#repository_group_rows[@]} == 1)) || {
  printf 'ERROR: the checkout GID does not resolve to exactly one group record.\n' >&2
  exit 1
}

mapfile -t repository_passwd_rows < <(getent passwd "$repository_uid" || true)
if ((${#repository_passwd_rows[@]} == 0)); then
  if getent passwd chummer-gate >/dev/null; then
    printf 'ERROR: chummer-gate already names a different unprivileged user.\n' >&2
    exit 1
  fi
  printf 'chummer-gate:x:%s:%s:Chummer source gate:/work/home:/bin/bash\n' \
    "$repository_uid" "$repository_gid" >>/etc/passwd
  mapfile -t repository_passwd_rows < <(getent passwd "$repository_uid" || true)
fi
((${#repository_passwd_rows[@]} == 1)) || {
  printf 'ERROR: the checkout UID does not resolve to exactly one passwd record.\n' >&2
  exit 1
}
identity_args=(--uid "$repository_uid" --gid "$repository_gid")
for repository_group_row in "${repository_group_rows[@]}"; do
  identity_args+=(--group-record "$repository_group_row")
done
for repository_passwd_row in "${repository_passwd_rows[@]}"; do
  identity_args+=(--passwd-record "$repository_passwd_row")
done
repository_user="$(
  bash /repo/scripts/validate_linux_source_build_gate_identity.sh "${identity_args[@]}"
)"
install -d -m 0700 -o "$repository_uid" -g "$repository_gid" /work/home
exec setpriv \
  --reuid="$repository_uid" \
  --regid="$repository_gid" \
  --clear-groups \
  --bounding-set=-all \
  --no-new-privs \
  env HOME=/work/home USER="$repository_user" LOGNAME="$repository_user" bash -lc "$1"
EOF
)

INNER_COMMAND=$(cat <<'EOF'
set -Eeuo pipefail
cd /repo
bash scripts/check-host-chummer6-linux.sh --base /work/base
GATE_SDK_ARCHIVE="/work/gate-runtime-sdk.tar.gz"
GATE_SDK_ROOT="/work/gate-runtime-sdk"
test ! -e "$GATE_SDK_ARCHIVE"
test ! -e "$GATE_SDK_ROOT"
curl --disable --fail --location --retry 5 --retry-delay 2 \
  --proto '=https' --tlsv1.2 --output "$GATE_SDK_ARCHIVE" "$CHUMMER_GATE_SDK_ARCHIVE_URL"
test "$(stat -c %s "$GATE_SDK_ARCHIVE")" = "$CHUMMER_GATE_SDK_ARCHIVE_SIZE"
test "$(sha256sum "$GATE_SDK_ARCHIVE" | awk '{print $1}')" = "$CHUMMER_GATE_SDK_ARCHIVE_SHA256"
python3 scripts/verify_linux_source_lock.py install-sdk \
  --lock RELEASE.lock.json --repo-root /repo --rid linux-x64 \
  --archive "$GATE_SDK_ARCHIVE" --output "$GATE_SDK_ROOT"
test "$($GATE_SDK_ROOT/dotnet --version)" = "$CHUMMER_GATE_SDK_VERSION"
export DOTNET_ROOT="$GATE_SDK_ROOT"
export DOTNET_ROOT_X64="$GATE_SDK_ROOT"
export DOTNET_HOST_PATH="$GATE_SDK_ROOT/dotnet"
export DOTNET_MULTILEVEL_LOOKUP=0
export DOTNET_NOLOGO=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export PATH="$GATE_SDK_ROOT:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
unset DOTNET_ROOT_X86 DOTNET_ROOT_ARM64
CHUMMER_SDK_ARCHIVE="$GATE_SDK_ARCHIVE" bash scripts/build-chummer6-linux.sh --base /work/base
CHUMMER_SDK_ARCHIVE="$GATE_SDK_ARCHIVE" bash scripts/build-chummer6-linux.sh --base /work/repro-base
PUBLISH_DIR="$(find /work/base/artifacts -mindepth 1 -maxdepth 1 -type d -name 'chummer6-linux-*' | sort | head -n 1)"
REPRO_PUBLISH_DIR="$(find /work/repro-base/artifacts -mindepth 1 -maxdepth 1 -type d -name 'chummer6-linux-*' | sort | head -n 1)"
test -n "$PUBLISH_DIR"
test -n "$REPRO_PUBLISH_DIR"
test -x "$PUBLISH_DIR/Chummer.Avalonia"
ARCHIVE_PATH="$(find "$PUBLISH_DIR" -mindepth 1 -maxdepth 1 -type f -name 'chummer6-linux-*-source-lock.tar.gz' | sort | head -n 1)"
REPRO_ARCHIVE_PATH="$(find "$REPRO_PUBLISH_DIR" -mindepth 1 -maxdepth 1 -type f -name 'chummer6-linux-*-source-lock.tar.gz' | sort | head -n 1)"
test -n "$ARCHIVE_PATH"
test -n "$REPRO_ARCHIVE_PATH"
CHECKSUM_PATH="$ARCHIVE_PATH.sha256"
REPRO_CHECKSUM_PATH="$REPRO_ARCHIVE_PATH.sha256"
test -f "$CHECKSUM_PATH"
test -f "$REPRO_CHECKSUM_PATH"
(cd "$PUBLISH_DIR" && sha256sum -c "$(basename "$CHECKSUM_PATH")")
(cd "$REPRO_PUBLISH_DIR" && sha256sum -c "$(basename "$REPRO_CHECKSUM_PATH")")
cmp -s "$ARCHIVE_PATH" "$REPRO_ARCHIVE_PATH"
cmp -s "$PUBLISH_DIR/BUILD-MANIFEST.txt" "$REPRO_PUBLISH_DIR/BUILD-MANIFEST.txt"
tar -tzf "$ARCHIVE_PATH" ./BUILD-MANIFEST.txt >/dev/null
tar -tzf "$ARCHIVE_PATH" ./Chummer.Avalonia >/dev/null
cmp -s "$PUBLISH_DIR/BUILD-MANIFEST.txt" <(tar -xOzf "$ARCHIVE_PATH" ./BUILD-MANIFEST.txt)
cmp -s "$PUBLISH_DIR/Chummer.Avalonia" <(tar -xOzf "$ARCHIVE_PATH" ./Chummer.Avalonia)
STARTUP_SMOKE_RECEIPT="/work/base/artifacts/startup-smoke-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
STARTUP_SMOKE_FAILURE="/work/base/artifacts/startup-smoke-$(date -u +%Y%m%dT%H%M%SZ).failure.json"
CHUMMER_DESKTOP_STARTUP_SMOKE_RECEIPT="$STARTUP_SMOKE_RECEIPT" \
CHUMMER_DESKTOP_STARTUP_SMOKE_FAILURE_PACKET="$STARTUP_SMOKE_FAILURE" \
CHUMMER_DESKTOP_STARTUP_SMOKE_READY_CHECKPOINT="fresh_container_gate" \
CHUMMER_DESKTOP_STARTUP_SMOKE_HOST_CLASS="debian:bookworm-slim" \
CHUMMER_DESKTOP_STARTUP_SMOKE_RID="$(basename "$PUBLISH_DIR" | sed 's/^chummer6-//')" \
"$PUBLISH_DIR/Chummer.Avalonia" --startup-smoke
test -f "$STARTUP_SMOKE_RECEIPT"
test ! -f "$STARTUP_SMOKE_FAILURE"
INSTALL_DEST="/work/base/installed/chummer6-source-build"
INSTALL_LINK="/work/base/bin/chummer6-source-build"
bash scripts/install-chummer6-linux-local.sh --archive "$ARCHIVE_PATH" --destination "$INSTALL_DEST" --command-link "$INSTALL_LINK" --force
test -x "$INSTALL_DEST/run-chummer6.sh"
test -x "$INSTALL_DEST/app/Chummer.Avalonia"
test -L "$INSTALL_LINK"
INSTALLED_STARTUP_SMOKE_RECEIPT="/work/base/artifacts/installed-startup-smoke-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
INSTALLED_STARTUP_SMOKE_FAILURE="/work/base/artifacts/installed-startup-smoke-$(date -u +%Y%m%dT%H%M%SZ).failure.json"
CHUMMER_DESKTOP_STARTUP_SMOKE_RECEIPT="$INSTALLED_STARTUP_SMOKE_RECEIPT" \
CHUMMER_DESKTOP_STARTUP_SMOKE_FAILURE_PACKET="$INSTALLED_STARTUP_SMOKE_FAILURE" \
CHUMMER_DESKTOP_STARTUP_SMOKE_READY_CHECKPOINT="fresh_container_installed_gate" \
CHUMMER_DESKTOP_STARTUP_SMOKE_HOST_CLASS="debian:bookworm-slim" \
CHUMMER_DESKTOP_STARTUP_SMOKE_RID="$(basename "$PUBLISH_DIR" | sed 's/^chummer6-//')" \
"$INSTALL_LINK" --startup-smoke
test -f "$INSTALLED_STARTUP_SMOKE_RECEIPT"
test ! -f "$INSTALLED_STARTUP_SMOKE_FAILURE"
UPDATER_STAGE_ROOT="/work/base/artifacts/updater-special-mode-stage"
UPDATER_STATE_PATH="$UPDATER_STAGE_ROOT/state.json"
UPDATER_REQUEST_PATH="$UPDATER_STAGE_ROOT/installer-request.json"
UPDATER_MISSING_INSTALLER="$UPDATER_STAGE_ROOT/missing-installer.deb"
UPDATER_SPECIAL_MODE_RECEIPT="/work/base/artifacts/updater-special-mode-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
mkdir -p "$UPDATER_STAGE_ROOT"
python3 - "$UPDATER_STATE_PATH" "$UPDATER_REQUEST_PATH" "$UPDATER_STAGE_ROOT" "$UPDATER_MISSING_INSTALLER" "$(basename "$PUBLISH_DIR" | sed 's/^chummer6-//')" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
request_path = Path(sys.argv[2])
stage_root = sys.argv[3]
missing_installer = sys.argv[4]
rid = sys.argv[5]
state = {
    "HeadId": "avalonia",
    "Platform": "linux",
    "Arch": rid.split("-", 1)[1],
    "InstalledVersion": "run-20260618-024810",
    "ChannelId": "stable",
    "LastCheckedAt": "2026-06-18T06:00:00Z",
    "LastManifestVersion": "run-20260618-051119",
    "LastManifestPublishedAt": "2026-06-18T06:15:00Z",
    "LastError": None,
    "PendingUpdateVersion": "run-20260618-051119",
    "PendingUpdateChannelId": "stable",
    "PendingUpdatePreparedAtUtc": "2026-06-18T06:16:00Z",
}
request = {
    "ParentProcessId": 0,
    "StageRoot": stage_root,
    "InstallerPath": missing_installer,
    "StateFilePath": str(state_path),
    "Version": "run-20260618-051119",
    "ChannelId": "stable",
    "HeadId": "avalonia",
    "RelaunchArgs": [],
}
state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
PY
set +e
"$PUBLISH_DIR/Chummer.Avalonia" --desktop-update-launch-installer "$UPDATER_REQUEST_PATH"
UPDATER_EXIT_CODE="$?"
set -e
python3 - "$UPDATER_STATE_PATH" "$UPDATER_SPECIAL_MODE_RECEIPT" "$UPDATER_EXIT_CODE" "$(basename "$PUBLISH_DIR" | sed 's/^chummer6-//')" <<'PY'
from __future__ import annotations
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

state_path = Path(sys.argv[1])
receipt_path = Path(sys.argv[2])
exit_code = int(sys.argv[3])
rid = sys.argv[4]
state = json.loads(state_path.read_text(encoding="utf-8-sig"))
failure_reason = str(state.get("LastFailureReason") or "").strip()
raw_last_error = str(state.get("LastError") or "").strip()
expected_missing_installer_error = raw_last_error.startswith("Installer payload was not found")
receipt = {
    "status": "pass" if (
        exit_code == 1
        and failure_reason == "installer_launch_failed"
        and expected_missing_installer_error
    ) else "fail",
    "mode": "desktop_update_launch_installer",
    "headId": str(state.get("HeadId") or "").strip(),
    "channelId": str(state.get("ChannelId") or "").strip(),
    "rid": rid,
    "exitCode": exit_code,
    "expectedExitCode": 1,
    "failureReason": failure_reason,
    "lastError": "Installer payload was not found.",
    "lastErrorSanitized": True,
    "pendingUpdateVersion": str(state.get("PendingUpdateVersion") or "").strip(),
    "pendingUpdateChannelId": str(state.get("PendingUpdateChannelId") or "").strip(),
    "recordedAtUtc": datetime.now(UTC).isoformat(),
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
test -f "$UPDATER_SPECIAL_MODE_RECEIPT"
UPDATER_SUCCESS_STAGE_ROOT="/work/base/artifacts/updater-special-mode-success-stage"
UPDATER_SUCCESS_STATE_PATH="/work/base/artifacts/updater-special-mode-success-state.json"
UPDATER_SUCCESS_REQUEST_PATH="$UPDATER_SUCCESS_STAGE_ROOT/installer-request.json"
UPDATER_SUCCESS_INSTALLER="$UPDATER_SUCCESS_STAGE_ROOT/chummer-avalonia-linux-x64-installer.deb"
UPDATER_SUCCESS_PKEXEC_MARKER="/work/base/artifacts/updater-dispatch-simulation-pkexec.json"
UPDATER_SUCCESS_DPKG_MARKER="/work/base/artifacts/updater-dispatch-simulation-dpkg.json"
UPDATER_SPECIAL_MODE_SUCCESS_RECEIPT="/work/base/artifacts/updater-dispatch-simulation-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
FAKE_BIN_ROOT="/work/base/fake-bin"
mkdir -p "$UPDATER_SUCCESS_STAGE_ROOT" "$FAKE_BIN_ROOT"
: > "$UPDATER_SUCCESS_INSTALLER"
UPDATER_SUCCESS_INSTALLER_ARGUMENT_SHA256="$(printf '%s' "$UPDATER_SUCCESS_INSTALLER" | sha256sum | awk '{print $1}')"
python3 - "$UPDATER_SUCCESS_STATE_PATH" "$UPDATER_SUCCESS_REQUEST_PATH" "$UPDATER_SUCCESS_STAGE_ROOT" "$UPDATER_SUCCESS_INSTALLER" "$(basename "$PUBLISH_DIR" | sed 's/^chummer6-//')" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
request_path = Path(sys.argv[2])
stage_root = sys.argv[3]
installer_path = sys.argv[4]
rid = sys.argv[5]
state = {
    "HeadId": "avalonia",
    "Platform": "linux",
    "Arch": rid.split("-", 1)[1],
    "InstalledVersion": "run-20260618-024810",
    "ChannelId": "stable",
    "LastCheckedAt": "2026-06-18T06:00:00Z",
    "LastManifestVersion": "run-20260618-051119",
    "LastManifestPublishedAt": "2026-06-18T06:15:00Z",
    "LastError": None,
    "PendingUpdateVersion": "run-20260618-051119",
    "PendingUpdateChannelId": "stable",
    "PendingUpdatePreparedAtUtc": "2026-06-18T06:16:00Z",
}
request = {
    "ParentProcessId": 0,
    "StageRoot": stage_root,
    "InstallerPath": installer_path,
    "StateFilePath": str(state_path),
    "Version": "run-20260618-051119",
    "ChannelId": "stable",
    "HeadId": "avalonia",
    "RelaunchArgs": [],
}
state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
PY
cat > "$FAKE_BIN_ROOT/dpkg" <<DPKG_SCRIPT
#!/usr/bin/env bash
set -euo pipefail
[[ "\$#" -eq 2 ]]
[[ "\$1" == "-i" ]]
[[ "\$2" == "$UPDATER_SUCCESS_INSTALLER" ]]
[[ "\$(id -u)" -ne 0 ]]
printf '%s\n' '{"argvCount":2,"installFlag":"-i","installerArgumentBinding":"sha256_of_utf8_gate_stage_installer_path","installerArgumentSha256":"$UPDATER_SUCCESS_INSTALLER_ARGUMENT_SHA256"}' > "$UPDATER_SUCCESS_DPKG_MARKER"
exit 0
DPKG_SCRIPT
cat > "$FAKE_BIN_ROOT/pkexec" <<PKEXEC_SCRIPT
#!/usr/bin/env bash
set -euo pipefail
[[ "\$#" -eq 3 ]]
[[ "\$1" == "dpkg" ]]
[[ "\$2" == "-i" ]]
[[ "\$3" == "$UPDATER_SUCCESS_INSTALLER" ]]
[[ "\$(id -u)" -ne 0 ]]
[[ "\$(command -v dpkg)" == "$FAKE_BIN_ROOT/dpkg" ]]
printf '%s\n' '{"argvCount":3,"commandLabel":"dpkg","installFlag":"-i","installerArgumentBinding":"sha256_of_utf8_gate_stage_installer_path","installerArgumentSha256":"$UPDATER_SUCCESS_INSTALLER_ARGUMENT_SHA256"}' > "$UPDATER_SUCCESS_PKEXEC_MARKER"
exec "\$@"
PKEXEC_SCRIPT
chmod +x "$FAKE_BIN_ROOT/dpkg" "$FAKE_BIN_ROOT/pkexec"
set +e
PATH="$FAKE_BIN_ROOT:$PATH" "$PUBLISH_DIR/Chummer.Avalonia" --desktop-update-launch-installer "$UPDATER_SUCCESS_REQUEST_PATH"
UPDATER_SUCCESS_EXIT_CODE="$?"
set -e
python3 - "$UPDATER_SUCCESS_STATE_PATH" "$UPDATER_SPECIAL_MODE_SUCCESS_RECEIPT" "$UPDATER_SUCCESS_EXIT_CODE" "$(basename "$PUBLISH_DIR" | sed 's/^chummer6-//')" "$UPDATER_SUCCESS_PKEXEC_MARKER" "$UPDATER_SUCCESS_DPKG_MARKER" "$UPDATER_SUCCESS_STAGE_ROOT" "$UPDATER_SUCCESS_INSTALLER_ARGUMENT_SHA256" "$UPDATER_SUCCESS_INSTALLER" "$UPDATER_SUCCESS_REQUEST_PATH" <<'PY'
from __future__ import annotations
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

state_path = Path(sys.argv[1])
receipt_path = Path(sys.argv[2])
exit_code = int(sys.argv[3])
rid = sys.argv[4]
pkexec_marker_path = Path(sys.argv[5])
dpkg_marker_path = Path(sys.argv[6])
stage_root = Path(sys.argv[7])
installer_argument_sha256 = sys.argv[8]
installer_path = Path(sys.argv[9])
request_path = Path(sys.argv[10])
state = json.loads(state_path.read_text(encoding="utf-8-sig"))
failure_reason = str(state.get("LastFailureReason") or "").strip()
last_error = str(state.get("LastError") or "").strip()
pending_update_version = str(state.get("PendingUpdateVersion") or "").strip()
pending_update_channel_id = str(state.get("PendingUpdateChannelId") or "").strip()
expected_pkexec_invocation = {
    "argvCount": 3,
    "commandLabel": "dpkg",
    "installFlag": "-i",
    "installerArgumentBinding": "sha256_of_utf8_gate_stage_installer_path",
    "installerArgumentSha256": installer_argument_sha256,
}
expected_dpkg_invocation = {
    "argvCount": 2,
    "installFlag": "-i",
    "installerArgumentBinding": "sha256_of_utf8_gate_stage_installer_path",
    "installerArgumentSha256": installer_argument_sha256,
}

def load_marker(path: Path) -> object:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

pkexec_invocation = load_marker(pkexec_marker_path)
dpkg_invocation = load_marker(dpkg_marker_path)
pkexec_shim_invoked = pkexec_invocation == expected_pkexec_invocation
dpkg_shim_invoked = dpkg_invocation == expected_dpkg_invocation
invocation_contract_proven = pkexec_shim_invoked and dpkg_shim_invoked
stage_retention_observed = stage_root.is_dir()
expected_stage_paths = {
    "installer_payload": installer_path,
    "installer_request": request_path,
}
try:
    actual_stage_entries = sorted(stage_root.iterdir(), key=lambda path: path.name)
except OSError:
    actual_stage_entries = []
retained_stage_inventory_exact = (
    stage_retention_observed
    and {path.name for path in actual_stage_entries}
        == {path.name for path in expected_stage_paths.values()}
    and all(path.is_file() and not path.is_symlink() for path in actual_stage_entries)
)

def retained_file_descriptor(role: str, path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        return {
            "role": role,
            "fileName": path.name,
            "sizeBytes": -1,
            "sha256": "",
        }
    payload = path.read_bytes()
    return {
        "role": role,
        "fileName": path.name,
        "sizeBytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }

retained_stage_inventory = [
    retained_file_descriptor(role, path)
    for role, path in sorted(expected_stage_paths.items())
]
retained_stage_inventory_sha256 = hashlib.sha256(
    json.dumps(
        retained_stage_inventory,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
status = "pass" if (
    exit_code == 0
    and failure_reason == ""
    and last_error == ""
    and pending_update_version == ""
    and pending_update_channel_id == ""
    and invocation_contract_proven
    and stage_retention_observed
    and retained_stage_inventory_exact
) else "fail"
receipt = {
    "status": status,
    "mode": "desktop_update_dispatch_pending_state_clearing_simulation",
    "headId": str(state.get("HeadId") or "").strip(),
    "channelId": str(state.get("ChannelId") or "").strip(),
    "rid": rid,
    "exitCode": exit_code,
    "expectedExitCode": 0,
    "failureReason": failure_reason,
    "lastError": last_error,
    "pendingUpdateVersion": pending_update_version,
    "pendingUpdateChannelId": pending_update_channel_id,
    "executionModel": "simulated_nonprivileged_pkexec_dpkg",
    "privilegeEscalationPerformed": False,
    "nativePackageManagerExecutionProven": False,
    "invocationContractProven": invocation_contract_proven,
    "pkexecShimInvoked": pkexec_shim_invoked,
    "dpkgShimInvoked": dpkg_shim_invoked,
    "pkexecInvocation": expected_pkexec_invocation,
    "dpkgInvocation": expected_dpkg_invocation,
    "stageRetentionObserved": stage_retention_observed,
    "stagedPayloadCleanupProven": False,
    "retainedStageInventoryExact": retained_stage_inventory_exact,
    "retainedStageInventory": retained_stage_inventory,
    "retainedStageInventorySha256": retained_stage_inventory_sha256,
    "gateStageLocation": "synthetic_gate_stage_outside_normal_ui_temp_root",
    "deferredCleanupPhase": "outside_dispatch_simulation",
    "deferredCleanupPolicy": "new_release_startup_or_two_day_stale_temp_pruning",
    "deferredCleanupExecutionProven": False,
    "recordedAtUtc": datetime.now(UTC).isoformat(),
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
test -f "$UPDATER_SPECIAL_MODE_SUCCESS_RECEIPT"
EOF
)

docker_args=(
  run
  --rm
  -e "CHUMMER_GITHUB_ORG=${CHUMMER_GITHUB_ORG:-ArchonMegalon}"
  -e "CHUMMER_MIN_FREE_GIB=${CHUMMER_LINUX_SOURCE_BUILD_GATE_MIN_FREE_GIB:-0}"
  -e "CHUMMER_KEEP_BUILD_TEMP=0"
  -e "CHUMMER_GATE_SDK_VERSION=$GATE_SDK_VERSION"
  -e "CHUMMER_GATE_SDK_ARCHIVE_URL=$GATE_SDK_ARCHIVE_URL"
  -e "CHUMMER_GATE_SDK_ARCHIVE_SHA256=$GATE_SDK_ARCHIVE_SHA256"
  -e "CHUMMER_GATE_SDK_ARCHIVE_SIZE=$GATE_SDK_ARCHIVE_SIZE"
  -v "$REPO_ROOT:/repo:ro"
  -v "$HOST_WORK_ROOT:$CONTAINER_WORK_ROOT"
  -w /repo
)

if [[ -f "$REPO_ROOT/.git" ]]; then
  git_common_dir="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute --git-common-dir)"
  [[ -d "$git_common_dir" ]] || die "Linked-worktree Git common directory is missing."
  docker_args+=(-v "$git_common_dir:$git_common_dir:ro")
fi

if [[ -n "${CHUMMER_REPO_BASE_URL:-}" ]]; then
  repo_base_url_for_container="$CHUMMER_REPO_BASE_URL"
  if [[ "$CHUMMER_REPO_BASE_URL" == file://* ]]; then
    repo_base_path="${CHUMMER_REPO_BASE_URL#file://}"
    [[ -d "$repo_base_path" ]] || die "CHUMMER_REPO_BASE_URL points to a missing local mirror directory: $repo_base_path"
    repo_base_path="$(cd "$repo_base_path" && pwd -P)"
    docker_args+=(-v "$repo_base_path:/mirror:ro")
    docker_args+=(-e "CHUMMER_GATE_LOCAL_REPO_MIRROR=1")
    repo_base_url_for_container="file:///mirror"
  fi
  docker_args+=(-e "CHUMMER_REPO_BASE_URL=$repo_base_url_for_container")
fi

docker "${docker_args[@]}" \
  "$IMAGE" \
  bash -lc "$ROOT_SETUP_COMMAND" chummer-linux-source-gate "$INNER_COMMAND" 2>&1 | \
  tee "$HOST_WORK_ROOT/docker-gate-$RUN_ID.log"

write_receipt fresh_container

log "Fresh slim-container gate passed."
log "Receipt: $RECEIPT_PATH"
if [[ "$KEEP_WORK_ROOT" == "1" || "$KEEP_WORK_ROOT" == "true" || "$KEEP_WORK_ROOT" == "yes" ]]; then
  log "Gate log: $HOST_WORK_ROOT/docker-gate-$RUN_ID.log"
  log "Build outputs: $HOST_WORK_ROOT/base/artifacts"
else
  log "Set CHUMMER_KEEP_DOCKER_GATE_WORKDIR=1 if you want to keep the container work directory."
fi
