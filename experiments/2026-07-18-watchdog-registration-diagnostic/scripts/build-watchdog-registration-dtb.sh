#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	echo "error: $*" >&2
	exit 2
}

usage() {
	cat >&2 <<'EOF'
usage: build-watchdog-registration-dtb.sh --baseline DTB --output DTB

Derive Candidate M from exact Candidate L by deleting only the optional
watchdog bark interrupt. This command has no device or flashing interface.
EOF
}

baseline=
output=
while (($#)); do
	case "$1" in
		--baseline)
			(($# >= 2)) || die "--baseline requires DTB"
			baseline=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || die "--output requires DTB"
			output=$2
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			die "unknown option: $1"
			;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ "$(uname -m)" == aarch64 ]] || die "expected an aarch64 development VM"
[[ -s "$baseline" ]] || die "exact Candidate L DTB is required"
[[ -n "$output" ]] || die "--output is required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
for command in awk cat dirname fdtput install mkdir mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

readonly EXPECTED_BASELINE_DTB_SHA256=73a0c1913beaf41473accfcc6765407ffe11acc56c6ec0ff3a787abc29f00cae
readonly EXPECTED_CANDIDATE_DTB_SHA256=c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_DTB_SHA256" ]] || die "baseline is not exact Candidate L"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="${script_dir}/validate-watchdog-registration-dtb.py"
[[ -s "$validator" ]] || die "DTB validator is missing: $validator"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.watchdog-registration-dtb.XXXXXX")"
temporary="${workdir}/candidate.dtb"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

install -m 0600 "$baseline" "$temporary"
fdtput -d "$temporary" /watchdog@10007000 interrupts
python3 "$validator" --baseline "$baseline" --candidate "$temporary" \
	>"${workdir}/validation.txt"
candidate_sha256="$(sha256sum "$temporary" | awk '{print $1}')"
[[ "$candidate_sha256" == "$EXPECTED_CANDIDATE_DTB_SHA256" ]] || \
	die "Candidate M DTB does not match its pinned bytes"
install -m 0600 "$temporary" "$output"

cat "${workdir}/validation.txt"
printf 'output=%s\n' "$output"
printf 'baseline_sha256=%s\n' "$EXPECTED_BASELINE_DTB_SHA256"
printf 'output_sha256=%s\n' "$candidate_sha256"
printf 'build_hardware_write=none\nflash=none\n'
