# Build from source on Linux

Most users should use the installers on [Download](DOWNLOAD.md). If you want a local source build, use the checked-in script:

[`scripts/build-chummer6-linux.sh`](https://github.com/ArchonMegalon/Chummer6/blob/main/scripts/build-chummer6-linux.sh)

## Build

```bash
bash scripts/build-chummer6-linux.sh --base "$HOME/chummer6-source-build"
```

The script does its own host checks, clones the required repositories, bootstraps a local .NET SDK, publishes the Avalonia desktop client, and writes a build manifest. It does not install Linux packages and it does not ask for `sudo`.

If a required tool is missing, it stops early and tells you what to install. `--skip-system-deps` is still accepted for compatibility, but the script does not install system packages either way.

If you use mirrors, set `CHUMMER_REPO_BASE_URL`. The script expects `chummer6-core.git`, `chummer6-hub.git`, `chummer6-hub-registry.git`, `chummer6-ui-kit.git`, and `chummer6-ui.git`.

Set `CHUMMER_KEEP_BUILD_TEMP=1` if you want to keep temporary build files.

Source builds default to `CHUMMER_DESKTOP_UPDATE_MODE=notify`, so they can report newer published builds without replacing themselves. The updater supports three modes: `full` for automatic download and replacement, `notify` for update notices without automatic replacement, and `off` to skip startup update checks.

## Requirements

- Linux with glibc
- x86_64 or arm64
- Git and Git LFS
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

## Output

After a successful build, the target directory contains:

- `artifacts/chummer6-linux-x64/Chummer.Avalonia` or `artifacts/chummer6-linux-arm64/Chummer.Avalonia`
- `run-chummer6.sh`
- `BUILD-MANIFEST.txt`
- a `.tar.gz` archive
- a `.sha256` file
- logs under `logs/`

Run it with:

```bash
~/chummer6-source-build/artifacts/chummer6-linux-x64/run-chummer6.sh
```

Use `linux-arm64` instead of `linux-x64` on arm64 systems.

## Notes

The script stops on local changes, low disk space, musl/Alpine hosts, non-executable directories, or missing native libraries after publish.

The binary and its native library links are verified. A real desktop session is still needed for a final launch check.

This is a local source build, not an official release.
