#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

repository_uid=""
repository_gid=""
declare -a repository_group_rows=()
declare -a repository_passwd_rows=()

while (($#)); do
  case "$1" in
    --uid)
      (($# >= 2)) || die "--uid requires a value."
      repository_uid="$2"
      shift 2
      ;;
    --gid)
      (($# >= 2)) || die "--gid requires a value."
      repository_gid="$2"
      shift 2
      ;;
    --group-record)
      (($# >= 2)) || die "--group-record requires a value."
      repository_group_rows+=("$2")
      shift 2
      ;;
    --passwd-record)
      (($# >= 2)) || die "--passwd-record requires a value."
      repository_passwd_rows+=("$2")
      shift 2
      ;;
    *) die "Unsupported identity validator argument: $1" ;;
  esac
done

[[ "$repository_uid" =~ ^[1-9][0-9]*$ ]] || die "the checkout UID must be a non-root decimal identifier."
[[ "$repository_gid" =~ ^[1-9][0-9]*$ ]] || die "the checkout GID must be a non-root decimal identifier."
((${#repository_group_rows[@]} == 1)) || \
  die "the checkout GID does not resolve to exactly one group record."
((${#repository_passwd_rows[@]} == 1)) || \
  die "the checkout UID does not resolve to exactly one passwd record."

repository_group_row="${repository_group_rows[0]}"
if [[ ! "$repository_group_row" =~ ^([^:]+):([^:]*):([0-9]+):([^:]*)$ ]]; then
  die "the checkout GID resolved to a malformed group record."
fi
repository_group="${BASH_REMATCH[1]}"
resolved_group_gid="${BASH_REMATCH[3]}"
[[ "$repository_group" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]] || \
  die "the checkout GID resolved to a non-canonical group name."
[[ "$resolved_group_gid" == "$repository_gid" ]] || \
  die "the checkout GID record does not match the mounted checkout."

repository_passwd_row="${repository_passwd_rows[0]}"
if [[ ! "$repository_passwd_row" =~ ^([^:]+):([^:]*):([0-9]+):([0-9]+):([^:]*):([^:]+):([^:]+)$ ]]; then
  die "the checkout UID resolved to a malformed passwd record."
fi
repository_user="${BASH_REMATCH[1]}"
resolved_passwd_uid="${BASH_REMATCH[3]}"
resolved_passwd_gid="${BASH_REMATCH[4]}"
resolved_passwd_home="${BASH_REMATCH[6]}"
resolved_passwd_shell="${BASH_REMATCH[7]}"
[[ "$repository_user" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]] || \
  die "the checkout UID resolved to a non-canonical user name."
[[ "$resolved_passwd_uid" == "$repository_uid" ]] || \
  die "the checkout UID record does not match the mounted checkout."
[[ "$resolved_passwd_gid" == "$repository_gid" ]] || \
  die "the checkout user primary group differs from the mounted checkout."
[[ "$resolved_passwd_home" == /work/home ]] || \
  die "the checkout user home must be exactly /work/home."
[[ "$resolved_passwd_shell" == /bin/bash ]] || \
  die "the checkout user shell must be exactly /bin/bash."

printf '%s\n' "$repository_user"
