#!/usr/bin/env bash
# shellcheck disable=SC2016

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

Require an exact Candidate M archive derivative whose only archive delta is
tracked Candidate N /init, then enforce its watchdog-first, CPU1-only sysfs
write contract. This validator has no hardware interface.
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
for command in awk cmp cpio dirname find grep gzip install mkdir mktemp rm sha256sum sort touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
candidate_init_source="${experiment_dir}/initramfs/init"
baseline_init_source="${repo_root}/experiments/2026-07-18-watchdog-registration-diagnostic/initramfs/init"
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=e0edeceb127e08cd0b01749e289474479ccebe8f33995d39014d7dcf8c5b25fc
readonly EXPECTED_BASELINE_INIT_SHA256=005dddd59b1918d18ff03d15671ab84b2453c67bc6db911dde6fdaded47e54d0
readonly EXPECTED_CANDIDATE_INIT_SHA256=d1c312dff2c7c2afea3969b937cc0f5b524da73c95f8cd0139212820b705a440
[[ -s "$candidate_init_source" ]] || die "tracked Candidate N /init is missing"
[[ -s "$baseline_init_source" ]] || die "tracked Candidate M /init is missing"
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || die "baseline is not exact Candidate M"
[[ "$(sha256sum "$baseline_init_source" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INIT_SHA256" ]] || die "tracked Candidate M /init changed"
[[ "$(sha256sum "$candidate_init_source" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INIT_SHA256" ]] || die "tracked Candidate N /init changed"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-cpu1-online-delta.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "$workdir/baseline" "$workdir/candidate" "$workdir/expected"
gzip -dc "$baseline" | (cd "$workdir/baseline" && cpio -idmu --quiet)
gzip -dc "$candidate" | (cd "$workdir/candidate" && cpio -idmu --quiet)
gzip -dc "$baseline" | (cd "$workdir/expected" && cpio -idmu --quiet)

cmp -s "$workdir/baseline/init" "$baseline_init_source" || \
	die "baseline archive /init is not exact Candidate M"
cmp -s "$workdir/candidate/init" "$candidate_init_source" || \
	die "candidate archive /init does not match tracked Candidate N"
for runtime_command in busybox cat dmesg grep mount sh sleep uname; do
	[[ -x "$workdir/candidate/bin/$runtime_command" ]] || \
		die "runtime command is unavailable in Candidate M archive: $runtime_command"
done
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

install -m 0755 "$candidate_init_source" "$workdir/expected/init"
find "$workdir/expected" -exec touch -h -d @0 {} +
(
	cd "$workdir/expected"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/expected.img"
cmp -s "$candidate" "$workdir/expected.img" || \
	die "candidate is not the canonical deterministic Candidate N archive"

init="$workdir/candidate/init"
grep -Fqx 'readonly MARKER="GEMINI_CPU1_ONLINE_20260718_N"' "$init" || \
	die "candidate /init lacks the exact unique marker"
grep -Fqx 'readonly CPU1_ONLINE_PATH=/sys/devices/system/cpu/cpu1/online' "$init" || \
	die "CPU1 online target is not exact"
grep -Fqx 'readonly WATCHDOG_TIMEOUT_SECONDS=31' "$init" || \
	die "watchdog timeout must remain 31 seconds"
grep -Fqx 'readonly WATCHDOG_FAILURE_SECONDS=40' "$init" || \
	die "watchdog failure boundary must remain 40 seconds"
grep -Fqx $'if exec 3>/dev/watchdog0; then' "$init" || \
	die "candidate must open watchdog fd 3 exactly once"
[[ "$(grep -Fxc $'if exec 3>/dev/watchdog0; then' "$init")" == 1 ]] || \
	die "watchdog may be opened at exactly one source site"
grep -Fqx $'\tif printf '\''.'\'' >&3; then' "$init" || \
	die "candidate must send one ownership-handoff ping"
[[ "$(grep -Foc '>&3' "$init")" == 1 ]] || \
	die "watchdog fd 3 may have exactly one write redirection"
grep -Fqx 'if printf '\''1\n'\'' >"$CPU1_ONLINE_PATH" 2>"$CPU1_ERROR_FILE"; then' "$init" || \
	die "candidate must issue one exact CPU1-online write"
[[ "$(grep -Foc '>"$CPU1_ONLINE_PATH"' "$init")" == 1 ]] || \
	die "CPU1 online target may have exactly one write redirection"

watchdog_open_line="$(grep -nFx 'if exec 3>/dev/watchdog0; then' "$init" | awk -F: '{print $1}')"
cpu_request_line="$(grep -nFx 'record "$MARKER cpu1_request=begin target=cpu1 requested_state=online"' "$init" | awk -F: '{print $1}')"
cpu_write_line="$(grep -nFx 'if printf '\''1\n'\'' >"$CPU1_ONLINE_PATH" 2>"$CPU1_ERROR_FILE"; then' "$init" | awk -F: '{print $1}')"
[[ "$watchdog_open_line" =~ ^[0-9]+$ && "$cpu_request_line" =~ ^[0-9]+$ && \
	"$cpu_write_line" =~ ^[0-9]+$ && "$watchdog_open_line" -lt "$cpu_request_line" && \
	"$cpu_request_line" -lt "$cpu_write_line" ]] || \
	die "watchdog arm, request marker, and CPU1 write order is invalid"

grep -Fqx 'if mount -t proc -o ro,nosuid,nodev,noexec proc /proc 2>/dev/null; then' \
	"$init" || die "procfs must be mounted read-only"
grep -Fqx 'if mount -t sysfs -o rw,nosuid,nodev,noexec sysfs /sys 2>/dev/null; then' \
	"$init" || die "sysfs must be mounted with the exact CPU-hotplug policy"
[[ "$(grep -Ec '^[[:space:]]*((if[[:space:]]+!?[[:space:]]*)?mount)[[:space:]]' "$init")" == 3 ]] || \
	die "init may mount only devtmpfs, procfs and sysfs"
grep -Fq '/sys/firmware/devicetree/base/cpus/cpu@1' "$init" || \
	die "live CPU1 DT gate is missing"
grep -Fq 'cpu1_compatible" = arm,cortex-a53' "$init" || \
	die "live CPU1 compatible gate is missing"
grep -Fq 'cpu1_enable_method" = psci' "$init" || \
	die "live CPU1 PSCI gate is missing"
grep -Fq '/sys/firmware/devicetree/base/watchdog@10007000' "$init" || \
	die "live no-IRQ watchdog gate is missing"
grep -Fq 'record_cpu_state pre-request' "$init" || die "pre-request CPU masks are missing"
grep -Fq 'record_cpu_state post-request' "$init" || die "post-request CPU masks are missing"
grep -Fq 'cpu1_of_node=' "$init" || die "live CPU1 of_node evidence is missing"
grep -Fq 'record_cpu1_stat_samples' "$init" || die "CPU1 accounting samples are missing"
grep -Fq 'cpu1_accounting=advanced' "$init" || die "CPU1 accounting decision is missing"
grep -Fq 'cpu1_result=online SUCCESS' "$init" || die "CPU1 success marker is missing"
grep -Fq 'cpu1_request=returned status=' "$init" || die "request return marker is missing"
grep -Fq 'wait_for_watchdog_reset cpu1-online' "$init" || \
	die "successful CPU1 path must retain watchdog recovery"
grep -Fq '/bin/busybox readlink' "$init" || \
	die "readlink must use the available BusyBox binary"
grep -Fq '/bin/busybox tr -d' "$init" || \
	die "tr must use the available BusyBox binary"
grep -Fq '/bin/busybox tail -n 20' "$init" || \
	die "CPU log tail must use the available BusyBox binary"
grep -Fq '/bin/busybox tail -n 4' "$init" || \
	die "error tail must use the available BusyBox binary"
if grep -Eq '^[[:space:]]*(tr|readlink|tail)[[:space:]]' "$init"; then
	die "unqualified applet lacks an initramfs symlink"
fi

if grep -Eqi '/dev/(fb|mmc|block|mem|kmem|i2c)|/proc/sysrq-trigger|/sys/class/net|(^|[^[:alnum:]_])(dd|devmem|reboot|poweroff|halt|shutdown|kexec|i2cget|i2cset|i2cdump|mknod|sync|ip|ifconfig|route|nc|telnet|wget|tftp|udhcpc)([^[:alnum:]_]|$)' "$init"; then
	die "candidate /init contains forbidden storage, framebuffer, raw-memory, I2C, reset, or network access"
fi
if grep -Eqi 'exec[[:space:]]+/bin/(ba)?sh|nc[^#]*-e[[:space:]]+/bin/(ba)?sh|(^|[^[:alnum:]_])(ash|bash|sh)[[:space:]]+-[cil]' "$init"; then
	die "candidate /init must not expose an interactive shell"
fi

candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
printf 'validation=cpu1-online-initramfs-delta\n'
printf 'baseline_sha256=%s\n' "$EXPECTED_BASELINE_INITRAMFS_SHA256"
printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'archive_path_type_mode_link_manifest_identical=yes\n'
printf 'only_differing_regular_file=init\n'
printf 'canonical_archive_bytes=yes\n'
printf 'marker=GEMINI_CPU1_ONLINE_20260718_N\n'
printf 'watchdog_action=open-fd3,one-handoff-ping,before-cpu1,no-further-pings\n'
printf 'sysfs_write=/sys/devices/system/cpu/cpu1/online:1\n'
printf 'other_sysfs_write=none\n'
printf 'storage_access=none\n'
printf 'runtime_networking=none\n'
printf 'generic_reset_command=none\n'
printf 'hardware_write=cpu1-standard-hotplug-control-only\n'
