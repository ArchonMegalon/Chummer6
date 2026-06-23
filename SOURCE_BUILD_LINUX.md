# Build from source on Linux

Most users should use the installers on [Download](DOWNLOAD.md). This page is for users who prefer to build the Linux desktop client themselves.

This page documents the checked-in source-build script at `scripts/build-chummer6-linux.sh`.

The script creates a local workspace, downloads the Chummer6 repositories, installs the .NET SDK into that workspace, publishes the Avalonia desktop client, and writes a manifest with the exact source revisions used.

It never installs Linux system packages and never asks for `sudo`. If the host is missing base tools such as `git`, `git-lfs`, `curl`, `flock`, or `file`, the script stops and tells you what to install first.

Source-built copies check for newer published builds in notify-only mode by default. They will tell you when a newer build exists, but they will not replace themselves unless you change `CHUMMER_DESKTOP_UPDATE_MODE`.

The updater supports three modes:

- `full` for automatic download and replacement.
- `notify` for update notices without automatic replacement.
- `off` to skip startup update checks.

Source builds default to `notify` so a locally built copy never silently replaces itself with a published installer build.

## Quick audit

Run this first from a local checkout of this docs repository. It does not install packages, clone repositories, or build Chummer.

```bash
bash scripts/list-chummer6-linux-prereqs.sh
bash scripts/check-host-chummer6-linux.sh --base "$HOME/chummer6-source-build"
```

If you prefer the lower-level commands, the wrapper above expands to:

```bash
bash -n scripts/build-chummer6-linux.sh
bash scripts/build-chummer6-linux.sh --audit-only --base "$HOME/chummer6-source-build"
```

## Fresh-container publish gate

The publish lane now has a dedicated Linux source-build gate. It starts a fresh `debian:bookworm-slim` container, installs the required host packages inside that container, runs the checked-in audit wrapper, and then runs the full checked-in source-build script.

```bash
bash scripts/verify_linux_source_build_docker_gate.sh
```

Use `CHUMMER_KEEP_DOCKER_GATE_WORKDIR=1` if you need to keep the container work directory and logs after the gate finishes.

The gate also writes a structured internal release record so the release lane keeps durable evidence of the fresh-container pass:

- `.guide-internal/receipts/LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json`

## Full build

```bash
bash scripts/build-chummer6-linux.sh --base "$HOME/chummer6-source-build"
```

If your host is missing prerequisites, print the expected package names first:

```bash
bash scripts/list-chummer6-linux-prereqs.sh
```

Then install the matching packages with your distribution package manager and rerun the audit or the full build. `--skip-system-deps` is accepted for compatibility, but the script no longer installs system packages either way.

If you mirror the repositories yourself, set `CHUMMER_REPO_BASE_URL` to the mirror base URL. The script expects repositories named `chummer6-core.git`, `chummer6-hub.git`, `chummer6-hub-registry.git`, `chummer6-ui-kit.git`, and `chummer6-ui.git`.

Set `CHUMMER_KEEP_BUILD_TEMP=1` when you need to keep temporary build directories for debugging. Otherwise the script removes temporary runtime and package-plane files after the archive is written.

## What it needs

- Linux with glibc.
- x86_64 or arm64 CPU.
- Git and Git LFS.
- `curl`, `tar`, `gzip`, `sha256sum`, `file`, and normal Linux desktop runtime libraries.
- ICU runtime libraries for the local .NET SDK.
- About 25 GiB free disk space by default.

The checked-in helper scripts recognize Debian/Ubuntu, Fedora/RHEL-style, Arch/Manjaro-style, and openSUSE-style package managers so they can print sensible prerequisite hints when host tools are missing.

## Output

After a successful build, the workspace contains:

- `artifacts/chummer6-linux-x64/Chummer.Avalonia` or `artifacts/chummer6-linux-arm64/Chummer.Avalonia`
- `run-chummer6.sh`
- `BUILD-MANIFEST.txt`
- a `.tar.gz` archive
- a `.sha256` checksum file
- a full log under `logs/`

The script prints both hashes at the end:

- `Executable SHA256` for the built desktop binary
- `Archive SHA256` for the generated `.tar.gz`

Run the client with:

```bash
~/chummer6-source-build/artifacts/chummer6-linux-x64/run-chummer6.sh
```

Use `linux-arm64` instead of `linux-x64` on arm64 machines.

The generated launcher sets `CHUMMER_DESKTOP_UPDATE_MODE=notify` only when you have not already chosen another mode.

## Safety notes

The script stops if the workspace has local changes, if the directory is not executable, if the disk is too small, if the host uses musl/Alpine, or if required native libraries are missing after publish.

The script verifies the published binary and its native library links. It does not prove that the GUI can open in a headless shell; the final desktop launch check still needs a real Linux desktop session with X11 or Wayland.

It does not make this source-built copy an official release. It is a local build for users who want to inspect and build the code themselves.
