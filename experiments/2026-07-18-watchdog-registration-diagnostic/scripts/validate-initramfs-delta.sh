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

Require an exact Candidate L archive derivative whose only archive delta is
tracked Candidate M /init, then enforce its read-only probe and single-stage
watchdog-expiry contract. This validator has no hardware interface.
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
baseline_init_source="${repo_root}/experiments/2026-07-17-uart-pstore-observability/initramfs/init"
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=52dd9145b3d85d8f73990f5798b494293aab17d86a066f79f33274207986de32
readonly EXPECTED_BASELINE_INIT_SHA256=70f4074656acd073e8146d25047ad7e3af09674bb67b6801418e04cdf8573130
readonly EXPECTED_CANDIDATE_INIT_SHA256=005dddd59b1918d18ff03d15671ab84b2453c67bc6db911dde6fdaded47e54d0
readonly EXPECTED_CANDIDATE_INITRAMFS_SHA256=e0edeceb127e08cd0b01749e289474479ccebe8f33995d39014d7dcf8c5b25fc
[[ -s "$candidate_init_source" ]] || die "tracked Candidate M /init is missing"
[[ -s "$baseline_init_source" ]] || die "tracked Candidate L /init is missing"
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || die "baseline is not exact Candidate L"
[[ "$(sha256sum "$baseline_init_source" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INIT_SHA256" ]] || die "tracked Candidate L /init changed"
[[ "$(sha256sum "$candidate_init_source" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INIT_SHA256" ]] || die "tracked Candidate M /init changed"
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INITRAMFS_SHA256" ]] || \
	die "candidate is not the pinned Candidate M initramfs"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-watchdog-registration-delta.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "$workdir/baseline" "$workdir/candidate" "$workdir/expected"
gzip -dc "$baseline" | (cd "$workdir/baseline" && cpio -idmu --quiet)
gzip -dc "$candidate" | (cd "$workdir/candidate" && cpio -idmu --quiet)
gzip -dc "$baseline" | (cd "$workdir/expected" && cpio -idmu --quiet)

cmp -s "$workdir/baseline/init" "$baseline_init_source" || \
	die "baseline archive /init is not exact Candidate L"
cmp -s "$workdir/candidate/init" "$candidate_init_source" || \
	die "candidate archive /init does not match tracked Candidate M"

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
	die "candidate is not the canonical deterministic Candidate M archive"

init="$workdir/candidate/init"
grep -Fqx 'readonly MARKER="GEMINI_WATCHDOG_REGISTRATION_20260718_M"' "$init" || \
	die "candidate /init lacks the exact unique marker"
grep -Fqx 'readonly WATCHDOG_WAIT_SECONDS=10' "$init" || \
	die "watchdog discovery must remain bounded to 10 seconds"
grep -Fqx 'readonly WATCHDOG_TIMEOUT_SECONDS=31' "$init" || \
	die "watchdog timeout must remain 31 seconds"
grep -Fqx 'readonly WATCHDOG_FAILURE_SECONDS=40' "$init" || \
	die "watchdog failure boundary must remain 40 seconds"
# Match literal code in the extracted init.
# shellcheck disable=SC2016
grep -Fqx 'record "$MARKER watchdog_irq=omitted pretimeout_expected=0"' "$init" || \
	die "candidate must disclose the omitted pretimeout IRQ"
grep -Fqx 'record_probe_state' "$init" || \
	die "candidate lacks the pre-open probe-state call"
grep -Fqx $'if exec 3>/dev/watchdog0; then' "$init" || \
	die "candidate must open watchdog fd 3 exactly once"
[[ "$(grep -Fxc $'if exec 3>/dev/watchdog0; then' "$init")" == 1 ]] || \
	die "watchdog may be opened at exactly one source site"
grep -Fqx $'\tif printf '\''.'\'' >&3; then' "$init" || \
	die "candidate must send one ownership-handoff ping"
[[ "$(grep -Foc '>&3' "$init")" == 1 ]] || \
	die "watchdog fd 3 may have exactly one write redirection"
first_probe_line="$(grep -nFx 'record_probe_state' "$init" | awk -F: 'NR == 1 {print $1}')"
open_line="$(grep -nFx 'if exec 3>/dev/watchdog0; then' "$init" | awk -F: '{print $1}')"
[[ "$first_probe_line" =~ ^[0-9]+$ && "$open_line" =~ ^[0-9]+$ && \
	"$first_probe_line" -lt "$open_line" ]] || die "probe state must be recorded before watchdog open"

grep -Fq '/sys/bus/platform/devices/10007000.watchdog' "$init" || \
	die "platform-device diagnostic is missing"
grep -Fq '/sys/class/watchdog/watchdog0' "$init" || \
	die "watchdog class diagnostic is missing"
grep -Fq '/sys/bus/platform/devices/*ramoops*' "$init" || \
	die "ramoops binding diagnostic is missing"
grep -Fq "grep -Ei 'mtk-wdt|watchdog|ramoops|pstore|10007000'" "$init" || \
	die "bounded probe-log filter is missing"
grep -Fqx $'\t\t| /bin/busybox grep -Fv "$MARKER" \\' "$init" || \
	die "probe-log filter must exclude Candidate M marker traffic"
grep -Fq 'kmsg_write=success' "$init" || die "kmsg write result is missing"
grep -Fqx $'\trecord_wait_state "$remaining"' "$init" || \
	die "each wait iteration must repeat the live registration summary"
# Match literal code in the extracted init.
# shellcheck disable=SC2016
grep -Fq 'wait=${wait_remaining}s platform=$wait_platform driver=$wait_driver class=$wait_class devnode=$wait_devnode' \
	"$init" || die "compact per-second registration summary is missing"
grep -Fq '/sys/firmware/devicetree/base/watchdog@10007000' "$init" || \
	die "live watchdog DT diagnostic is missing"
grep -Fqx $'\tif [ -e "$live_watchdog_node/interrupts" ]; then' "$init" || \
	die "live DT interrupt-property gate is missing"
grep -Fqx 'if ! validate_live_dtb_contract; then' "$init" || \
	die "watchdog test must stop when the live DT delta is not established"

grep -Fqx 'if mount -t proc -o ro,nosuid,nodev,noexec proc /proc 2>/dev/null; then' \
	"$init" || die "procfs must be mounted read-only with an observed result"
grep -Fqx 'if mount -t sysfs -o ro,nosuid,nodev,noexec sysfs /sys 2>/dev/null; then' \
	"$init" || die "sysfs must be mounted read-only with an observed result"
# Match literal code in the extracted init.
# shellcheck disable=SC2016
grep -Fqx 'if [ "$sysfs_status" != mounted ]; then' "$init" || \
	die "failed sysfs mount must invalidate the diagnostic"
grep -Fqx $'\trecord "$MARKER sysfs=failed diagnostic=invalid; STATIC HOLD"' "$init" || \
	die "failed sysfs mount must enter a static hold"
[[ "$(grep -Ec '^[[:space:]]*((if[[:space:]]+!?[[:space:]]*)?mount)[[:space:]]' "$init")" == 3 ]] || \
	die "init may mount only devtmpfs, procfs and sysfs"

if grep -Eqi '/dev/(fb|mmc|block|mem|kmem|i2c)|/proc/sysrq-trigger|/sys/class/net|(^|[^[:alnum:]_])(dd|devmem|reboot|poweroff|halt|shutdown|kexec|i2cget|i2cset|i2cdump|mknod|sync|ip|ifconfig|route|nc|telnet|wget|tftp|udhcpc)([^[:alnum:]_]|$)' "$init"; then
	die "candidate /init contains forbidden storage, framebuffer, raw-memory, I2C, reset, or network access"
fi
if grep -Eqi 'exec[[:space:]]+/bin/(ba)?sh|nc[^#]*-e[[:space:]]+/bin/(ba)?sh|(^|[^[:alnum:]_])(ash|bash|sh)[[:space:]]+-[cil]' "$init"; then
	die "candidate /init must not expose an interactive shell"
fi

printf 'validation=watchdog-registration-initramfs-delta\n'
printf 'baseline_sha256=%s\n' "$EXPECTED_BASELINE_INITRAMFS_SHA256"
printf 'candidate_sha256=%s\n' "$EXPECTED_CANDIDATE_INITRAMFS_SHA256"
printf 'archive_path_type_mode_link_manifest_identical=yes\n'
printf 'only_differing_regular_file=init\n'
printf 'canonical_archive_bytes=yes\n'
printf 'marker=GEMINI_WATCHDOG_REGISTRATION_20260718_M\n'
printf 'watchdog_irq=omitted\n'
printf 'pre_open_diagnostics=platform,driver,class,devnode,ramoops,kmsg,dmesg\n'
printf 'live_dtb_gate=watchdog-interrupts-absent\n'
printf 'per_second_summary=platform,driver,class,devnode\n'
printf 'watchdog_action=open-fd3,one-handoff-ping,hold-without-further-pings\n'
printf 'watchdog_timeout_seconds=31\n'
printf 'storage_access=none\n'
printf 'runtime_networking=none\n'
printf 'generic_reset_command=none\n'
printf 'hardware_write=none\n'
