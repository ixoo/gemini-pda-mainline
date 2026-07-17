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

Require a byte-deterministic exact-H archive derivative whose only path or
content delta is tracked /init, then enforce the 60-second tty refresh and
static-hold safety contract. This validator has no hardware interface.
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
for command in awk cmp cpio find grep gzip install sha256sum sort tail touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
candidate_init_source="${experiment_dir}/initramfs/init"
baseline_init_source="${repo_root}/experiments/2026-07-16-fbcon-text-diagnostic/initramfs/init"
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=8dc85151bececf297f99b6f22c87316a54d0fa062e29c2c64ad00334b7ad0956
readonly EXPECTED_BASELINE_INIT_SHA256=c81247da5b39ed27daae1afc0fa988f5375bc493eccb6d2e5309389c389e85bb
readonly EXPECTED_CANDIDATE_INIT_SHA256=f918e03f1df6c7e50b5673eba99d2dbe48e438e9035453908231c28c94d5d6d5
readonly EXPECTED_CANDIDATE_INITRAMFS_SHA256=85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
[[ -s "$candidate_init_source" ]] || die "tracked Candidate I /init is missing"
[[ -s "$baseline_init_source" ]] || die "tracked Candidate G/H /init is missing"
[[ "$(sha256sum "$candidate_init_source" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INIT_SHA256" ]] || \
	die "tracked Candidate I /init no longer matches its pinned bytes"
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || \
	die "baseline initramfs is not exact Candidate H"
[[ "$(sha256sum "$baseline_init_source" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INIT_SHA256" ]] || \
	die "tracked Candidate G/H /init no longer matches its pinned bytes"
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INITRAMFS_SHA256" ]] || \
	die "candidate initramfs does not match its pinned bytes"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-fbcon-refresh-delta.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "$workdir/baseline" "$workdir/candidate" "$workdir/expected"
gzip -dc "$baseline" | (cd "$workdir/baseline" && cpio -idmu --quiet)
gzip -dc "$candidate" | (cd "$workdir/candidate" && cpio -idmu --quiet)
gzip -dc "$baseline" | (cd "$workdir/expected" && cpio -idmu --quiet)

cmp -s "$workdir/baseline/init" "$baseline_init_source" || \
	die "baseline archive /init is not exact Candidate G/H"
cmp -s "$workdir/candidate/init" "$candidate_init_source" || \
	die "candidate archive /init does not match tracked Candidate I"

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
	die "expected only init bytes to differ; got: ${differences[*]:-none}"

# Reconstruct the only permitted deterministic archive and require the entire
# compressed candidate to match it, including newc metadata, order and gzip
# header/trailer bytes.
install -m 0755 "$candidate_init_source" "$workdir/expected/init"
find "$workdir/expected" -exec touch -h -d @0 {} +
(
	cd "$workdir/expected"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/expected.img"
cmp -s "$candidate" "$workdir/expected.img" || \
	die "candidate is not the canonical deterministic Candidate I archive"

init="$workdir/candidate/init"
grep -Fqx 'readonly MARKER="GEMINI_FBCON_REFRESH_20260716_I"' "$init" || \
	die "candidate /init lacks the exact unique marker"
grep -Fqx 'readonly LAST_TICK=60' "$init" || \
	die "candidate /init lacks the exact 60-tick bound"
grep -Fqx 'tick=0' "$init" || \
	die "candidate /init must begin elapsed-time accounting at zero"
grep -Fqx $'while [ "$tick" -lt "$LAST_TICK" ]; do' "$init" || \
	die "candidate /init lacks the exact bounded timing loop"
grep -Fqx $'\tfor output in /dev/tty0 /dev/ttyS0; do' "$init" || \
	die "candidate /init does not target exactly tty0 and ttyS0"
grep -Fqx $'\ttick=$((tick + 1))' "$init" || \
	die "candidate /init lacks the one-second tick increment"
grep -Fqx $'\temit "$MARKER T+$tick_label ACTIVE REFRESH $tick_label/60"' "$init" || \
	die "candidate /init lacks the numbered active-refresh line"
grep -Fqx $'emit "$MARKER T+60 STATIC HOLD; NO FURTHER CONSOLE WRITES"' "$init" || \
	die "candidate /init lacks the final static-hold line"
[[ "$(grep -Ec '^[[:space:]]*sleep 1$' "$init")" == 1 ]] || \
	die "candidate /init must contain exactly one bounded one-second sleep site"
[[ "$(grep -Ec '^[[:space:]]*sleep 3600$' "$init")" == 2 ]] || \
	die "candidate /init must contain only the two failure/final hold sleep sites"
sleep_line="$(grep -nF $'\tsleep 1' "$init")"
increment_line="$(grep -nF $'\ttick=$((tick + 1))' "$init")"
active_emit_line="$(grep -nF $'\temit "$MARKER T+$tick_label ACTIVE REFRESH $tick_label/60"' "$init")"
sleep_line=${sleep_line%%:*}
increment_line=${increment_line%%:*}
active_emit_line=${active_emit_line%%:*}
((sleep_line < increment_line && increment_line < active_emit_line)) || \
	die "each numbered line must follow its one-second delay and tick increment"
last_emit_line="$(grep -nE '^[[:space:]]*emit ' "$init" | tail -n 1)"
[[ "$last_emit_line" == *$'emit "$MARKER T+60 STATIC HOLD; NO FURTHER CONSOLE WRITES"' ]] || \
	die "static hold is not the final console-write call"

grep -Fqx 'mount -t proc -o ro,nosuid,nodev,noexec proc /proc 2>/dev/null || true' \
	"$init" || die "candidate /init must mount procfs read-only"
grep -Fqx 'mount -t sysfs -o ro,nosuid,nodev,noexec sysfs /sys 2>/dev/null || true' \
	"$init" || die "candidate /init must mount sysfs read-only"
if grep -Eqi '/dev/fb|/dev/mmc|/dev/block|/dev/mem|/dev/kmem|/proc/sysrq-trigger|/sys/class/net|/proc/net|(^|[^[:alnum:]_])(dd|reboot|poweroff|halt|shutdown|reset|kexec|watchdog|ifconfig|ip|route|nc|telnet|wget|tftp|udhcpc)([^[:alnum:]_]|$)' "$init"; then
	die "candidate /init contains forbidden framebuffer, storage, network, raw-memory, or reset access"
fi

printf 'validation=fbcon-refresh-timing-initramfs-delta\n'
printf 'baseline_sha256=%s\n' "$(sha256sum "$baseline" | awk '{print $1}')"
printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
printf 'archive_path_type_mode_link_manifest_identical=yes\n'
printf 'only_differing_regular_file=init\n'
printf 'canonical_archive_bytes=yes\n'
printf 'marker=GEMINI_FBCON_REFRESH_20260716_I\n'
printf 'tick_sequence=T+01..T+60\n'
printf 'tick_interval_seconds=1\n'
printf 'final_state=static-hold-no-further-console-writes\n'
printf 'raw_framebuffer_access=none\n'
printf 'storage_access=none\n'
printf 'runtime_networking=none\n'
printf 'runtime_reset_request=none\n'
printf 'build_hardware_write=none\n'
