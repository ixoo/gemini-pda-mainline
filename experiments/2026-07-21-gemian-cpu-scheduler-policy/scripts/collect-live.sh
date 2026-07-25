#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --target USER@HOST --output FILE [--identity FILE]\n' "$0" >&2; }

target=
output=
identity=artifacts/credentials/gemini_ed25519
while (($#)); do
	case "$1" in
	--target|--output|--identity)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--target) target=$2 ;;
		--output) output=$2 ;;
		--identity) identity=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$target" =~ ^[A-Za-z_][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || \
	die 'target must be a simple USER@HOST value'
[[ -n "$output" && ! -e "$output" && ! -L "$output" ]] || \
	die 'output must be a new path'
[[ -f "$identity" && ! -L "$identity" ]] || die 'identity is not a regular file'
[[ "$(stat -f '%Lp' "$identity")" == 600 ]] || die 'identity mode must be 0600'
output_parent=$(dirname -- "$output")
[[ -d "$output_parent" && ! -L "$output_parent" ]] || die 'output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
partial="$output.partial"
[[ ! -e "$partial" && ! -L "$partial" ]] || die 'partial output already exists'
cleanup() { [[ ! -f "$partial" ]] || rm -f -- "$partial"; }
trap cleanup EXIT

ssh \
	-i "$identity" \
	-o IdentitiesOnly=yes \
	-o IdentityAgent=none \
	-o BatchMode=yes \
	-o ConnectTimeout=5 \
	"$target" 'sudo -n sh -s' \
	<"$script_dir/remote-probe.sh" >"$partial"
chmod 0600 "$partial"
mv "$partial" "$output"
trap - EXIT

printf 'capture=%s\n' "$output"
printf 'bytes=%s\n' "$(wc -c <"$output" | tr -d ' ')"
printf 'sha256=%s\n' "$(shasum -a 256 "$output" | awk '{print $1}')"
printf 'device_writes=none\n'
