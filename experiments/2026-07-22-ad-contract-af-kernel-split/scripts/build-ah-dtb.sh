#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --ad-dtb FILE --output FILE\n' "$0" >&2; }

ad_dtb=
output=
while (($#)); do
	case "$1" in
	--ad-dtb|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--ad-dtb) ad_dtb=$2 ;;
		--output) output=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$ad_dtb" && -n "$output" ]] || { usage; exit 2; }
for command in awk chmod dirname fdtget fdtput install mktemp mv python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$ad_dtb" && ! -L "$ad_dtb" && -s "$ad_dtb" ]] || \
	die 'Candidate AD DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output DTB'
output_parent="$(dirname -- "$output")"
[[ -d "$output_parent" && ! -L "$output_parent" ]] || die 'output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-dtb-delta.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] || \
	die 'DT semantic validator is missing or unsafe'

readonly AD_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
[[ "$(sha256sum "$ad_dtb" | awk '{ print $1 }')" == "$AD_DTB_SHA256" ]] || \
	die 'exact hardware-passed Candidate AD DTB changed'
for cpu in /cpus/cpu@200 /cpus/cpu@201; do
	[[ "$(fdtget -t s "$ad_dtb" "$cpu" compatible)" == arm,cortex-a72 ]] || \
		die "Candidate AD A72 identity changed: $cpu"
	[[ "$(fdtget -t s "$ad_dtb" "$cpu" enable-method)" == psci ]] || \
		die "Candidate AD enable-method changed: $cpu"
done

temporary="$(mktemp "$output_parent/.candidate-ah-dtb.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
install -m 0600 "$ad_dtb" "$temporary"
for cpu in /cpus/cpu@200 /cpus/cpu@201; do
	fdtput -t s "$temporary" "$cpu" enable-method mediatek,mt6797-psci
done
python3 "$validator" --ad "$ad_dtb" --candidate "$temporary"
built_sha256="$(sha256sum "$temporary" | awk '{ print $1 }')"
chmod 0600 "$temporary"
mv -n "$temporary" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$temporary" ]] || \
	die 'exclusive DTB publication failed'
temporary=
trap - EXIT
printf 'validation=candidate-ah-ad-contract-dtb-built\n'
printf 'output=%s\nsha256=%s\n' "$output" "$built_sha256"
printf 'changed_properties=cpu8-enable-method,cpu9-enable-method\n'
printf 'active_a72_operation=none\nraw_framebuffer_write=none\ndevice_access=none\n'
