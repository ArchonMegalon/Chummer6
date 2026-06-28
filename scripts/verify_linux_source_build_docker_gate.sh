#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE="${CHUMMER_LINUX_SOURCE_BUILD_GATE_IMAGE:-debian:bookworm-slim}"
HOST_WORK_ROOT="${CHUMMER_LINUX_SOURCE_BUILD_GATE_WORK_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/chummer6-linux-source-gate.XXXXXX")}"
KEEP_WORK_ROOT="${CHUMMER_KEEP_DOCKER_GATE_WORKDIR:-0}"
RECEIPT_PATH="${CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH:-$REPO_ROOT/.guide-internal/receipts/LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
CONTAINER_WORK_ROOT="/work"
CONTAINER_BASE="$CONTAINER_WORK_ROOT/base"
CONTAINER_LOG="$CONTAINER_WORK_ROOT/gate-$RUN_ID.log"

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
  CHUMMER_GIT_REF                            Git ref for the inner source-build script
  CHUMMER_GITHUB_ORG                         GitHub org for the inner source-build script
  CHUMMER_REPO_BASE_URL                      Mirror base URL for the inner source-build script
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

command -v docker >/dev/null 2>&1 || die "docker is required for the fresh-container gate."
[[ -f "$REPO_ROOT/scripts/build-chummer6-linux.sh" ]] || die "build script missing: $REPO_ROOT/scripts/build-chummer6-linux.sh"
[[ -f "$REPO_ROOT/scripts/install-chummer6-linux-local.sh" ]] || die "install script missing: $REPO_ROOT/scripts/install-chummer6-linux-local.sh"
[[ -f "$REPO_ROOT/scripts/check-host-chummer6-linux.sh" ]] || die "audit wrapper missing: $REPO_ROOT/scripts/check-host-chummer6-linux.sh"
assert_build_script_no_privilege_escalation

mkdir -p "$HOST_WORK_ROOT"
HOST_WORK_ROOT="$(cd "$HOST_WORK_ROOT" && pwd -P)"

log "Docker image: $IMAGE"
log "Host work root: $HOST_WORK_ROOT"

write_receipt() {
  local artifacts_root="$HOST_WORK_ROOT/base/artifacts"
  local publish_dir=""
  local archive_path=""
  local manifest_path=""
  local launcher_path=""
  local binary_path=""
  local build_log_path=""
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
  archive_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'chummer6-linux-*.tar.gz' | sort | head -n 1)"
  [[ -n "$archive_path" ]] || die "Could not locate published archive under $artifacts_root"
  manifest_path="$publish_dir/BUILD-MANIFEST.txt"
  launcher_path="$publish_dir/run-chummer6.sh"
  binary_path="$publish_dir/Chummer.Avalonia"
  build_log_path="$(find "$HOST_WORK_ROOT/base/logs" -mindepth 1 -maxdepth 1 -type f -name 'linux-desktop-build-*.log' | sort | tail -n 1)"
  startup_smoke_receipt_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'startup-smoke-*.receipt.json' | sort | head -n 1)"
  startup_smoke_failure_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'startup-smoke-*.failure.json' | sort | head -n 1)"
  install_startup_smoke_receipt_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'installed-startup-smoke-*.receipt.json' | sort | head -n 1)"
  install_startup_smoke_failure_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'installed-startup-smoke-*.failure.json' | sort | head -n 1)"
  updater_special_mode_receipt_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'updater-special-mode-*.receipt.json' | sort | head -n 1)"
  updater_special_mode_success_receipt_path="$(find "$artifacts_root" -mindepth 1 -maxdepth 1 -type f -name 'updater-special-mode-success-*.receipt.json' | sort | head -n 1)"

  [[ -f "$manifest_path" ]] || die "Missing build manifest: $manifest_path"
  [[ -f "$launcher_path" ]] || die "Missing launcher: $launcher_path"
  [[ -f "$binary_path" ]] || die "Missing published binary: $binary_path"
  [[ -n "$build_log_path" && -f "$build_log_path" ]] || die "Missing build log under $HOST_WORK_ROOT/base/logs"
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

  rid="$(basename "$publish_dir" | sed 's/^chummer6-//')"
  executable_sha="$(sha256sum "$binary_path" | awk '{print $1}')"
  archive_sha="$(sha256sum "$archive_path" | awk '{print $1}')"

  mkdir -p "$(dirname "$RECEIPT_PATH")"
  python3 - "$RECEIPT_PATH" "$RUN_ID" "$IMAGE" "${CHUMMER_GIT_REF:-main}" "${CHUMMER_GITHUB_ORG:-ArchonMegalon}" "${CHUMMER_REPO_BASE_URL:-}" "$rid" "$executable_sha" "$archive_sha" "$manifest_path" "$build_log_path" "$binary_path" "$archive_path" "$launcher_path" "$startup_smoke_receipt_path" "$install_startup_smoke_receipt_path" "$updater_special_mode_receipt_path" "$updater_special_mode_success_receipt_path" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

receipt_path = Path(sys.argv[1])
run_id = sys.argv[2]
image = sys.argv[3]
git_ref = sys.argv[4]
github_org = sys.argv[5]
repo_base_url = sys.argv[6]
rid = sys.argv[7]
executable_sha = sys.argv[8]
archive_sha = sys.argv[9]
manifest_path = Path(sys.argv[10])
build_log_path = Path(sys.argv[11])
binary_path = Path(sys.argv[12])
archive_path = Path(sys.argv[13])
launcher_path = Path(sys.argv[14])
startup_smoke_receipt_path = Path(sys.argv[15])
install_startup_smoke_receipt_path = Path(sys.argv[16])
updater_special_mode_receipt_path = Path(sys.argv[17])
updater_special_mode_success_receipt_path = Path(sys.argv[18])

manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
startup_smoke_receipt = json.loads(startup_smoke_receipt_path.read_text(encoding="utf-8-sig"))
install_startup_smoke_receipt = json.loads(install_startup_smoke_receipt_path.read_text(encoding="utf-8-sig"))
updater_special_mode_receipt = json.loads(updater_special_mode_receipt_path.read_text(encoding="utf-8-sig"))
updater_special_mode_success_receipt = json.loads(updater_special_mode_success_receipt_path.read_text(encoding="utf-8-sig"))
source_heads = {}
for line in manifest_lines:
    if line.startswith("chummer6-"):
        parts = line.split()
        if len(parts) >= 2:
            source_heads[parts[0]] = parts[-1]

receipt = {
    "contract_name": "ea.chummer6_linux_source_build_docker_gate.v1",
    "status": "passed",
    "generated_at_utc": run_id,
    "docker_image": image,
    "git_ref": git_ref,
    "github_org": github_org,
    "repo_base_url": repo_base_url or f"https://github.com/{github_org}",
    "gate": {
        "name": "linux_source_build_fresh_container",
        "host_audit_wrapper": "scripts/check-host-chummer6-linux.sh",
        "build_script": "scripts/build-chummer6-linux.sh",
        "install_script": "scripts/install-chummer6-linux-local.sh",
        "container_flow": "audit_then_full_build_then_local_install",
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
        "executable_sha256": executable_sha,
        "archive_sha256": archive_sha,
    },
    "artifacts": {
        "build_manifest_excerpt": manifest_lines[:20],
        "source_heads": source_heads,
        "build_log_name": build_log_path.name,
        "startup_smoke_receipt_name": startup_smoke_receipt_path.name,
        "installed_startup_smoke_receipt_name": install_startup_smoke_receipt_path.name,
        "updater_special_mode_receipt_name": updater_special_mode_receipt_path.name,
        "updater_special_mode_success_receipt_name": updater_special_mode_success_receipt_path.name,
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
            "pending_update_version": str(updater_special_mode_receipt.get("pendingUpdateVersion") or "").strip(),
            "pending_update_channel_id": str(updater_special_mode_receipt.get("pendingUpdateChannelId") or "").strip(),
            "recorded_at_utc": str(updater_special_mode_receipt.get("recordedAtUtc") or "").strip(),
        },
        "updater_special_mode_success": {
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
            "dpkg_invoked": bool(updater_special_mode_success_receipt.get("dpkgInvoked")),
            "stage_deleted": bool(updater_special_mode_success_receipt.get("stageDeleted")),
            "recorded_at_utc": str(updater_special_mode_success_receipt.get("recordedAtUtc") or "").strip(),
        },
    },
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

INNER_COMMAND=$(cat <<'EOF'
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
git lfs install --skip-repo >/dev/null
if [[ "${CHUMMER_GATE_LOCAL_REPO_MIRROR:-0}" == "1" ]]; then
  git config --global --add safe.directory '*'
fi
cd /repo
bash scripts/check-host-chummer6-linux.sh --base /work/base
bash scripts/build-chummer6-linux.sh --base /work/base
test -x /work/base/artifacts/chummer6-linux-x64/Chummer.Avalonia || test -x /work/base/artifacts/chummer6-linux-arm64/Chummer.Avalonia
ls -1 /work/base/artifacts/chummer6-*.tar.gz >/dev/null
PUBLISH_DIR="$(find /work/base/artifacts -mindepth 1 -maxdepth 1 -type d -name 'chummer6-linux-*' | sort | head -n 1)"
test -n "$PUBLISH_DIR"
ARCHIVE_PATH="$(find /work/base/artifacts -mindepth 1 -maxdepth 1 -type f -name 'chummer6-linux-*.tar.gz' | sort | head -n 1)"
test -n "$ARCHIVE_PATH"
STARTUP_SMOKE_RECEIPT="/work/base/artifacts/startup-smoke-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
STARTUP_SMOKE_FAILURE="/work/base/artifacts/startup-smoke-$(date -u +%Y%m%dT%H%M%SZ).failure.json"
CHUMMER_DESKTOP_STARTUP_SMOKE_RECEIPT="$STARTUP_SMOKE_RECEIPT" \
CHUMMER_DESKTOP_STARTUP_SMOKE_FAILURE_PACKET="$STARTUP_SMOKE_FAILURE" \
CHUMMER_DESKTOP_STARTUP_SMOKE_READY_CHECKPOINT="fresh_container_gate" \
CHUMMER_DESKTOP_STARTUP_SMOKE_HOST_CLASS="debian:bookworm-slim" \
CHUMMER_DESKTOP_STARTUP_SMOKE_RID="$(basename "$PUBLISH_DIR" | sed 's/^chummer6-//')" \
"$PUBLISH_DIR/run-chummer6.sh" --startup-smoke
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
"$PUBLISH_DIR/run-chummer6.sh" --desktop-update-launch-installer "$UPDATER_REQUEST_PATH"
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
receipt = {
    "status": "pass" if exit_code == 1 and state.get("LastFailureReason") == "installer_launch_failed" else "fail",
    "mode": "desktop_update_launch_installer",
    "headId": str(state.get("HeadId") or "").strip(),
    "channelId": str(state.get("ChannelId") or "").strip(),
    "rid": rid,
    "exitCode": exit_code,
    "expectedExitCode": 1,
    "failureReason": str(state.get("LastFailureReason") or "").strip(),
    "lastError": str(state.get("LastError") or "").strip(),
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
UPDATER_SUCCESS_MARKER="/work/base/artifacts/updater-special-mode-success-dpkg-invoked.txt"
UPDATER_SPECIAL_MODE_SUCCESS_RECEIPT="/work/base/artifacts/updater-special-mode-success-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
FAKE_BIN_ROOT="/work/base/fake-bin"
mkdir -p "$UPDATER_SUCCESS_STAGE_ROOT" "$FAKE_BIN_ROOT"
: > "$UPDATER_SUCCESS_INSTALLER"
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
printf '%s\n' "\$*" > "$UPDATER_SUCCESS_MARKER"
exit 0
DPKG_SCRIPT
chmod +x "$FAKE_BIN_ROOT/dpkg"
set +e
PATH="$FAKE_BIN_ROOT:$PATH" "$PUBLISH_DIR/run-chummer6.sh" --desktop-update-launch-installer "$UPDATER_SUCCESS_REQUEST_PATH"
UPDATER_SUCCESS_EXIT_CODE="$?"
set -e
python3 - "$UPDATER_SUCCESS_STATE_PATH" "$UPDATER_SPECIAL_MODE_SUCCESS_RECEIPT" "$UPDATER_SUCCESS_EXIT_CODE" "$(basename "$PUBLISH_DIR" | sed 's/^chummer6-//')" "$UPDATER_SUCCESS_MARKER" "$UPDATER_SUCCESS_STAGE_ROOT" <<'PY'
from __future__ import annotations
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

state_path = Path(sys.argv[1])
receipt_path = Path(sys.argv[2])
exit_code = int(sys.argv[3])
rid = sys.argv[4]
marker_path = Path(sys.argv[5])
stage_root = Path(sys.argv[6])
state = json.loads(state_path.read_text(encoding="utf-8-sig"))
failure_reason = str(state.get("LastFailureReason") or "").strip()
last_error = str(state.get("LastError") or "").strip()
pending_update_version = str(state.get("PendingUpdateVersion") or "").strip()
pending_update_channel_id = str(state.get("PendingUpdateChannelId") or "").strip()
dpkg_invoked = marker_path.exists()
stage_deleted = not stage_root.exists()
status = "pass" if (
    exit_code == 0
    and failure_reason == ""
    and last_error == ""
    and pending_update_version == ""
    and pending_update_channel_id == ""
    and dpkg_invoked
) else "fail"
receipt = {
    "status": status,
    "mode": "desktop_update_launch_installer_success",
    "headId": str(state.get("HeadId") or "").strip(),
    "channelId": str(state.get("ChannelId") or "").strip(),
    "rid": rid,
    "exitCode": exit_code,
    "expectedExitCode": 0,
    "failureReason": failure_reason,
    "lastError": last_error,
    "pendingUpdateVersion": pending_update_version,
    "pendingUpdateChannelId": pending_update_channel_id,
    "dpkgInvoked": dpkg_invoked,
    "stageDeleted": stage_deleted,
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
  -e "CHUMMER_GIT_REF=${CHUMMER_GIT_REF:-main}"
  -e "CHUMMER_GITHUB_ORG=${CHUMMER_GITHUB_ORG:-ArchonMegalon}"
  -e "CHUMMER_MIN_FREE_GIB=${CHUMMER_LINUX_SOURCE_BUILD_GATE_MIN_FREE_GIB:-0}"
  -e "CHUMMER_KEEP_BUILD_TEMP=0"
  -v "$REPO_ROOT:/repo:ro"
  -v "$HOST_WORK_ROOT:$CONTAINER_WORK_ROOT"
  -w /repo
)

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
  bash -lc "$INNER_COMMAND" | tee "$HOST_WORK_ROOT/docker-gate-$RUN_ID.log"

write_receipt

log "Fresh slim-container gate passed."
log "Receipt: $RECEIPT_PATH"
if [[ "$KEEP_WORK_ROOT" == "1" || "$KEEP_WORK_ROOT" == "true" || "$KEEP_WORK_ROOT" == "yes" ]]; then
  log "Gate log: $HOST_WORK_ROOT/docker-gate-$RUN_ID.log"
  log "Build outputs: $HOST_WORK_ROOT/base/artifacts"
else
  log "Set CHUMMER_KEEP_DOCKER_GATE_WORKDIR=1 if you want to keep the container work directory."
fi
