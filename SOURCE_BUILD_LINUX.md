# Build from source on Linux

Most users should use the installers on [Download](DOWNLOAD.md). For a local source build, use the checked-in builder and then the separate installer:

```bash
bash scripts/build-chummer6-linux.sh --base "$HOME/chummer6-source-build"
bash scripts/install-chummer6-linux-local.sh --base "$HOME/chummer6-source-build" --force
```

The build script never installs Linux packages, never asks for `sudo`, and never installs the resulting application into your home directory.

The binary is installed by a second script on purpose. Source-built copies
check for newer published builds in notify-only mode by default. The generated
launcher sets `CHUMMER_DESKTOP_UPDATE_MODE=notify` only when you have not
already chosen another mode. Analytics also default to `off` through
`CHUMMER_DESKTOP_ANALYTICS_DEFAULT=off` unless you already chose another value.

## What the lock covers

[`RELEASE.lock.json`](RELEASE.lock.json) is a review-only v2 authority. It binds:

- exact 40-character commits for Core, Hub, Registry, UI Kit, and UI;
- SHA256, SHA512, size, and four toolchain-file hashes for both .NET SDK archives;
- the final UI v5 package-plane receipt;
- Hub's exact v3 package-plane lock, producer, inventory, and three canonical packages;
- a 96-package normalized canonical feed and two 99-package RID restore feeds;
- three RID-specific project-local `packages.lock.json` graphs for Avalonia,
  Desktop Runtime, and Presentation, including exact NuGet `contentHash` values;
- six RID-specific runtime and host packages;
- separate restore and post-publish cache observations;
- the source-lock verifier, package composer, source-build script, and exact
  Registry-bound public release-truth packet.

Hub is fixed at commit `35aa5a828f076d7c7c4a57dbab17d8715f9c3b68`. The locked flow fetches that SHA even if the remote `main` branch advances.

The current release truth is bound to the exact Registry snapshot while its decision remains `review_required` and `releaseEvidenceEligible=false`. A reproducible dependency graph does not turn this source build into public release evidence.

## SDK and package isolation

The SDK path does not execute `dotnet-install.sh`. Its URL and digest remain only as a forbidden historical reference. The builder downloads the exact SDK `.tar.gz` and verifies its SHA256, SHA512, size, archive structure, toolchain bytes, executable bit, and reported `10.0.103` version.

The package composer independently rebuilds owner packages and compares the result with checked inventories. Exact Git source acquisition, the authenticated SDK download, and hash-bound external package acquisition use the network. After those inputs are acquired and verified, Hub package production, owner-package restore/pack, and final UI restore/publish use generated `NuGet.Config` files and command-line restore properties bound only to the same-run local feed. Any HTTP(S) Hub NuGet source fails closed. The UI consumer is moved away from owner repositories before restore and publish, and the build sets:

```text
ChummerUseLocalCompatibilityTree=false
```

There is no network NuGet source, sibling project plane, stub package, or ambient local feed in this lane. The exact cache is verified after restore and again after publish.

Each project in the Avalonia restore closure receives its own checked
`packages.lock.json` in its project directory. Restore runs from the isolated UI
root with `--locked-mode`; no global `NuGetLockFilePath` override is permitted.

Temporary checkouts, feeds, caches, NuGet configuration, and diagnostics are removed on normal exit, error, `HUP`, `INT`, and `TERM`. Generator failures remain useful in the build log, but bearer/config values and machine-local paths are sanitized first.

## Python runtime selection

Python 3.11 through Python 3.x (`>=3.11,<4`) is required. Selection is deterministic:

1. `CHUMMER_PYTHON`, when explicitly set;
2. `python3.13`;
3. `python3.12`;
4. `python3.11`;
5. `python3`.

Every candidate must explicitly report a compatible version. The discovered executable path is logged; no Linux or macOS host path is hard-coded.

The canonical archive records `pythonRequirement=>=3.11,<4` and
`pythonRole=authenticated-orchestrator`, not the observed host patch version.
The selected version remains in the external build log and Docker-gate receipt.
Cross-runtime archive reproducibility is claimed only when an independent host
archive and the clean-container archive have the same SHA256; otherwise the
receipt remains explicitly environment-bounded and ineligible for release evidence.

## Platform models

The observed native lane is `linux-x64`, with 41 exact packages in distinct restore and post-publish caches. The `linux-arm64` authority is an x64-host cross-target lane with 42 exact packages. It is not native ARM execution evidence.

Build x64 on an x64 host:

```bash
bash scripts/build-chummer6-linux.sh \
  --target-rid linux-x64 \
  --base "$HOME/chummer6-source-build"
```

Build the bounded ARM64 cross-target on an x64 host:

```bash
bash scripts/build-chummer6-linux.sh \
  --target-rid linux-arm64 \
  --base "$HOME/chummer6-source-build-arm64"
```

The script stops on a native ARM host instead of representing an unobserved model as evidence.

## Moving refs

`--ref` requires an explicit non-reproducible acknowledgement:

```bash
bash scripts/build-chummer6-linux.sh \
  --audit-only \
  --allow-moving-ref \
  --ref main \
  --base "$HOME/chummer6-source-audit"
```

The full build intentionally stops for moving refs because mutable source cannot consume the checked immutable package plane. Generate and review a new lock instead of bypassing it.

## Requirements

- glibc Linux on x86_64;
- Git;
- Python 3.11 through Python 3.x (`>=3.11,<4`);
- `curl`, `tar`, `gzip`, and `sha256sum`;
- ICU runtime libraries;
- about 25 GiB free space.

The helpers below remain read-only and do not install packages:

```bash
bash scripts/list-chummer6-linux-prereqs.sh
bash scripts/check-host-chummer6-linux.sh
bash scripts/build-chummer6-linux.sh --audit-only --base /tmp/chummer6-audit
```

For an authoritative clean-container check, first preserve the SHA256 and Python
version from an independent host build, then require the two clean container
builds to reproduce those exact archive bytes:

```bash
CHUMMER_HOST_ARCHIVE="$HOME/chummer6-source-build/artifacts/chummer6-linux-x64/chummer6-linux-x64-source-lock.tar.gz"
CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256="$(sha256sum "$CHUMMER_HOST_ARCHIVE" | awk '{print $1}')" \
CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION="$(python3 -c 'import platform; print(platform.python_version())')" \
  bash scripts/verify_linux_source_build_docker_gate.sh
```

The default tracked receipt path rejects a bare same-container-only run. For a
non-authoritative diagnostic, choose a separate path explicitly; it cannot pass
the tracked v2 receipt verifier:

```bash
CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH="$PWD/artifacts/linux-docker-gate-diagnostic.json" \
  bash scripts/verify_linux_source_build_docker_gate.sh
```

The clean-container gate authenticates the exact `linux-x64` SDK archive from
`RELEASE.lock.json` once, installs it under the gate-owned work directory, and
passes that same archive to both clean builds through `CHUMMER_SDK_ARCHIVE`.
Startup and updater checks are bound to that installed SDK through
`DOTNET_ROOT`, `DOTNET_ROOT_X64`, `DOTNET_HOST_PATH`, a gate-first `PATH`, and
`DOTNET_MULTILEVEL_LOOKUP=0`; ambient or system .NET fallback is not allowed.
The v2 receipt records the SDK version, archive authority, digests, size, and
this no-fallback posture without recording a machine-local SDK path.

The updater portion is deliberately an **updater dispatch/pending-state-clearing
simulation**, not an operating-system package installation. It runs
nonprivileged `pkexec` and `dpkg` shims, proves their exact argument counts,
command/flag labels, and a SHA256 binding to the exact staged installer
argument, then verifies pending/error-state clearing. The pinned UI deliberately
retains the installer and request after this handoff, so the gate also proves
that exact two-file retained inventory and records
`stage_retention_observed=true` and `staged_payload_cleanup_proven=false`.
Cleanup belongs to a later new-release startup or two-day stale-temp pruning;
that deferred phase is outside this simulation, and the synthetic gate stage is
outside the normal UI temp root, so the receipt explicitly records that cleanup
execution was not proven. The receipt
explicitly records `privilege_escalation_performed=false` and
`native_package_manager_execution_proven=false`; it does not claim elevation or
native package-manager execution. Runtime errors are reduced to a canonical,
path-free value before any inner or outer receipt is accepted.

It also records exact SHA256 descriptors for the Docker gate, host-audit
wrapper, source-build script, package composer, local installer, unprivileged
identity validator, and source-lock verifier. The strict receipt check
recomputes those current bytes and independently matches the three lock-bound
tools to `RELEASE.lock.json`, so a receipt cannot remain current after any
proof-producing helper changes.

Before archiving, the builder normalizes the stage root and directories to
mode `0755`, regular files to `0644`, and the exact `Chummer.Avalonia`
entrypoint to `0755`. Symlinks, special files, and any other mode are rejected.
The Docker gate checks those member types and modes in both archives before it
accepts cross-runtime byte equality.

## Output and installation

A successful x64 build writes:

```text
$HOME/chummer6-source-build/
  artifacts/chummer6-linux-x64/
    Chummer.Avalonia
    BUILD-MANIFEST.txt
    chummer6-linux-x64-source-lock.tar.gz
    chummer6-linux-x64-source-lock.tar.gz.sha256
  logs/
```

You may install directly from the archive:

```bash
bash scripts/install-chummer6-linux-local.sh \
  --archive "$HOME/chummer6-source-build/artifacts/chummer6-linux-x64/chummer6-linux-x64-source-lock.tar.gz" \
  --force
```

The installer creates a personal copy under `$HOME/.local/opt/chummer6-source-build` and a command link under `$HOME/.local/bin/chummer6-source-build`. A real desktop session is still needed for final startup and visual evidence.
