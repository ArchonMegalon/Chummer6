# Build from source on Linux

Most users should use the installers on [Download](DOWNLOAD.md). This page is for users who prefer to build the Linux desktop client themselves.

The source-build script creates a local workspace, downloads the Chummer6 repositories, installs the .NET SDK into that workspace, publishes the Avalonia desktop client, and writes a manifest with the exact source revisions used.

Source-built copies check for newer published builds in notify-only mode by default. They will tell you when a newer build exists, but they will not replace themselves unless you change `CHUMMER_DESKTOP_UPDATE_MODE`.

## Quick audit

Run this first from a local checkout of this docs repository. It does not install packages, clone repositories, or build Chummer. The [source-build script](scripts/build-chummer6-linux.sh) is checked in with these docs.

```bash
bash -n scripts/build-chummer6-linux.sh
bash scripts/build-chummer6-linux.sh --audit-only --base "$HOME/chummer6-source-build"
```

## Full build

```bash
bash scripts/build-chummer6-linux.sh --base "$HOME/chummer6-source-build"
```

The script asks before installing Linux prerequisites. Use this when you want the script to install missing packages for your distribution.

If you want to install packages yourself first, use:

```bash
bash scripts/build-chummer6-linux.sh --skip-system-deps --base "$HOME/chummer6-source-build"
```

If you mirror the repositories yourself, set `CHUMMER_REPO_BASE_URL` to the mirror base URL. The script expects repositories named `chummer6-core.git`, `chummer6-hub.git`, `chummer6-hub-registry.git`, `chummer6-ui-kit.git`, and `chummer6-ui.git`.

Set `CHUMMER_KEEP_BUILD_TEMP=1` when you need to keep temporary build directories for debugging. Otherwise the script removes temporary runtime and package-plane files after the archive is written.

## What it needs

- Linux with glibc.
- x86_64 or arm64 CPU.
- Git and Git LFS.
- `curl`, `tar`, `gzip`, `sha256sum`, `file`, and normal Linux desktop runtime libraries.
- About 25 GiB free disk space by default.

The script supports Debian/Ubuntu, Fedora/RHEL-style, Arch/Manjaro-style, and openSUSE-style package managers for prerequisite installation.

## Output

After a successful build, the workspace contains:

- `artifacts/chummer6-linux-x64/Chummer.Avalonia` or `artifacts/chummer6-linux-arm64/Chummer.Avalonia`
- `run-chummer6.sh`
- `BUILD-MANIFEST.txt`
- a `.tar.gz` archive
- a `.sha256` checksum file
- a full log under `logs/`

Run the client with:

```bash
~/chummer6-source-build/artifacts/chummer6-linux-x64/run-chummer6.sh
```

Use `linux-arm64` instead of `linux-x64` on arm64 machines.

The generated launcher sets `CHUMMER_DESKTOP_UPDATE_MODE=notify` only when you have not already chosen another mode.

## Safety notes

The script stops if the workspace has local changes, if the directory is not executable, if the disk is too small, if the host uses musl/Alpine, or if required native libraries are missing after publish.

It does not make this source-built copy an official release. It is a local build for users who want to inspect and build the code themselves.
