# Build from source on macOS

Most users should use the installers on [Download](DOWNLOAD.md). macOS is not on the public installer shelf today. If you want a personal local build for your own Mac, use the checked-in scripts:

- [`scripts/build-chummer6-macos-local.sh`](scripts/build-chummer6-macos-local.sh)
- [`scripts/install-chummer6-macos-local.sh`](scripts/install-chummer6-macos-local.sh)

## Check the host first

```bash
bash scripts/check-host-chummer6-macos-local.sh --base "$HOME/chummer6-source-build-macos"
```

This only audits the machine and the checked-in build script. It does not clone anything and it does not build Chummer.

## Build

```bash
bash scripts/build-chummer6-macos-local.sh --base "$HOME/chummer6-source-build-macos"
```

The build script does its own host checks, clones the required repositories, bootstraps a local .NET SDK, publishes the Avalonia desktop client, and writes a build manifest. It does not install packages, it does not ask for `sudo`, and it never installs the `.app` bundle.

If a required tool is missing, it stops early and tells you what to install with your package manager. The script only builds the binary and archive artifacts.

Source-built copies default to `notify` for desktop updates and `off` for analytics unless you already chose another value in the environment:

- `CHUMMER_DESKTOP_UPDATE_MODE=notify`
- `CHUMMER_DESKTOP_ANALYTICS_DEFAULT=off`

Set `CHUMMER_KEEP_BUILD_TEMP=1` if you want to keep temporary build files.

## Install the built binary

The binary is installed by a second script on purpose. The build step never installs it for you.

```bash
bash scripts/install-chummer6-macos-local.sh --base "$HOME/chummer6-source-build-macos" --force
```

You can also install straight from the produced archive:

```bash
bash scripts/install-chummer6-macos-local.sh \
  --archive "$HOME/chummer6-source-build-macos/artifacts/chummer6-osx-arm64-<timestamp>.tar.gz" \
  --force
```

The installer script creates a personal unsigned `.app` bundle at:

```text
$HOME/Applications/Chummer6 Source Build.app
```

It strips the quarantine attribute when possible, but this is still an unsigned local build.

## Requirements

- macOS 13 or newer
- Apple Silicon or Intel Mac
- Git and Git LFS
- `curl`, `tar`, `gzip`, `file`
- `shasum` or `sha256sum`
- about 20 GiB of free disk space

## Output

After a successful build, the target directory contains:

- `artifacts/chummer6-osx-arm64/Chummer.Avalonia` or `artifacts/chummer6-osx-x64/Chummer.Avalonia`
- `run-chummer6.sh`
- `BUILD-MANIFEST.txt`
- a `.tar.gz` archive
- a `.sha256` file
- logs under `logs/`

The install script turns that artifact into a launchable local app bundle.

## Notes

This is a local personal source build, not an official macOS release. The scripts do not sign or notarize the app, and they do not change the public macOS support status on `chummer.run`.
