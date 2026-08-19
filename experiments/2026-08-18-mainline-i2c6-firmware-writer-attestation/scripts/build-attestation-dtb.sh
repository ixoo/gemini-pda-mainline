#!/usr/bin/env bash

# Derive the exact read-only I2C6 firmware-writer attestation DT.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'Usage: %s --base-dtb FILE --output FILE\n' "$0"; }

base_dtb=
output=
while (($#)); do
	case "$1" in
	--base-dtb) base_dtb=${2:-}; shift 2 ;;
	--output) output=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$base_dtb" && -n "$output" ]] || { usage >&2; exit 2; }
for command in awk chmod dirname dtc fdtget fdtput install mkdir mktemp mv rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mkdir -p -- "$(dirname -- "$output")"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
provider_builder="$repo_root/experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/scripts/build-provider-dtb.sh"
readonly PROVIDER_BUILDER_SHA256=b40340ee88a0346959da9a145530971fdfaad781611a6603154a98f8536c5cd5
readonly PROVIDER_DTB_SHA256=d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48
readonly OUTPUT_DTB_SHA256=80972fc24406d5be8818c891d06fb8ed4d40f2332bd1eda2d8263597029ea683
readonly HANDOFF=/dvfsp-handoff@11015000

[[ -f "$provider_builder" && ! -L "$provider_builder" ]] ||
	die 'provider reference builder is unsafe'
[[ "$(sha256sum "$provider_builder" | awk '{print $1}')" == \
	"$PROVIDER_BUILDER_SHA256" ]] || die 'provider reference builder changed'

temporary_dir="$(mktemp -d "$(dirname -- "$output")/.fwatt-dtb.XXXXXXXX")"
provider_dtb="$temporary_dir/provider.dtb"
candidate_dtb="$temporary_dir/candidate.dtb"
cleanup() { [[ ! -d "${temporary_dir:-}" ]] || rm -rf -- "$temporary_dir"; }
trap cleanup EXIT HUP INT TERM

"$provider_builder" --base-dtb "$base_dtb" --output "$provider_dtb"
[[ "$(sha256sum "$provider_dtb" | awk '{print $1}')" == \
	"$PROVIDER_DTB_SHA256" ]] || die 'provider DT identity changed'
install -m 0600 "$provider_dtb" "$candidate_dtb"

fdtput -tx "$candidate_dtb" "$HANDOFF" reg \
	0 11015000 0 1000 \
	0 100a0000 0 1000 \
	0 1000e000 0 1000
fdtput -ts "$candidate_dtb" "$HANDOFF" reg-names \
	cspm scp-cfg devapc-ao

dtc -q -I dtb -O dtb -o /dev/null "$candidate_dtb"
[[ "$(fdtget -tx "$candidate_dtb" "$HANDOFF" reg)" == \
	'0 11015000 0 1000 0 100a0000 0 1000 0 1000e000 0 1000' ]] ||
	die 'attestation register windows changed'
[[ "$(fdtget -ts "$candidate_dtb" "$HANDOFF" reg-names)" == \
	'cspm scp-cfg devapc-ao' ]] || die 'attestation register names changed'
[[ "$(fdtget -ts "$candidate_dtb" "$HANDOFF" status)" == okay ]] ||
	die 'handoff is not enabled'
[[ "$(fdtget -ts "$candidate_dtb" /scp@10020000 status)" == disabled ]] ||
	die 'SCP closure changed'
[[ "$(sha256sum "$candidate_dtb" | awk '{print $1}')" == \
	"$OUTPUT_DTB_SHA256" ]] || die 'derived attestation DT identity changed'

mv "$candidate_dtb" "$output"
chmod 0600 "$output"
cleanup
temporary_dir=
trap - EXIT HUP INT TERM

printf '%s\n' \
	'validation=mainline-i2c6-firmware-writer-attestation-dtb' \
	"provider_dtb_sha256=$PROVIDER_DTB_SHA256" \
	"output_dtb_sha256=$OUTPUT_DTB_SHA256" \
	'SCP_status=disabled' \
	'attestation_register_reads=bounded' \
	'attestation_register_writes=0' \
	'I2C6_attestation_transfers=0' \
	'CPU8_CPU9_admission=closed' \
	'device_access=none' \
	'hardware_write=none' \
	'result=pass'
