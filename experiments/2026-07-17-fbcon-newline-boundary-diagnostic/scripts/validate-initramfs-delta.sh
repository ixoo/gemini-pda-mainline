#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	echo "error: $*" >&2
	exit 2
}

baseline=
candidate=
while (($#)); do
	case "$1" in
		--baseline)
			(($# >= 2)) || die "--baseline requires FILE"
			baseline=$2
			shift 2
			;;
		--candidate)
			(($# >= 2)) || die "--candidate requires FILE"
			candidate=$2
			shift 2
			;;
		-h|--help)
			echo "usage: validate-initramfs-delta.sh --baseline FILE --candidate FILE" >&2
			exit 0
			;;
		*)
			die "unknown option: $1"
			;;
	esac
done

[[ -s "$baseline" ]] || die "baseline initramfs is missing"
[[ -s "$candidate" ]] || die "candidate initramfs is missing"
for command in awk cmp cpio find gzip install sha256sum sort touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
candidate_init_source="${experiment_dir}/initramfs/init"
baseline_init_source="${repo_root}/experiments/2026-07-16-fbcon-refresh-timing-diagnostic/initramfs/init"
contract_validator="${script_dir}/validate-init-contract.sh"
readonly EXPECTED_J_INITRAMFS_SHA256=85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
readonly EXPECTED_J_INIT_SHA256=f918e03f1df6c7e50b5673eba99d2dbe48e438e9035453908231c28c94d5d6d5
readonly EXPECTED_K_INIT_SHA256=c1b3cfa8bcda856d4afe3b54cbdef947b055e7c045b7c311af286ba51b5cd58b
readonly EXPECTED_K_INITRAMFS_SHA256=c6356f895579b8d0cac516f3a6618ab70d7d4bc33c8c15cc052a71445607dda8
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_J_INITRAMFS_SHA256" ]] || die "baseline is not exact Candidate J initramfs"
[[ "$(sha256sum "$baseline_init_source" | awk '{print $1}')" == \
	"$EXPECTED_J_INIT_SHA256" ]] || die "tracked Candidate I/J /init bytes changed"
[[ "$(sha256sum "$candidate_init_source" | awk '{print $1}')" == \
	"$EXPECTED_K_INIT_SHA256" ]] || die "tracked Candidate K /init bytes changed"
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == \
	"$EXPECTED_K_INITRAMFS_SHA256" ]] || \
	die "candidate is not the pinned Candidate K initramfs"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-k-initramfs-delta.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "${workdir}/baseline" "${workdir}/candidate" "${workdir}/expected"
gzip -dc "$baseline" | (cd "${workdir}/baseline" && cpio -idmu --quiet)
gzip -dc "$candidate" | (cd "${workdir}/candidate" && cpio -idmu --quiet)
gzip -dc "$baseline" | (cd "${workdir}/expected" && cpio -idmu --quiet)

cmp -s "${workdir}/baseline/init" "$baseline_init_source" || \
	die "baseline archive /init is not exact Candidate I/J"
cmp -s "${workdir}/candidate/init" "$candidate_init_source" || \
	die "candidate archive /init does not match tracked Candidate K"
"$contract_validator" --init "${workdir}/candidate/init" >/dev/null

(
	cd "${workdir}/baseline"
	find . -printf '%P\t%y\t%m\t%l\n' | sort
) >"${workdir}/baseline-tree"
(
	cd "${workdir}/candidate"
	find . -printf '%P\t%y\t%m\t%l\n' | sort
) >"${workdir}/candidate-tree"
cmp -s "${workdir}/baseline-tree" "${workdir}/candidate-tree" || \
	die "archive path/type/mode/link manifests differ"

declare -a differences=()
while IFS= read -r relative; do
	if ! cmp -s "${workdir}/baseline/$relative" "${workdir}/candidate/$relative"; then
		differences+=("$relative")
	fi
done < <(cd "${workdir}/baseline" && find . -type f -printf '%P\n' | sort)
[[ "${differences[*]:-}" == init ]] || \
	die "expected only init bytes to differ; got: ${differences[*]:-none}"

install -m 0755 "$candidate_init_source" "${workdir}/expected/init"
find "${workdir}/expected" -exec touch -h -d @0 {} +
(
	cd "${workdir}/expected"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"${workdir}/expected.img"
cmp -s "$candidate" "${workdir}/expected.img" || \
	die "candidate is not the canonical deterministic Candidate K archive"

printf 'validation=fbcon-newline-boundary-initramfs-delta\n'
printf 'baseline_sha256=%s\n' "$(sha256sum "$baseline" | awk '{print $1}')"
printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
printf 'archive_path_type_mode_link_manifest_identical=yes\n'
printf 'only_differing_regular_file=init\n'
printf 'canonical_archive_bytes=yes\n'
printf 'marker=GEMINI_FBCON_BOUNDARY_20260717_K\n'
printf 'phase1=20x-one-second-fixed-width-leading-cr-no-newline\n'
printf 'phase2=transition-plus-12x-one-second-newline-terminated\n'
printf 'final_state=static-hold-no-further-console-writes\n'
printf 'tracked_init_forbidden_storage_fbdev_raw_memory_mmio_i2c_reset_watchdog_network_usb_control_access=none\n'
printf 'build_hardware_write=none\n'
