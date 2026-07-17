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

Require identical archive paths, types, modes, links, and regular-file bytes
except for /init. The candidate /init must equal the tested baseline after
applying this experiment's exact tracked fixed-delay reboot patch.
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
for command in awk cmp cpio find gzip grep patch sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
baseline_init_source="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/initramfs/init"
reboot_patch="${experiment_dir}/initramfs/timed-reboot.patch"
readonly EXPECTED_BASELINE_INIT_SHA256=bd7b2679d4e12f6b17d1b5b963dc160b6bb28f956eaba746e8f4102c7ec9f3d9
[[ -s "$baseline_init_source" ]] || die "baseline init source is missing"
[[ -s "$reboot_patch" ]] || die "timed-reboot patch is missing"
[[ "$(sha256sum "$baseline_init_source" | awk '{print $1}')" == "$EXPECTED_BASELINE_INIT_SHA256" ]] || \
	die "baseline init source does not match the tested USB candidate"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-rebootdiag-delta.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "$workdir/baseline" "$workdir/candidate" "$workdir/expected"

gzip -dc "$baseline" | (cd "$workdir/baseline" && cpio -idmu --quiet)
gzip -dc "$candidate" | (cd "$workdir/candidate" && cpio -idmu --quiet)
install -m 0755 "$baseline_init_source" "$workdir/expected/init"
patch_log="${workdir}/patch.log"
if ! patch --fuzz=0 --no-backup-if-mismatch -d "$workdir/expected" -p0 \
	<"$reboot_patch" >"$patch_log" 2>&1; then
	die "timed-reboot patch did not apply exactly"
fi
if grep -Eqi 'offset|fuzz' "$patch_log"; then
	die "timed-reboot patch required offset or fuzz"
fi
rm "$patch_log"

(
	cd "$workdir/baseline"
	find . -printf '%P\t%y\t%m\t%l\n' | sort
) >"$workdir/baseline-tree"
(
	cd "$workdir/candidate"
	find . -printf '%P\t%y\t%m\t%l\n' | sort
) >"$workdir/candidate-tree"
cmp -s "$workdir/baseline-tree" "$workdir/candidate-tree" || \
	die "archive path/type/mode/link manifests differ"

declare -a differences=()
while IFS= read -r relative; do
	if ! cmp -s "$workdir/baseline/$relative" "$workdir/candidate/$relative"; then
		differences+=("$relative")
	fi
done < <(cd "$workdir/baseline" && find . -type f -printf '%P\n' | sort)
[[ "${differences[*]:-}" == init ]] || \
	die "expected only init to differ; got: ${differences[*]:-none}"
cmp -s "$workdir/baseline/init" "$baseline_init_source" || \
	die "baseline archive /init does not match the tested source"
cmp -s "$workdir/candidate/init" "$workdir/expected/init" || \
	die "candidate /init is not exactly baseline plus the tracked patch"
grep -Fqx 'readonly REBOOT_DELAY_SECONDS=10' "$workdir/candidate/init" || \
	die "candidate /init lacks the fixed 10-second delay"
grep -Fqx $'\t/bin/busybox reboot -f' "$workdir/candidate/init" || \
	die "candidate /init lacks the forced BusyBox reboot invocation"

printf 'validation=initramfs-single-file-delta\n'
printf 'archive_path_type_mode_link_manifest_identical=yes\n'
printf 'only_differing_regular_file=init\n'
printf 'baseline_init_matches_tested_source=yes\n'
printf 'candidate_init_matches_tracked_patch=yes\n'
printf 'reboot_delay_seconds=10\n'
printf 'reboot_invocation=/bin/busybox reboot -f\n'
printf 'baseline_sha256=%s\n' "$(sha256sum "$baseline" | awk '{print $1}')"
printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
printf 'hardware_write=none\n'
