# Build from source on Linux

Most users should use the installers on [Download](DOWNLOAD.md). For a local source build, use the checked-in builder and then the separate installer:

```bash
bash scripts/build-chummer6-linux.sh --base "$HOME/chummer6-source-build"
bash scripts/install-chummer6-linux-local.sh --base "$HOME/chummer6-source-build" --force
```

The build script never installs Linux packages, never asks for `sudo`, and never installs the resulting application into your home directory.

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
- the package composer, source-build script, and release-truth placeholder.

Hub is fixed at commit `35aa5a828f076d7c7c4a57dbab17d8715f9c3b68`. The locked flow fetches that SHA even if the remote `main` branch advances.

The current release truth remains `unbound_review_placeholder`, `review_required`, and `releaseEvidenceEligible=false`. A reproducible dependency graph does not turn this source build into public release evidence.

## SDK and package isolation

The SDK path does not execute `dotnet-install.sh`. Its URL and digest remain only as a forbidden historical reference. The builder downloads the exact SDK `.tar.gz` and verifies its SHA256, SHA512, size, archive structure, toolchain bytes, executable bit, and reported `10.0.103` version.

The package composer independently rebuilds owner packages and compares the result with checked inventories. Restore uses a generated `NuGet.Config` with one source: that same-run local feed. The UI consumer is moved away from owner repositories before restore and publish, and the build sets:

```text
ChummerUseLocalCompatibilityTree=false
```

There is no network NuGet source, sibling project plane, stub package, or ambient local feed in this lane. The exact cache is verified after restore and again after publish.

Each project in the Avalonia restore closure receives its own checked
`packages.lock.json` in its project directory. Restore runs from the isolated UI
root with `--locked-mode`; no global `NuGetLockFilePath` override is permitted.

Temporary checkouts, feeds, caches, NuGet configuration, and diagnostics are removed on normal exit, error, `HUP`, `INT`, and `TERM`. Generator failures remain useful in the build log, but bearer/config values and machine-local paths are sanitized first.

## Python runtime selection

Python 3.11 or newer is required. Selection is deterministic:

1. `CHUMMER_PYTHON`, when explicitly set;
2. `python3.13`;
3. `python3.12`;
4. `python3.11`;
5. `python3`.

Every candidate must explicitly report a compatible version. The discovered executable path is logged; no Linux or macOS host path is hard-coded.

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
- Python 3.11 or newer;
- `curl`, `tar`, `gzip`, and `sha256sum`;
- ICU runtime libraries;
- about 25 GiB free space.

The helpers below remain read-only and do not install packages:

```bash
bash scripts/list-chummer6-linux-prereqs.sh
bash scripts/check-host-chummer6-linux.sh
bash scripts/build-chummer6-linux.sh --audit-only --base /tmp/chummer6-audit
```

For an additional clean-container check:

```bash
bash scripts/verify_linux_source_build_docker_gate.sh
```

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
