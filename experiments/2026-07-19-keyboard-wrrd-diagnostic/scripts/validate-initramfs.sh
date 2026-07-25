#!/usr/bin/env bash
# Literal source checks intentionally contain unexpanded shell expressions.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline V_INITRAMFS --candidate FILE --helper FILE\n' "$0" >&2; }

baseline=
candidate=
helper=
while (($#)); do
	case "$1" in
		--baseline) baseline=$2; shift 2 ;;
		--candidate) candidate=$2; shift 2 ;;
		--helper) helper=$2; shift 2 ;;
		*) usage; die "unknown option: $1" ;;
	esac
done
[[ -s "$baseline" && -s "$candidate" && -x "$helper" ]] || die "missing required input"
for command in awk chmod cmp cp cpio file find grep gzip mkdir mktemp python3 \
	readelf readlink rm sed sha256sum sort strings touch; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

readonly V_INITRAMFS_SHA256=9382288385b50fed67b47ae494609f4ee9d314cfac0257c738e33e86094508b6
readonly V_BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
readonly V_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$V_INITRAMFS_SHA256" ]] || \
	die "baseline is not exact Candidate V initramfs"
[[ "$(sha256sum "$helper" | awk '{print $1}')" == "$V_HELPER_SHA256" ]] || \
	die "helper is not exact Candidate V input-event-capture"
gzip -t "$candidate" || die "candidate initramfs is not a valid gzip stream"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="${script_dir}/../initramfs"
workdir="$(mktemp -d "${TMPDIR:-/tmp}/candidate-w-initramfs.XXXXXX")"
trap 'rm -rf "$workdir"' EXIT
mkdir "$workdir/root" "$workdir/v" "$workdir/rebuilt"
gzip -dc "$candidate" | (cd "$workdir/root" && cpio -idmu --quiet)
gzip -dc "$baseline" | \
	(cd "$workdir/v" && \
		cpio -idmu --quiet bin/busybox bin/input-event-capture bin/v-watchdog)

[[ "$(sha256sum "$workdir/root/bin/busybox" | awk '{print $1}')" == "$V_BUSYBOX_SHA256" ]] || \
	die "BusyBox bytes changed"
cmp -s "$workdir/v/bin/input-event-capture" "$helper" || \
	die "exact Candidate V archive helper differs from selected helper"
cmp -s "$workdir/root/bin/input-event-capture" "$helper" || \
	die "archive helper differs from exact Candidate V helper"
sed 's#/bin/v-record#/bin/w-record#g' "$workdir/v/bin/v-watchdog" \
	>"$workdir/v/w-watchdog.expected"
cmp -s "$workdir/root/bin/w-watchdog" "$workdir/v/w-watchdog.expected" || \
	die "watchdog behavior differs from exact Candidate V beyond the recorder rename"
cmp -s "$workdir/root/init" "$source_dir/init" || die "archive /init differs from source"
for program in local-shell pass w-probe w-record w-watchdog; do
	cmp -s "$workdir/root/bin/$program" "$source_dir/$program" || \
		die "archive program differs from source: $program"
done
cmp -s "$workdir/root/etc/inittab" "$source_dir/inittab" || \
	die "archive inittab differs from source"
printf '%s\n' 'tty1::respawn:/bin/local-shell' \
	'::ctrlaltdel:/bin/busybox true' >"$workdir/inittab.expected"
cmp -s "$workdir/root/etc/inittab" "$workdir/inittab.expected" || \
	die "inittab must contain only the tty1 shell and inert ctrl-alt-delete action"

applets='ash cat chvt clear init mount readlink sh sleep stty true'
expected="$({
	printf '%s\n' . bin dev etc proc run sys init bin/busybox \
		bin/input-event-capture bin/local-shell bin/pass bin/w-probe \
		bin/w-record bin/w-watchdog etc/inittab
	for applet in $applets; do printf 'bin/%s\n' "$applet"; done
} | sort)"
actual="$(cd "$workdir/root" && find . -printf '%P\n' | sed 's/^$/./' | sort)"
[[ "$actual" == "$expected" ]] || die "archive member allowlist mismatch"
for applet in $applets; do
	[[ "$(readlink "$workdir/root/bin/$applet")" == busybox ]] || \
		die "BusyBox applet symlink target changed: $applet"
done

python3 - "$candidate" <<'PY'
import gzip
import pathlib
import stat
import sys

raw = pathlib.Path(sys.argv[1]).read_bytes()
if raw[:10] != bytes.fromhex("1f8b0800000000000203"):
    raise SystemExit("error: gzip header is not deterministic -n/-9")
data = gzip.decompress(raw)
offset = 0
seen = set()
while True:
    if data[offset:offset + 6] != b"070701":
        raise SystemExit("error: archive is not canonical newc")
    fields = [int(data[offset + 6 + i * 8:offset + 14 + i * 8], 16) for i in range(13)]
    mode, uid, gid, nlink, mtime, size, namesize = (
        fields[1], fields[2], fields[3], fields[4], fields[5], fields[6], fields[11]
    )
    name_start = offset + 110
    name_end = name_start + namesize
    if namesize < 2 or data[name_end - 1] != 0:
        raise SystemExit("error: malformed newc name")
    name = data[name_start:name_end - 1].decode("utf-8")
    content_start = (name_end + 3) & ~3
    content_end = content_start + size
    offset = (content_end + 3) & ~3
    if name == "TRAILER!!!":
        if any(data[offset:]):
            raise SystemExit("error: nonzero bytes follow newc trailer")
        break
    if name in seen:
        raise SystemExit(f"error: duplicate archive member: {name}")
    seen.add(name)
    if uid != 0 or gid != 0 or mtime != 0:
        raise SystemExit(f"error: noncanonical owner/time: {name}")
    permissions = stat.S_IMODE(mode)
    if stat.S_ISDIR(mode) and permissions != 0o755:
        raise SystemExit(f"error: directory mode is not 0755: {name}")
    if stat.S_ISREG(mode) and name != "etc/inittab" and permissions != 0o755:
        raise SystemExit(f"error: executable mode is not 0755: {name}")
    if name == "etc/inittab" and permissions != 0o644:
        raise SystemExit("error: inittab mode is not 0644")
    if stat.S_ISLNK(mode) and permissions != 0o777:
        raise SystemExit(f"error: symlink mode is not 0777: {name}")
PY

cp -a "$workdir/root/." "$workdir/rebuilt/"
chmod 0755 "$workdir/rebuilt"
find "$workdir/rebuilt" -exec touch -h -d @0 {} +
(
	cd "$workdir/rebuilt"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/rebuilt.img"
cmp -s "$candidate" "$workdir/rebuilt.img" || \
	die "archive is not the deterministic canonical reconstruction"

file "$workdir/root/bin/input-event-capture" >"$workdir/helper.file"
readelf -lW "$workdir/root/bin/input-event-capture" >"$workdir/helper.readelf"
strings "$workdir/root/bin/input-event-capture" >"$workdir/helper.strings"
grep -Fq 'ARM aarch64' "$workdir/helper.file" || die "helper is not AArch64"
grep -Fq 'statically linked' "$workdir/helper.file" || die "helper is not static"
! grep -q ' INTERP ' "$workdir/helper.readelf" || die "helper has PT_INTERP"
grep -Fq 'usage: input-event-capture /dev/input/eventN EXPECTED_NAME' \
	"$workdir/helper.strings" || die "helper does not require exact path and expected name"
grep -Fq 'identity=exact-sysfs-to-fd' "$workdir/helper.strings" || \
	die "helper lacks exact identity result"
grep -Fq 'capture-bound-15s-absolute-monotonic' "$workdir/helper.strings" || \
	die "helper does not expose the exact absolute 15-second capture bound"

init="$workdir/root/init"
watchdog="$workdir/root/bin/w-watchdog"
probe="$workdir/root/bin/w-probe"
record="$workdir/root/bin/w-record"
shell="$workdir/root/bin/local-shell"
pass="$workdir/root/bin/pass"
grep -Fqx "readonly MARKER='GEMINI_KEYBOARD_WRRD_20260719_W'" "$init" || \
	die "exact Candidate W marker is absent from init"
grep -Fqx "readonly MARKER='GEMINI_KEYBOARD_WRRD_20260719_W'" "$record" || \
	die "exact Candidate W marker is absent from recorder"
grep -Fqx '/bin/w-watchdog &' "$init" || die "watchdog worker is not independent"
grep -Fqx '/bin/w-probe &' "$init" || die "probe worker is not independent"
grep -Fqx 'exec /bin/busybox init' "$init" || die "BusyBox init supervision is absent"
grep -Fqx 'tty1::respawn:/bin/local-shell' "$workdir/root/etc/inittab" || \
	die "tty1 shell is not independently supervised"
grep -Fqx "export PS1='GEMINI-W# '" "$shell" || die "exact W shell prompt is absent"

[[ "$(grep -Fxc 'if /bin/busybox chvt 1; then' "$shell")" == 1 ]] || \
	die "tty1 must be selected at exactly one source site"
[[ "$(grep -Fxc '/bin/busybox clear' "$shell")" == 1 ]] || \
	die "tty1 must be cleared exactly once"
grep -Fqx '/bin/busybox stty sane' "$shell" || die "tty1 sane mode setup is absent"
grep -Fqx "/bin/w-record \"tty1_shell=ready foreground_vt=\$foreground_vt prompt=GEMINI-W# run=pass status=/run/w-status\"" \
	"$shell" || die "tty1 readiness record or letters-only command advertisement is absent"
grep -Fqx "printf '%s\\n' 'Type pass then Enter to record keyboard success.'" "$shell" || \
	die "visible pass instruction is absent"
grep -Fqx 'exec /bin/busybox ash -i' "$shell" || die "interactive shell exec is absent"
chvt_line="$(grep -nFx 'if /bin/busybox chvt 1; then' "$shell" | awk -F: 'NR == 1 {print $1}')"
clear_line="$(grep -nFx '/bin/busybox clear' "$shell" | awk -F: 'NR == 1 {print $1}')"
ready_line="$(grep -nF 'tty1_shell=ready' "$shell" | awk -F: 'NR == 1 {print $1}')"
instruction_line="$(grep -nF 'Type pass then Enter' "$shell" | awk -F: 'NR == 1 {print $1}')"
shell_exec_line="$(grep -nFx 'exec /bin/busybox ash -i' "$shell" | awk -F: 'NR == 1 {print $1}')"
[[ "$chvt_line" =~ ^[0-9]+$ && "$clear_line" =~ ^[0-9]+$ && \
	"$ready_line" =~ ^[0-9]+$ && "$instruction_line" =~ ^[0-9]+$ && \
	"$shell_exec_line" =~ ^[0-9]+$ && "$chvt_line" -lt "$clear_line" && \
	"$clear_line" -lt "$ready_line" && "$ready_line" -lt "$instruction_line" && \
	"$instruction_line" -lt "$shell_exec_line" ]] || \
	die "foreground selection, clear, advertisement and shell exec ordering changed"

grep -Fqx "/bin/w-record 'SHELL_INPUT_PASS typed_command=pass required_keys=P,A,S,ENTER'" \
	"$pass" || die "letters-only pass success record is absent"
typed_token="$(sed -n 's/.*typed_command=\([[:alpha:]]*\).*/\1/p' "$pass")"
[[ "$typed_token" == pass && "$typed_token" =~ ^[[:alpha:]]+$ ]] || \
	die "success token is not exact letters-only pass"
grep -Fq 'required_keys=P,A,S,ENTER' "$pass" || \
	die "P/A/S/Enter keymap requirement is not explicit"
! grep -Fq 'typed_command=/bin/' "$pass" || die "success token requires slash characters"
! grep -Fq 'run=/bin/' "$shell" || die "advertised command requires slash characters"

grep -Fqx 'readonly WATCHDOG_WAIT_SECONDS=10' "$watchdog" || \
	die "watchdog discovery is not bounded to 10 seconds"
grep -Fqx 'readonly WATCHDOG_TIMEOUT_SECONDS=31' "$watchdog" || \
	die "watchdog timeout contract is not 31 seconds"
grep -Fqx 'readonly WATCHDOG_FAILURE_SECONDS=40' "$watchdog" || \
	die "watchdog failure boundary is not 40 seconds"
grep -Fqx 'if exec 3>/dev/watchdog0; then' "$watchdog" || \
	die "watchdog fd 3 open is absent"
[[ "$(grep -Fxc 'if exec 3>/dev/watchdog0; then' "$watchdog")" == 1 ]] || \
	die "watchdog may be opened at exactly one source site"
grep -Fqx $'\tif printf '\''.'\'' >&3; then' "$watchdog" || \
	die "single ownership-handoff ping is absent"
[[ "$(grep -Foc '>&3' "$watchdog")" == 1 ]] || \
	die "watchdog fd 3 may be written exactly once"
! grep -Eq '/(proc/(self|[0-9]+)/fd|dev/fd)/3|exec 3>&-' "$watchdog" || \
	die "watchdog fd 3 has an alias or explicit close path"
grep -Fq 'watchdog_observation=invalid reason=live-node-unavailable recovery=continue' \
	"$watchdog" || die "missing live watchdog node does not preserve recovery"
grep -Fq 'watchdog_observation=invalid reason=live-interrupts-present recovery=continue' \
	"$watchdog" || die "live watchdog IRQ mismatch does not preserve recovery"
grep -Fq 'if [ "$identity" != mtk-wdt ] && [ "$platform_driver" != mtk-wdt ]; then' \
	"$watchdog" || die "safe watchdog identity gate is absent"
grep -Fq 'class_device="$(readlink -f /sys/class/watchdog/watchdog0/device 2>/dev/null || true)"' \
	"$watchdog" || die "canonical watchdog class-device lookup is absent"
grep -Fq 'platform_device="$(readlink -f /sys/bus/platform/devices/10007000.watchdog 2>/dev/null || true)"' \
	"$watchdog" || die "canonical exact platform-device lookup is absent"
grep -Fq '[ "$class_device" != "$platform_device" ]; then' "$watchdog" || \
	die "watchdog class device is not correlated to exact 10007000 platform device"
grep -Fq 'watchdog_association=exact class_device=$class_device platform_driver=$platform_driver' \
	"$watchdog" || die "exact watchdog association result is absent"
grep -Fq 'watchdog_observation=invalid timeout=$timeout expected=$WATCHDOG_TIMEOUT_SECONDS recovery=continue' \
	"$watchdog" || die "timeout mismatch does not preserve bounded recovery"
grep -Fq '/sys/bus/platform/devices/*ramoops*' "$watchdog" || \
	die "ramoops platform binding check is absent"
grep -Fq 'observation_contract=invalid ramoops_platform=$ramoops_platform driver=$ramoops_driver watchdog_recovery=continue' \
	"$watchdog" || die "ramoops failure does not preserve watchdog recovery"
ramoops_invalid_line="$(grep -nF 'observation_contract=invalid ramoops_platform=' "$watchdog" | \
	awk -F: 'NR == 1 {print $1}')"
watchdog_open_line="$(grep -nFx 'if exec 3>/dev/watchdog0; then' "$watchdog" | \
	awk -F: 'NR == 1 {print $1}')"
[[ "$ramoops_invalid_line" =~ ^[0-9]+$ && "$watchdog_open_line" =~ ^[0-9]+$ && \
	"$ramoops_invalid_line" -lt "$watchdog_open_line" ]] || \
	die "ramoops binding result must precede watchdog ownership"

grep -Fqx 'readonly DISCOVERY_SECONDS=5' "$probe" || \
	die "input discovery is not bounded to 5 seconds"
grep -Fqx 'readonly CAPTURE_SECONDS=15' "$probe" || \
	die "event capture is not bounded to 15 seconds"
grep -Fq 'controller_policy=mt6797-mt8173-data' "$probe" || \
	die "Candidate W controller policy marker is absent"
grep -Fq 'i2c_platform=$i2c_platform driver=$i2c_platform_driver expected_driver=i2c-mt65xx' \
	"$probe" || die "exact I2C platform/driver observation is absent"
grep -Fq '"$matrix_path"/input/input*/event*' "$probe" || \
	die "event discovery is not anchored to the matrix platform device"
grep -Fq '/bin/input-event-capture "$event_node" "$event_name"' "$probe" || \
	die "probe does not pass the exact path/name identity pair"
grep -Fq 'raw_event_window=skipped reason=no-matrix-owned-event-node' "$probe" || \
	die "absent exact event has no deterministic skip result"

grep -Fq '>>/run/w-status' "$record" || die "runtime status ledger is absent"
grep -Fq '>/dev/kmsg' "$record" || die "markers do not enter kernel console-ramoops"
grep -Fqx 'for output in /dev/ttyS0; do' "$record" || \
	die "direct diagnostic output is not restricted to ttyS0"
record_devices="$(grep -Eo '/dev/[[:alnum:]_-]+' "$record" | grep -Fvx /dev/null | sort -u)"
[[ "$record_devices" == $'/dev/kmsg\n/dev/ttyS0' ]] || \
	die "recorder has a device target other than kmsg and ttyS0"
! grep -Eq '/dev/(console|tty[0-9]+)' "$record" || \
	die "background recorder may interfere with a virtual terminal"
for background_source in "$init" "$watchdog" "$probe" "$record" "$pass"; do
	if grep -Eq '/dev/(console|tty[0-9]+)|(^|[^[:alnum:]_-])(chvt|openvt|setconsole)([^[:alnum:]_-]|$)' \
		"$background_source"; then
		die "background path may write to or take control of a virtual terminal: $background_source"
	fi
done
[[ "$(grep -Ec '^[[:space:]]*((if[[:space:]]+!?[[:space:]]*)?mount)[[:space:]]' "$init")" == 3 ]] || \
	die "init may mount only devtmpfs, procfs and sysfs"

for source in "$init" "$watchdog" "$probe" "$record" "$shell" "$pass" \
	"$workdir/root/etc/inittab"; do
	if grep -Eqi '/dev/(fb|mmc|block|mem|kmem|i2c|sd[a-z]|vd[a-z]|nvme|mapper|disk)|/proc/sysrq-trigger|/sys/class/net|(^|[^[:alnum:]_])(dd|devmem|reboot|poweroff|halt|shutdown|kexec|i2cget|i2cset|i2cdump|mknod|sync|ip|ifconfig|route|nc|telnet|wget|tftp|udhcpc)([^[:alnum:]_]|$)' "$source"; then
		die "scripted path contains forbidden storage, framebuffer, raw-I2C/memory, explicit-reset, or network access: $source"
	fi
	if grep -Eq '>[[:space:]]*/(sys|proc)/' "$source"; then
		die "scripted path writes to sysfs or procfs: $source"
	fi
done

printf 'validation=candidate-w-initramfs\n'
printf 'baseline_sha256=%s\ncandidate_sha256=%s\nbusybox_sha256=%s\nhelper_sha256=%s\n' \
	"$V_INITRAMFS_SHA256" "$(sha256sum "$candidate" | awk '{print $1}')" \
	"$V_BUSYBOX_SHA256" "$V_HELPER_SHA256"
printf 'archive=canonical-newc-root-owned-epoch-zero-gzip-n9\nmember_allowlist=exact\n'
printf 'workers=watchdog-and-probe-independent\ntty1_shell=respawn-chvt1-cleared\n'
printf 'tty1_background_marker_fanout=none\nkernel_console=external-fixed-tty2\n'
printf 'input_success_token=pass\nrequired_keys=P,A,S,ENTER\ndt_keymap_gate=external-exact-v-dtb-validator\n'
printf 'event_identity=matrix-parent-plus-exact-path-name-revalidation\n'
printf 'event_budget=5s-discovery-plus-15s-capture\n'
printf 'watchdog_action=open-fd3,one-handoff-ping,retain-without-further-pings\n'
printf 'watchdog_source=exact-candidate-v-behavior-with-recorder-rename-only\n'
printf 'marker_path=kmsg-to-console-ramoops-plus-ttyS0\n'
printf 'storage_access=none\nruntime_networking=none\nraw_i2c_access=none\nexplicit_reset_command=none\nhardware_write=none\n'
