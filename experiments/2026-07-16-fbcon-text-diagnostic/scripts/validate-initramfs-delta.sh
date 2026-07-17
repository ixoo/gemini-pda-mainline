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
usage: validate-initramfs-delta.sh --baseline FILE --candidate FILE

Require an exact Candidate F archive minus screen-marker.raw, bin/dd and
bin/wc, with only /init changed to the tracked Candidate G source.
EOF
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
			usage
			exit 0
			;;
		*)
			usage
			die "unknown option: $1"
			;;
	esac
done

[[ -s "$baseline" ]] || die "baseline initramfs is missing: $baseline"
[[ -s "$candidate" ]] || die "candidate initramfs is missing: $candidate"
for command in awk cmp cpio find grep gzip sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
candidate_init_source="${experiment_dir}/initramfs/init"
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=1c76b34ea58956ffd8b97a640b76788b9f7e1ab92204a9881ad031bd7fe6c72c
[[ -s "$candidate_init_source" ]] || die "candidate init source is missing"
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || \
	die "baseline initramfs is not exact Candidate F"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-fbcon-text-delta.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "$workdir/baseline" "$workdir/candidate"
gzip -dc "$baseline" | (cd "$workdir/baseline" && cpio -idmu --quiet)
gzip -dc "$candidate" | (cd "$workdir/candidate" && cpio -idmu --quiet)

(
	cd "$workdir/baseline"
	find . -printf '%P\t%y\t%m\t%l\n' | \
		awk -F '\t' '$1 != "screen-marker.raw" && $1 != "bin/dd" && $1 != "bin/wc"' | \
		sort
) >"$workdir/expected-tree"
(
	cd "$workdir/candidate"
	find . -printf '%P\t%y\t%m\t%l\n' | sort
) >"$workdir/candidate-tree"
cmp -s "$workdir/expected-tree" "$workdir/candidate-tree" || \
	die "archive tree differs outside the allowlisted removals and /init bytes"

cmp -s "$workdir/candidate/init" "$candidate_init_source" || \
	die "candidate /init does not match the tracked source"
while IFS= read -r relative; do
	case "$relative" in
		init|screen-marker.raw) continue ;;
	esac
	cmp -s "$workdir/baseline/$relative" "$workdir/candidate/$relative" || \
		die "unexpected regular-file delta: $relative"
done < <(cd "$workdir/baseline" && find . -type f -printf '%P\n' | sort)

init="$workdir/candidate/init"
grep -Fqx 'readonly MARKER="GEMINI_FBCON_TEXT_20260716_G"' "$init" || \
	die "candidate /init lacks its exact visible marker"
grep -Fqx 'mount -t sysfs -o ro,nosuid,nodev,noexec sysfs /sys 2>/dev/null || true' \
	"$init" || die "candidate /init must keep sysfs read-only"
grep -Fq 'RAW FRAMEBUFFER WRITE: NONE' "$init" || \
	die "candidate /init does not state the no-write contract"
grep -Fq 'STATE: HOLDING; HEARTBEAT UPDATES EVERY 30 SECONDS' "$init" || \
	die "candidate /init lacks the persistent hold signal"
grep -Fq '/dev/tty0 /dev/ttyS0' "$init" || \
	die "candidate /init lacks both diagnostic console targets"
if grep -Eqi '/dev/fb|screen-marker|(^|[^[:alnum:]_])(dd|reboot|poweroff|halt)([^[:alnum:]_]|$)|/dev/mmc|/dev/mem' \
	"$init"; then
	die "candidate /init contains forbidden framebuffer, reset, storage, or raw-memory access"
fi

printf 'validation=fbcon-text-initramfs-delta\n'
printf 'baseline_sha256=%s\n' "$(sha256sum "$baseline" | awk '{print $1}')"
printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
printf 'changed_regular_files=init\n'
printf 'removed_regular_files=screen-marker.raw\n'
printf 'removed_symlinks=bin/dd,bin/wc\n'
printf 'all_other_paths_and_bytes_identical=yes\n'
printf 'sysfs_read_only=yes\n'
printf 'raw_framebuffer_access=none\n'
printf 'storage_access=none\n'
printf 'runtime_reset_request=none\n'
printf 'build_hardware_write=none\n'
