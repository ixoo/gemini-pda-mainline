#!/usr/bin/env bash
# Literal source checks intentionally contain unexpanded shell expressions.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline W_INITRAMFS --candidate FILE --helper FILE\n' "$0" >&2; }

baseline=
candidate=
helper=
while (($#)); do
	case "$1" in
		--baseline) (($# >= 2)) || die "$1 requires a value"; baseline=$2; shift 2 ;;
		--candidate) (($# >= 2)) || die "$1 requires a value"; candidate=$2; shift 2 ;;
		--helper) (($# >= 2)) || die "$1 requires a value"; helper=$2; shift 2 ;;
		-h|--help) usage; exit 0 ;;
		*) usage; die "unknown option: $1" ;;
	esac
done
[[ -s "$baseline" && ! -L "$baseline" && -s "$candidate" && ! -L "$candidate" && \
	-x "$helper" && ! -L "$helper" ]] || die "missing exact regular input"
for command in awk cat chmod cmp cpio find grep gzip install ln mkdir mktemp od \
	python3 readelf readlink rm sha256sum sort stat touch tr; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

readonly W_INITRAMFS_SHA256=3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6
readonly W_BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
readonly W_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$W_INITRAMFS_SHA256" ]] || \
	die "baseline is not exact Candidate W initramfs"
[[ "$(sha256sum "$helper" | awk '{print $1}')" == "$W_HELPER_SHA256" ]] || \
	die "helper is not exact Candidate W input-event-capture"
readelf -lW "$helper" | grep -q ' INTERP ' && die "helper contains PT_INTERP"
gzip -t "$candidate" || die "candidate initramfs is not a valid gzip stream"
gzip_header="$(od -An -tx1 -N10 "$candidate" | tr -d ' \n')"
[[ "$gzip_header" == 1f8b0800000000000203 ]] || \
	die "gzip header is not deterministic -n/-9"

python3 - "$candidate" <<'PY'
import gzip
import pathlib
import stat
import sys

expected = {
    ".", "bin", "dev", "etc", "proc", "run", "sys", "init",
    "bin/busybox", "bin/input-event-capture", "bin/local-shell",
    "bin/reboot", "bin/x-probe", "bin/x-record", "etc/inittab",
    "bin/ash", "bin/cat", "bin/chvt", "bin/clear", "bin/init",
    "bin/mount", "bin/readlink", "bin/sh", "bin/sleep", "bin/stty",
    "bin/true",
}
directories = {".", "bin", "dev", "etc", "proc", "run", "sys"}
symlinks = {
    "bin/ash", "bin/cat", "bin/chvt", "bin/clear", "bin/init",
    "bin/mount", "bin/readlink", "bin/sh", "bin/sleep", "bin/stty",
    "bin/true",
}
data = gzip.decompress(pathlib.Path(sys.argv[1]).read_bytes())
offset = 0
seen = set()
trailer = False
while offset + 110 <= len(data):
    header = data[offset:offset + 110]
    if header[:6] != b"070701":
        raise SystemExit("error: initramfs is not canonical newc")
    try:
        fields = [int(header[6 + index * 8:14 + index * 8], 16) for index in range(13)]
    except ValueError as exc:
        raise SystemExit("error: malformed newc header") from exc
    mode, uid, gid, mtime, size, namesize = (
        fields[1], fields[2], fields[3], fields[5], fields[6], fields[11]
    )
    if namesize < 2:
        raise SystemExit("error: invalid newc pathname size")
    name_start = offset + 110
    name_end = name_start + namesize
    if name_end > len(data) or data[name_end - 1] != 0:
        raise SystemExit("error: truncated newc pathname")
    raw_name = data[name_start:name_end - 1]
    try:
        name = raw_name.decode("ascii")
    except UnicodeDecodeError as exc:
        raise SystemExit("error: non-ASCII newc pathname") from exc
    data_start = (name_end + 3) & ~3
    data_end = data_start + size
    if data_end > len(data):
        raise SystemExit("error: truncated newc payload")
    next_offset = (data_end + 3) & ~3
    if name == "TRAILER!!!":
        if size != 0:
            raise SystemExit("error: non-empty newc trailer")
        trailer = True
        if any(data[next_offset:]):
            raise SystemExit("error: nonzero bytes after newc trailer")
        break
    normalized = name[2:] if name.startswith("./") else name
    if normalized == "":
        normalized = "."
    pure = pathlib.PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts or normalized.startswith("/"):
        raise SystemExit("error: unsafe newc pathname")
    if normalized in seen:
        raise SystemExit("error: duplicate newc member")
    seen.add(normalized)
    if uid != 0 or gid != 0 or mtime != 0:
        raise SystemExit("error: noncanonical newc ownership or timestamp")
    file_type = stat.S_IFMT(mode)
    permissions = stat.S_IMODE(mode)
    if normalized in directories:
        if file_type != stat.S_IFDIR or permissions != 0o755:
            raise SystemExit("error: expected directory has wrong type or mode")
    if normalized in symlinks:
        if (file_type != stat.S_IFLNK or permissions != 0o777 or
                data[data_start:data_end] != b"busybox"):
            raise SystemExit("error: invalid BusyBox applet symlink")
    elif normalized not in directories:
        expected_mode = 0o644 if normalized == "etc/inittab" else 0o755
        if file_type != stat.S_IFREG or permissions != expected_mode:
            raise SystemExit("error: expected regular file has wrong type or mode")
    offset = next_offset
if not trailer:
    raise SystemExit("error: missing newc trailer")
if seen != expected:
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    raise SystemExit(f"error: initramfs member allowlist mismatch: missing={missing[:1]} extra={extra[:1]}")
PY

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="${script_dir}/../initramfs"
for source in "$source_dir/init" "$source_dir/inittab" \
	"$source_dir/local-shell" "$source_dir/reboot" "$source_dir/x-probe" \
	"$source_dir/x-record"; do
	[[ -s "$source" && ! -L "$source" ]] || \
		die "tracked initramfs source is missing, empty, or a symlink: $source"
done
workdir="$(mktemp -d /tmp/candidate-x-initramfs.XXXXXX)"
cleanup() { rm -rf "$workdir"; }
trap cleanup EXIT
mkdir "$workdir/root" "$workdir/w" "$workdir/rebuilt"
gzip -dc "$candidate" | (cd "$workdir/root" && cpio -idmu --quiet)
gzip -dc "$baseline" | \
	(cd "$workdir/w" && cpio -idmu --quiet bin/busybox bin/input-event-capture)

[[ "$(sha256sum "$workdir/root/bin/busybox" | awk '{print $1}')" == "$W_BUSYBOX_SHA256" ]] || \
	die "BusyBox bytes changed"
cmp -s "$workdir/w/bin/input-event-capture" "$helper" || \
	die "exact Candidate W archive helper differs from selected helper"
cmp -s "$workdir/root/bin/input-event-capture" "$helper" || \
	die "archive helper differs from exact Candidate W helper"
cmp -s "$workdir/root/init" "$source_dir/init" || die "archive /init differs from source"
for program in local-shell reboot x-probe x-record; do
	cmp -s "$workdir/root/bin/$program" "$source_dir/$program" || \
		die "archive program differs from source: $program"
done
cmp -s "$workdir/root/etc/inittab" "$source_dir/inittab" || \
	die "archive inittab differs from source"
printf '%s\n' 'tty1::respawn:/bin/local-shell' \
	'::ctrlaltdel:/bin/busybox true' >"$workdir/inittab.expected"
cmp -s "$workdir/root/etc/inittab" "$workdir/inittab.expected" || \
	die "inittab must contain only respawned tty1 shell and inert ctrl-alt-delete"

linked_applets='ash cat chvt clear init mount readlink sh sleep stty true'
available="$("$workdir/root/bin/busybox" --list)"
for applet in $linked_applets reboot; do
	grep -Fxq "$applet" <<<"$available" || die "BusyBox applet missing: $applet"
done
for applet in $linked_applets; do
	[[ "$(readlink "$workdir/root/bin/$applet")" == busybox ]] || \
		die "BusyBox applet symlink target changed: $applet"
done
[[ ! -L "$workdir/root/bin/reboot" ]] || die "/bin/reboot must be the tracked wrapper"

payload_text="$workdir/payload.txt"
cat "$workdir/root/init" "$workdir/root/bin/local-shell" \
	"$workdir/root/bin/reboot" "$workdir/root/bin/x-probe" \
	"$workdir/root/bin/x-record" >"$payload_text"
for forbidden in /dev/watchdog /sys/class/watchdog 10007000.watchdog \
	watchdog@10007000 /bin/w-watchdog handoff_ping further_pings; do
	! grep -Fq "$forbidden" "$payload_text" || \
		die "watchdog access or ownership token present: $forbidden"
done
for forbidden in /dev/mmc /dev/block /sys/block /proc/partitions \
	/bin/dd /bin/mountpoint /bin/swapon /bin/fsck /bin/mkfs sysrq-trigger \
	/bin/poweroff /bin/halt /bin/kexec; do
	! grep -Fq "$forbidden" "$payload_text" || \
		die "storage access token present: $forbidden"
done
grep -Fqx '/bin/x-probe &' "$workdir/root/init" || \
	die "probe is not started independently by /init"
! grep -Fq '/bin/x-probe' "$workdir/root/bin/local-shell" || \
	die "probe incorrectly depends on shell startup"
grep -Fqx "/bin/x-record 'manual_reboot=requested method=busybox-forced storage_access=none'" \
	"$workdir/root/bin/reboot" || die "manual reboot request marker changed"
grep -Fqx '/bin/busybox reboot -n -f' "$workdir/root/bin/reboot" || \
	die "manual reboot is not exact BusyBox no-sync forced reboot"
[[ "$(grep -Fxc '/bin/busybox reboot -n -f' "$workdir/root/bin/reboot")" == 1 ]] || \
	die "manual reboot wrapper must contain one exact reboot invocation"
! grep -Eq '^[[:space:]]*(exec[[:space:]]+)?(/bin/)?(busybox[[:space:]]+)?sync([[:space:]]|$)' \
	"$workdir/root/bin/reboot" || die "manual reboot wrapper contains a sync command"
intent_line="$(grep -Fn "manual_reboot=requested method=busybox-forced storage_access=none" \
	"$workdir/root/bin/reboot" | awk -F: 'NR == 1 { print $1 }')"
reboot_line="$(grep -Fn '/bin/busybox reboot -n -f' "$workdir/root/bin/reboot" | \
	awk -F: 'NR == 1 { print $1 }')"
[[ "$intent_line" =~ ^[0-9]+$ && "$reboot_line" =~ ^[0-9]+$ && \
	"$intent_line" -lt "$reboot_line" ]] || \
	die "manual reboot intent must precede the sole reboot invocation"
for automatic_path in "$workdir/root/init" "$workdir/root/etc/inittab" \
	"$workdir/root/bin/local-shell" "$workdir/root/bin/x-probe" \
	"$workdir/root/bin/x-record"; do
	! grep -Eq '(^|[;&|])[[:space:]]*(exec[[:space:]]+)?(/bin/reboot|/bin/busybox[[:space:]]+reboot)([[:space:]]|$)|^[[:space:]]*(exec[[:space:]]+)?reboot([[:space:]]|$)' \
		"$automatic_path" || \
		die "automatic path contains a reboot invocation: $automatic_path"
done
grep -Fq "export PS1='GEMINI-X# '" "$workdir/root/bin/local-shell" || \
	die "Candidate X prompt changed"
grep -Fq "readonly MARKER='GEMINI_KEYBOARD_MANUAL_REBOOT_20260719_X'" \
	"$workdir/root/bin/x-record" || die "Candidate X marker changed"
grep -Fqx 'output=/dev/ttyS0' "$workdir/root/bin/x-record" || \
	die "background serial sink changed"
for forbidden in /dev/tty0 /dev/tty1 /dev/tty2 /dev/console; do
	! grep -Fq "$forbidden" "$workdir/root/init" "$workdir/root/bin/x-probe" \
		"$workdir/root/bin/x-record" || \
		die "background path references visible VT sink: $forbidden"
done

# Reconstruct the complete archive independently and demand byte identity.
mkdir -p "$workdir/rebuilt/bin" "$workdir/rebuilt/etc" "$workdir/rebuilt/dev" \
	"$workdir/rebuilt/proc" "$workdir/rebuilt/run" "$workdir/rebuilt/sys"
chmod 0755 "$workdir/rebuilt" "$workdir/rebuilt/bin" "$workdir/rebuilt/etc" \
	"$workdir/rebuilt/dev" "$workdir/rebuilt/proc" "$workdir/rebuilt/run" \
	"$workdir/rebuilt/sys"
install -m 0755 "$workdir/w/bin/busybox" "$workdir/rebuilt/bin/busybox"
install -m 0755 "$helper" "$workdir/rebuilt/bin/input-event-capture"
install -m 0755 "$source_dir/init" "$workdir/rebuilt/init"
for program in local-shell reboot x-probe x-record; do
	install -m 0755 "$source_dir/$program" "$workdir/rebuilt/bin/$program"
done
install -m 0644 "$source_dir/inittab" "$workdir/rebuilt/etc/inittab"
for applet in $linked_applets; do
	ln -s busybox "$workdir/rebuilt/bin/$applet"
done
find "$workdir/rebuilt" -exec touch -h -d @0 {} +
(
	cd "$workdir/rebuilt"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/rebuilt.img"
cmp -s "$candidate" "$workdir/rebuilt.img" || \
	die "candidate is not the canonical deterministic Candidate X archive"

printf 'validation=candidate-x-initramfs\n'
printf 'candidate_sha256=%s\n' "$(sha256sum "$candidate" | awk '{print $1}')"
printf 'baseline_sha256=%s\nhelper_sha256=%s\n' "$W_INITRAMFS_SHA256" "$W_HELPER_SHA256"
printf 'marker=GEMINI_KEYBOARD_MANUAL_REBOOT_20260719_X\nprompt=GEMINI-X#\n'
printf 'probe=independent\ntty1_shell=respawn\nbackground_vt_output=none\n'
printf 'watchdog_userspace=start-none,open-none,ping-none\n'
printf 'manual_reboot=busybox-reboot-no-sync-force\nmanual_reboot_storage_access=none\n'
printf 'runtime_networking=none\nstorage_access=none\nhardware_write=none\n'
