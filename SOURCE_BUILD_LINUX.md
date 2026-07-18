# Build from source on Linux

Most users should use the installers on [Download](DOWNLOAD.md). If you want a local source build, use the checked-in script:

[`scripts/build-chummer6-linux.sh`](scripts/build-chummer6-linux.sh)

and install the result afterwards with:

[`scripts/install-chummer6-linux-local.sh`](scripts/install-chummer6-linux-local.sh)

## Build

```bash
bash scripts/build-chummer6-linux.sh --base "$HOME/chummer6-source-build"
```

The script does its own host checks, resolves every owner repository from [`RELEASE.lock.json`](RELEASE.lock.json), bootstraps the locked local .NET SDK, verifies the locked NuGet service index, restores the checked per-RID Avalonia dependency graph in NuGet locked mode, publishes the desktop client, and writes a build manifest. It does not install Linux packages and it does not ask for `sudo`.

The lock binds the exact five owner commits, .NET SDK version, `dotnet-install.sh` SHA256, NuGet service-index SHA256, the complete resolved Avalonia package graph and NuGet `contentHash` values for `linux-x64` and `linux-arm64`, SDK-injected runtime-pack hashes, build-script SHA256, and the checked release-truth projection SHA256. The current UI Kit source pin is `d51ecd99cf72098d4adc8db0192bff7bf9fd8e61`.

Restore runs with a generated `NuGet.Config` that clears inherited sources, names only the lock-approved NuGet service index, and maps every allowed package ID explicitly. The build clears ambient feed, package-version, local-project, and restore-path overrides first. It then creates a new isolated package cache, refuses to reuse a pre-existing cache at that locked path, runs the root project against the checked `packages.lock.json` with `--locked-mode`, and verifies the resulting cache before and after publish. Package graph drift, `contentHash` drift, unexpected packages, source drift, archive drift, and symlinked cache entries fail closed.

The current release projection is deliberately `unbound_review_placeholder`, so these builds remain ineligible for release evidence until Registry supplies a bound immutable authority snapshot. The script records that posture in `BUILD-MANIFEST.txt`; dependency reproducibility never turns an unbound packet into a release claim.

`--ref` no longer opts into a moving branch by itself. Development builds from `main` require an explicit acknowledgement and print a non-release-evidence warning:

```bash
bash scripts/build-chummer6-linux.sh \
  --allow-moving-ref \
  --ref main \
  --base "$HOME/chummer6-source-build-moving"
```

Use `--lock PATH` or `CHUMMER_RELEASE_LOCK` only with a reviewed lock that passes `scripts/verify_linux_source_lock.py`. Digest and dependency-graph mismatches fail before downloaded scripts or package restores run. Moving-ref builds still use the checked package allowlist and therefore fail if their package graph has drifted; update and review the lock instead of bypassing it.

The build step never installs the user-local copy for you. It only produces the artifact directory and archive.

If a required tool is missing, it stops early and tells you what to install. `--skip-system-deps` is still accepted for compatibility, but the script does not install system packages either way.

If you use mirrors, set `CHUMMER_REPO_BASE_URL`. The script expects `chummer6-core.git`, `chummer6-hub.git`, `chummer6-hub-registry.git`, `chummer6-ui-kit.git`, and `chummer6-ui.git`.

Set `CHUMMER_KEEP_BUILD_TEMP=1` if you want to keep temporary build files.

Source-built copies check for newer published builds in notify-only mode by default. The generated launcher sets `CHUMMER_DESKTOP_UPDATE_MODE=notify` only when you have not already chosen another mode. Analytics also default to `off` through `CHUMMER_DESKTOP_ANALYTICS_DEFAULT=off` unless you already chose another value. The updater supports three modes: `full` for automatic download and replacement, `notify` for update notices without automatic replacement, and `off` to skip startup update checks.

## Requirements

- Linux with glibc
- x86_64 or arm64
- Git and Git LFS
- Python 3
- `curl`, `tar`, `gzip`, `sha256sum`, `file`, `flock`
- ICU runtime libraries
- about 25 GiB of free disk space

Before you build, you can inspect the checked-in helpers directly:

```bash
bash scripts/list-chummer6-linux-prereqs.sh
bash scripts/check-host-chummer6-linux.sh
```

`scripts/list-chummer6-linux-prereqs.sh` prints package hints for Debian/Ubuntu, Fedora/RHEL-style, Arch/Manjaro-style, and openSUSE-style systems. `scripts/check-host-chummer6-linux.sh` runs the same local-first host audit without cloning or publishing anything.

For extra-paranoid builds, you can also run the checked-in Docker verification script:

```bash
bash scripts/verify_linux_source_build_docker_gate.sh
```

It runs the build in a clean `debian:bookworm-slim` container. Set `CHUMMER_KEEP_DOCKER_GATE_WORKDIR=1` to keep the work directory and logs.

## Install the built binary

The binary is installed by a second script on purpose.

```bash
bash scripts/install-chummer6-linux-local.sh --base "$HOME/chummer6-source-build" --force
```

You can also install straight from the produced archive:

```bash
bash scripts/install-chummer6-linux-local.sh \
  --archive "$HOME/chummer6-source-build/artifacts/chummer6-linux-x64-<timestamp>.tar.gz" \
  --force
```

The installer script creates a user-local install directory at:

```text
$HOME/.local/opt/chummer6-source-build
```

and a command link at:

```text
$HOME/.local/bin/chummer6-source-build
```

## Output

After a successful build, the target directory contains:

- `artifacts/chummer6-linux-x64/Chummer.Avalonia` or `artifacts/chummer6-linux-arm64/Chummer.Avalonia`
- `run-chummer6.sh`
- `BUILD-MANIFEST.txt`
- a `.tar.gz` archive
- a `.sha256` file
- logs under `logs/`

The install script turns that artifact into a user-local installed copy with a stable command link.

## Notes

The script stops on lock drift, checkout drift, download digest drift, local changes, low disk space, musl/Alpine hosts, non-executable directories, or missing native libraries after publish.

The binary and its native library links are verified. A real desktop session is still needed for a final launch check.

This is a local source build, not an official release. A moving-ref build is always ineligible for release evidence; a locked build becomes eligible only after its lock carries a bound Registry authority snapshot.
