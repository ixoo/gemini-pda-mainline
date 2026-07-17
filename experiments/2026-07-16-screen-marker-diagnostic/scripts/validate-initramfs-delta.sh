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

Validate the screen-marker initramfs against the exact timed-reboot baseline.
Only /init, /screen-marker.raw, and the BusyBox dd/wc links may differ.
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
for command in awk cmp cp cpio find grep gzip python3 readlink sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
candidate_init_source="${experiment_dir}/initramfs/init"
marker_validator="${script_dir}/generate-screen-marker.py"
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=8a63939caf76473ad8d688e923155d2b9800bf25cd2017c36acafb08a11bb71b
[[ -s "$candidate_init_source" ]] || die "candidate init source is missing"
[[ -x "$marker_validator" ]] || die "marker validator is not executable"
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || \
	die "baseline initramfs is not the exact timed-reboot image"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-screen-marker-delta.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "$workdir/baseline" "$workdir/candidate"

gzip -dc "$baseline" | (cd "$workdir/baseline" && cpio -idmu --quiet)
gzip -dc "$candidate" | (cd "$workdir/candidate" && cpio -idmu --quiet)

(
	cd "$workdir/baseline"
	find . -printf '%P\t%y\t%m\t%l\n' | sort
) >"$workdir/baseline-tree"
(
	cd "$workdir/candidate"
	find . -printf '%P\t%y\t%m\t%l\n' | sort
) >"$workdir/candidate-tree"

cp "$workdir/baseline-tree" "$workdir/expected-tree"
{
	printf 'bin/dd\tl\t777\tbusybox\n'
	printf 'bin/wc\tl\t777\tbusybox\n'
	printf 'screen-marker.raw\tf\t644\t\n'
} >>"$workdir/expected-tree"
sort -o "$workdir/expected-tree" "$workdir/expected-tree"
# /init exists in both trees with the same type and mode; its bytes are checked
# separately below.
cmp -s "$workdir/expected-tree" "$workdir/candidate-tree" || \
	die "archive path/type/mode/link delta is outside init, marker, dd, and wc"

cmp -s "$workdir/candidate/init" "$candidate_init_source" || \
	die "candidate /init does not match the tracked source"
[[ "$(readlink "$workdir/candidate/bin/dd")" == busybox ]] || \
	die "candidate dd link does not target BusyBox"
[[ "$(readlink "$workdir/candidate/bin/wc")" == busybox ]] || \
	die "candidate wc link does not target BusyBox"
python3 "$marker_validator" --validate "$workdir/candidate/screen-marker.raw" \
	>"$workdir/marker-validation"

while IFS= read -r relative; do
	case "$relative" in
		init) continue ;;
	esac
	cmp -s "$workdir/baseline/$relative" "$workdir/candidate/$relative" || \
		die "unexpected regular-file delta: $relative"
done < <(cd "$workdir/baseline" && find . -type f -printf '%P\n' | sort)

grep -Fqx 'readonly FRAME_BYTES=9400320' "$workdir/candidate/init" || \
	die "candidate /init lacks the bounded frame size"
framebuffer_write="dd if=\"\$MARKER_FILE\" of=\"\$FRAMEBUFFER\" bs=4352 count=2160"
[[ "$(grep -Fc "$framebuffer_write" "$workdir/candidate/init")" == 1 ]] || \
	die "candidate /init must contain exactly one bounded framebuffer write"
if grep -Eq '(^|[[:space:]])(reboot|poweroff)([[:space:]]|$)|/dev/mmc|/dev/mem' \
	"$workdir/candidate/init"; then
	die "candidate /init contains a forbidden reset, storage, or raw-memory path"
fi

printf 'validation=screen-marker-initramfs-delta\n'
printf 'baseline_sha256=%s\n' "$(sha256sum "$baseline" | awk '{print $1}')"
printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
printf 'changed_regular_files=init\n'
printf 'added_regular_files=screen-marker.raw\n'
printf 'added_symlinks=bin/dd,bin/wc\n'
printf 'all_other_paths_and_bytes_identical=yes\n'
printf 'marker_pattern_validated=yes\n'
printf 'framebuffer_write_bytes=9400320\n'
printf 'storage_access=none\n'
printf 'build_hardware_write=none\n'
