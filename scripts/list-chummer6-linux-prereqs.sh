#!/usr/bin/env bash
set -Eeuo pipefail

MANAGER="auto"

usage() {
  cat <<'USAGE'
Print the Linux host packages typically needed before running the Chummer6 source-build script.

Usage:
  ./list-chummer6-linux-prereqs.sh [options]

Options:
  --manager NAME   Force a package manager family: apt, dnf, pacman, zypper, or auto.
  --help, -h       Show this help.

This script never installs packages. It only prints the package names and example commands.
USAGE
}

while (($#)); do
  case "$1" in
    --manager)
      [[ $# -ge 2 ]] || { echo "--manager requires a value" >&2; exit 2; }
      MANAGER="$2"
      shift 2
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

detect_manager() {
  local distro_id="unknown"
  local distro_like=""
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    distro_id="${ID:-unknown}"
    distro_like="${ID_LIKE:-}"
  fi

  local all_ids=" $distro_id $distro_like "
  if [[ "$all_ids" == *" debian "* || "$all_ids" == *" ubuntu "* || "$all_ids" == *" linuxmint "* ]] && command -v apt-get >/dev/null 2>&1; then
    printf 'apt'
  elif [[ "$all_ids" == *" fedora "* || "$all_ids" == *" rhel "* || "$all_ids" == *" centos "* || "$all_ids" == *" rocky "* || "$all_ids" == *" almalinux "* ]] && command -v dnf >/dev/null 2>&1; then
    printf 'dnf'
  elif [[ "$all_ids" == *" arch "* || "$all_ids" == *" manjaro "* ]] && command -v pacman >/dev/null 2>&1; then
    printf 'pacman'
  elif [[ "$all_ids" == *" suse "* || "$all_ids" == *" opensuse "* ]] && command -v zypper >/dev/null 2>&1; then
    printf 'zypper'
  elif command -v apt-get >/dev/null 2>&1; then
    printf 'apt'
  elif command -v dnf >/dev/null 2>&1; then
    printf 'dnf'
  elif command -v pacman >/dev/null 2>&1; then
    printf 'pacman'
  elif command -v zypper >/dev/null 2>&1; then
    printf 'zypper'
  else
    printf 'unknown'
  fi
}

print_packages() {
  local manager="$1"
  case "$manager" in
    apt)
      cat <<'APT'
Package manager: apt

Base tools:
  git git-lfs curl tar gzip unzip xz-utils util-linux file

Runtime and desktop libraries:
  libc6 libgcc-s1 libgssapi-krb5-2 libicu-dev libssl-dev libstdc++6 zlib1g
  libx11-6 libx11-xcb1 libxcb1 libxkbcommon0 libfontconfig1 libfreetype6
  libgl1 libegl1 libglx0 libgbm1 libdrm2 libice6 libsm6 libxext6 libxfixes3
  libxi6 libxrandr2 libxcursor1 libxinerama1 libwayland-client0 libwayland-cursor0 dbus

Example command:
  apt-get install git git-lfs curl ca-certificates tar gzip unzip xz-utils util-linux file \
    libc6 libgcc-s1 libgssapi-krb5-2 libicu-dev libssl-dev libstdc++6 zlib1g \
    libx11-6 libx11-xcb1 libxcb1 libxkbcommon0 libfontconfig1 libfreetype6 \
    libgl1 libegl1 libglx0 libgbm1 libdrm2 libice6 libsm6 libxext6 libxfixes3 \
    libxi6 libxrandr2 libxcursor1 libxinerama1 libwayland-client0 libwayland-cursor0 dbus
APT
      ;;
    dnf)
      cat <<'DNF'
Package manager: dnf

Base tools:
  git git-lfs curl tar gzip unzip xz util-linux file

Runtime and desktop libraries:
  glibc libgcc krb5-libs libicu openssl-libs libstdc++ zlib
  libX11 libX11-xcb libxcb libxkbcommon fontconfig freetype mesa-libGL mesa-libEGL
  mesa-libgbm libdrm libICE libSM libXext libXfixes libXi libXrandr libXcursor
  libXinerama wayland-libs dbus

Example command:
  dnf install git git-lfs curl ca-certificates tar gzip unzip xz util-linux file \
    glibc libgcc krb5-libs libicu openssl-libs libstdc++ zlib \
    libX11 libX11-xcb libxcb libxkbcommon fontconfig freetype mesa-libGL mesa-libEGL \
    mesa-libgbm libdrm libICE libSM libXext libXfixes libXi libXrandr libXcursor \
    libXinerama wayland-libs dbus
DNF
      ;;
    pacman)
      cat <<'PACMAN'
Package manager: pacman

Base tools:
  git git-lfs curl tar gzip unzip xz util-linux file

Runtime and desktop libraries:
  glibc gcc-libs krb5 icu openssl zlib libx11 libxcb libxkbcommon
  fontconfig freetype2 mesa libglvnd libdrm libice libsm libxext libxfixes libxi
  libxrandr libxcursor libxinerama wayland dbus

Example command:
  pacman -S --needed git git-lfs curl ca-certificates tar gzip unzip xz util-linux file \
    glibc gcc-libs krb5 icu openssl zlib libx11 libxcb libxkbcommon \
    fontconfig freetype2 mesa libglvnd libdrm libice libsm libxext libxfixes libxi \
    libxrandr libxcursor libxinerama wayland dbus
PACMAN
      ;;
    zypper)
      cat <<'ZYPPER'
Package manager: zypper

Base tools:
  git git-lfs curl tar gzip unzip xz util-linux file

Runtime and desktop libraries:
  glibc libgcc_s1 libicu libopenssl3 libstdc++6 zlib
  libX11-6 libxcb1 libxkbcommon0 fontconfig libfreetype6 Mesa-libGL1
  libICE6 libSM6 libXext6 libXfixes3 libXi6 libXrandr2 libXcursor1
  libXinerama1 libwayland-client0 dbus-1

Example command:
  zypper install git git-lfs curl ca-certificates tar gzip unzip xz util-linux file \
    glibc libgcc_s1 libicu libopenssl3 libstdc++6 zlib \
    libX11-6 libxcb1 libxkbcommon0 fontconfig libfreetype6 Mesa-libGL1 \
    libICE6 libSM6 libXext6 libXfixes3 libXi6 libXrandr2 libXcursor1 \
    libXinerama1 libwayland-client0 dbus-1
ZYPPER
      ;;
    *)
      cat <<'UNKNOWN'
No supported package manager was detected automatically.

You need at least:
  git git-lfs curl tar gzip unzip xz util-linux file
  ICU runtime libraries
  glibc-based Linux desktop runtime libraries for X11 or Wayland

Install the equivalent packages for your distro, then run:
  bash scripts/check-host-chummer6-linux.sh --base "$HOME/chummer6-source-build"
UNKNOWN
      ;;
  esac
}

case "$MANAGER" in
  auto)
    SELECTED_MANAGER="$(detect_manager)"
    ;;
  apt|dnf|pacman|zypper)
    SELECTED_MANAGER="$MANAGER"
    ;;
  *)
    echo "Unsupported manager: $MANAGER" >&2
    usage >&2
    exit 2
    ;;
esac

print_packages "$SELECTED_MANAGER"
