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

Require an exact Candidate N archive derivative whose only archive delta is
tracked Candidate O /init, then enforce its watchdog-first, CPU1-7 sequential
sweep contract. This validator has no hardware interface.
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
baseline_init_source="${repo_root}/experiments/2026-07-18-cpu1-online-diagnostic/initramfs/init"
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=3351422e594c59e5785e12cac6ffbefa2644bd6c85932ac6825a9b9c5edd6290
readonly EXPECTED_BASELINE_INIT_SHA256=d1c312dff2c7c2afea3969b937cc0f5b524da73c95f8cd0139212820b705a440
readonly EXPECTED_CANDIDATE_INIT_SHA256=0393b9fba88bf7dc8d1ba5217f7a422066ca4f427130f3fed5eb6e064aed8d52
readonly EXPECTED_CANDIDATE_INITRAMFS_SHA256=3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8
[[ "$EXPECTED_CANDIDATE_INIT_SHA256" != TO_PIN ]] || \
	die "tracked Candidate O /init SHA-256 is not pinned"
[[ "$EXPECTED_CANDIDATE_INITRAMFS_SHA256" != TO_PIN ]] || \
	die "Candidate O initramfs SHA-256 is not pinned"
[[ -s "$candidate_init_source" ]] || die "tracked Candidate O /init is missing"
[[ -s "$baseline_init_source" ]] || die "tracked Candidate N /init is missing"
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || die "baseline is not exact Candidate N"
[[ "$(sha256sum "$baseline_init_source" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INIT_SHA256" ]] || die "tracked Candidate N /init changed"
[[ "$(sha256sum "$candidate_init_source" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INIT_SHA256" ]] || die "tracked Candidate O /init changed"
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INITRAMFS_SHA256" ]] || die "candidate archive is not pinned Candidate O"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-a53-sweep-delta.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT
mkdir "$workdir/baseline" "$workdir/candidate" "$workdir/expected"
gzip -dc "$baseline" | (cd "$workdir/baseline" && cpio -idmu --quiet)
gzip -dc "$candidate" | (cd "$workdir/candidate" && cpio -idmu --quiet)
gzip -dc "$baseline" | (cd "$workdir/expected" && cpio -idmu --quiet)

cmp -s "$workdir/baseline/init" "$baseline_init_source" || \
	die "baseline archive /init is not exact Candidate N"
cmp -s "$workdir/candidate/init" "$candidate_init_source" || \
	die "candidate archive /init does not match tracked Candidate O"
for runtime_command in busybox cat dmesg grep mount sh sleep uname; do
	[[ -x "$workdir/candidate/bin/$runtime_command" ]] || \
		die "runtime command is unavailable in inherited archive: $runtime_command"
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
	die "candidate is not the canonical deterministic Candidate O archive"

init="$workdir/candidate/init"
grep -Fqx 'readonly MARKER="GEMINI_A53_SWEEP_20260718_O"' "$init" || \
	die "candidate /init lacks the exact unique marker"
grep -Fqx 'readonly CPU_DT_SPECS="1:1:a53 2:2:a53 3:3:a53 4:100:a53 5:101:a53 6:102:a53 7:103:a53 8:200:a72 9:201:a72"' "$init" || \
	die "literal CPU-to-DT mapping is not exact"
grep -Fqx 'readonly SWEEP_CPUS="1 2 3 4 5 6 7"' "$init" || \
	die "sweep CPU set is not exact"
grep -Fqx 'readonly WATCHDOG_TIMEOUT_SECONDS=31' "$init" || \
	die "watchdog timeout must remain 31 seconds"
grep -Fqx 'readonly WATCHDOG_FAILURE_SECONDS=40' "$init" || \
	die "watchdog failure boundary must remain 40 seconds"
grep -Fqx 'readonly LATEST_REQUEST_SECONDS=23' "$init" || \
	die "request budget gate changed"
grep -Fqx 'readonly LATEST_ACCOUNTING_SECONDS=25' "$init" || \
	die "accounting budget gate changed"

grep -Fqx 'if run_a53_sweep 3>/dev/watchdog0; then' "$init" || \
	die "watchdog must be opened on the conditionally invoked sweep function"
[[ "$(grep -Fxc 'if run_a53_sweep 3>/dev/watchdog0; then' "$init")" == 1 ]] || \
	die "watchdog may be opened at exactly one source site"
if grep -Eq '(^|[[:space:]])exec[[:space:]]+[0-9]*>/dev/watchdog' "$init"; then
	die "ash exec special builtin must not own the watchdog-open failure path"
fi
grep -Fqx $'\tif ! printf \'.\' >&3; then' "$init" || \
	die "sweep must send one ownership-handoff ping"
[[ "$(grep -Foc '>&3' "$init")" == 1 ]] || \
	die "watchdog fd 3 may have exactly one write redirection"
grep -Fqx $'\tfor cpu in $SWEEP_CPUS; do' "$init" || \
	die "CPU sweep must use the exact literal set"
grep -Fqx $'\tif printf \'1\\n\' >"$online_path" 2>"$CPU_ERROR_FILE"; then' "$init" || \
	die "candidate must contain one dynamic CPU-online write source"
[[ "$(grep -Foc '>"$online_path"' "$init")" == 1 ]] || \
	die "CPU online control may have exactly one write source"
if grep -Eq '>[[:space:]]*[^#]*(cpu8|cpu9)/online' "$init"; then
	die "deferred Cortex-A72 online controls must never be written"
fi

watchdog_open_line="$(grep -nFx 'if run_a53_sweep 3>/dev/watchdog0; then' "$init" | awk -F: '{print $1}')"
cpu_loop_line="$(grep -nFx $'\tfor cpu in $SWEEP_CPUS; do' "$init" | awk -F: '{print $1}')"
cpu_write_line="$(grep -nFx $'\tif printf \'1\\n\' >"$online_path" 2>"$CPU_ERROR_FILE"; then' "$init" | awk -F: '{print $1}')"
[[ "$watchdog_open_line" =~ ^[0-9]+$ && "$cpu_loop_line" =~ ^[0-9]+$ && \
	"$cpu_write_line" =~ ^[0-9]+$ && "$cpu_write_line" -lt "$cpu_loop_line" ]] || \
	die "could not establish the validated function/loop write structure"

grep -Fq 'watchdog_identity" != mtk-wdt' "$init" || \
	die "exact watchdog identity gate is missing"
grep -Fq 'watchdog_driver" != mtk-wdt' "$init" || \
	die "exact watchdog platform-driver gate is missing"
grep -Fq '*10007000.watchdog)' "$init" || \
	die "exact watchdog device association gate is missing"
grep -Fq 'validate_initial_cpu_inventory' "$init" || \
	die "initial CPU inventory gate is missing"
grep -Fq 'validate_live_cpu_dtb_contract' "$init" || \
	die "live CPU DT gate is missing"
grep -Fq 'logical_mapping=cpu@$expected_node' "$init" || \
	die "logical CPU1-9 to DT mapping evidence is missing"
grep -Fq 'logical_mapping=invalid' "$init" || \
	die "logical CPU mapping fail-stop is missing"
grep -Fq 'precondition=unexpected-global-mask' "$init" || \
	die "cumulative pre-request mask gate is missing"
grep -Fq 'boot_line=' "$init" || die "target CPU boot-line evidence is missing"
grep -Fq 'accounting=advanced' "$init" || die "per-CPU accounting decision is missing"
grep -Fq 'checkpoint=PASS' "$init" || die "per-CPU durable checkpoint is missing"
grep -Fq 'request=budget-insufficient' "$init" || die "request budget fail-stop is missing"
grep -Fq 'accounting=budget-insufficient' "$init" || \
	die "accounting budget fail-stop is missing"
grep -Fq 'sweep=STOP' "$init" || die "first-failure stop marker is missing"
grep -Fq 'sweep_result=online-0-7 SUCCESS cpu8=offline cpu9=offline' "$init" || \
	die "complete A53 sweep success marker is missing"
grep -Fq 'final_offline" != 8-9' "$init" || \
	die "deferred Cortex-A72 final-state gate is missing"
grep -Fq 'wait_for_watchdog_reset sweep-success 7' "$init" || \
	die "successful sweep must retain watchdog recovery"

grep -Fqx 'if mount -t proc -o ro,nosuid,nodev,noexec proc /proc 2>/dev/null; then' \
	"$init" || die "procfs must be mounted read-only"
grep -Fqx 'if mount -t sysfs -o rw,nosuid,nodev,noexec sysfs /sys 2>/dev/null; then' \
	"$init" || die "sysfs must use the exact CPU-hotplug policy"
[[ "$(grep -Ec '^[[:space:]]*((if[[:space:]]+!?[[:space:]]*)?mount)[[:space:]]' "$init")" == 3 ]] || \
	die "init may mount only devtmpfs, procfs and sysfs"
grep -Fq '/bin/busybox readlink' "$init" || \
	die "readlink must use the available BusyBox binary"
grep -Fq '/bin/busybox tr -d' "$init" || \
	die "tr must use the available BusyBox binary"
grep -Fq '/bin/busybox tail -n 1' "$init" || \
	die "bounded CPU log tail must use BusyBox"
grep -Fq '/bin/busybox tail -n 4' "$init" || \
	die "bounded error tail must use BusyBox"
if grep -Eq '^[[:space:]]*(tr|readlink|tail|seq|cut|date|od)[[:space:]]' "$init"; then
	die "unqualified applet lacks an inherited initramfs symlink"
fi

if grep -Eqi '/dev/(fb|mmc|block|mem|kmem|i2c)|/proc/sysrq-trigger|/sys/class/net|(^|[^[:alnum:]_])(dd|devmem|reboot|poweroff|halt|shutdown|kexec|i2cget|i2cset|i2cdump|mknod|sync|ip|ifconfig|route|nc|telnet|wget|tftp|udhcpc)([^[:alnum:]_]|$)' "$init"; then
	die "candidate /init contains forbidden storage, framebuffer, raw-memory, I2C, reset, or network access"
fi
if grep -Eqi 'exec[[:space:]]+/bin/(ba)?sh|nc[^#]*-e[[:space:]]+/bin/(ba)?sh|(^|[^[:alnum:]_])(ash|bash|sh)[[:space:]]+-[cil]' "$init"; then
	die "candidate /init must not expose an interactive shell"
fi

candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
printf 'validation=a53-sweep-initramfs-delta\n'
printf 'baseline_sha256=%s\n' "$EXPECTED_BASELINE_INITRAMFS_SHA256"
printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'archive_path_type_mode_link_manifest_identical=yes\n'
printf 'only_differing_regular_file=init\n'
printf 'canonical_archive_bytes=yes\n'
printf 'marker=GEMINI_A53_SWEEP_20260718_O\n'
printf 'watchdog_action=open-fd3,one-handoff-ping,before-sweep,no-further-pings\n'
printf 'sysfs_writes=cpu1-7-online:1-once-each-sequential\n'
printf 'cpu8_9_action=validated-offline,no-write\n'
printf 'storage_access=none\n'
printf 'runtime_networking=none\n'
printf 'generic_reset_command=none\n'
printf 'hardware_write=seven-standard-cpu-hotplug-controls-only\n'
