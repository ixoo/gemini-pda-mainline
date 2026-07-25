#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# -eq 2 ]] || die "usage: validate-initramfs-delta.sh P_INITRAMFS Q_INITRAMFS"
baseline=$1
candidate=$2
[[ -s "$baseline" && -s "$candidate" ]] || die "initramfs input missing"

readonly P_SHA256=3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8
readonly Q_SHA256=379eb9ad3d24b33df6986839968b7f3e6236e1aeaa57e906f012e30b88afe283
readonly BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
[[ "$(sha256sum "$baseline" | cut -c1-64)" == "$P_SHA256" ]] || die "baseline is not P"
[[ "$(sha256sum "$candidate" | cut -c1-64)" == "$Q_SHA256" ]] || die "candidate initramfs hash mismatch"
gzip -t "$candidate"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
gzip -dc "$candidate" >"$workdir/archive.cpio"
python3 - "$workdir/archive.cpio" <<'PY'
import pathlib
import stat
import sys

data = pathlib.Path(sys.argv[1]).read_bytes()
offset = 0
entries = {}
while True:
    if data[offset:offset + 6] != b"070701":
        raise SystemExit("error: archive is not canonical newc")
    fields = [int(data[offset + 6 + i * 8:offset + 14 + i * 8], 16) for i in range(13)]
    mode, uid, gid, nlink, mtime, size, namesize = fields[1], fields[2], fields[3], fields[4], fields[5], fields[6], fields[11]
    name_start = offset + 110
    name_end = name_start + namesize
    if namesize < 2 or data[name_end - 1] != 0:
        raise SystemExit("error: malformed newc name")
    name = data[name_start:name_end - 1].decode("utf-8")
    content_start = (name_end + 3) & ~3
    content_end = content_start + size
    content = data[content_start:content_end]
    offset = (content_end + 3) & ~3
    if name == "TRAILER!!!":
        if any(data[offset:]):
            raise SystemExit("error: nonzero bytes follow newc trailer")
        break
    if name in entries:
        raise SystemExit(f"error: duplicate archive member: {name}")
    if uid != 0 or gid != 0 or mtime != 0:
        raise SystemExit(f"error: noncanonical owner/time: {name}")
    entries[name] = (mode, nlink, content)

applets = "ash cat dmesg grep init ls mount ps readlink reboot sed sh sleep stty tail true uname".split()
expected = {".", "bin", "dev", "etc", "proc", "run", "sys", "init",
            "bin/busybox", "bin/input-event-capture", "bin/local-shell",
            "bin/q-pass", "etc/inittab"}
expected.update(f"bin/{name}" for name in applets)
if set(entries) != expected:
    raise SystemExit(f"error: member allowlist mismatch: {sorted(set(entries) ^ expected)}")
directories = {".", "bin", "dev", "etc", "proc", "run", "sys"}
executables = {"init", "bin/busybox", "bin/input-event-capture", "bin/local-shell", "bin/q-pass"}
for name, (mode, _nlink, content) in entries.items():
    permissions = stat.S_IMODE(mode)
    if name in directories:
        if not stat.S_ISDIR(mode) or permissions != 0o755 or content:
            raise SystemExit(f"error: invalid directory metadata: {name}")
    elif name in executables:
        if not stat.S_ISREG(mode) or permissions != 0o755:
            raise SystemExit(f"error: invalid executable metadata: {name}")
    elif name == "etc/inittab":
        if not stat.S_ISREG(mode) or permissions != 0o644:
            raise SystemExit("error: invalid inittab metadata")
    elif name.startswith("bin/"):
        if not stat.S_ISLNK(mode) or permissions != 0o777 or content != b"busybox":
            raise SystemExit(f"error: invalid BusyBox applet symlink: {name}")
PY

mkdir "$workdir/root"
(cd "$workdir/root" && cpio -idmu --quiet <"$workdir/archive.cpio")
[[ "$(sha256sum "$workdir/root/bin/busybox" | cut -c1-64)" == "$BUSYBOX_SHA256" ]] || \
	die "BusyBox bytes changed"
file "$workdir/root/bin/input-event-capture" | grep -Fq 'ARM aarch64' || die "helper is not AArch64"
file "$workdir/root/bin/input-event-capture" | grep -Fq 'statically linked' || die "helper is not static"
! readelf -lW "$workdir/root/bin/input-event-capture" | grep -q ' INTERP ' || die "helper has PT_INTERP"
grep -Fq 'GEMINI_KEYBOARD_SHELL_20260718_Q' "$workdir/root/init" || die "Q marker absent"
grep -Fq 'raw_event_window=begin duration=60s' "$workdir/root/init" || die "bounded event window absent"
grep -Fxq 'tty1::respawn:/bin/local-shell' "$workdir/root/etc/inittab" || die "tty1 is not supervised"
grep -Fq "exec /bin/busybox ash -i" "$workdir/root/bin/local-shell" || die "interactive shell absent"
for forbidden in 'watchdog' 'reboot -f' '/sys/devices/system/cpu/' '/dev/mmc' '/dev/mem' \
	'ip addr' 'udhcpc' 'nc -l' 'mount /dev/'; do
	! grep -R -Fq -- "$forbidden" "$workdir/root/init" "$workdir/root/bin/local-shell" \
		"$workdir/root/bin/q-pass" "$workdir/root/etc/inittab" || die "forbidden action: $forbidden"
done
printf 'validation=candidate-q-initramfs-delta\n'
printf 'baseline_sha256=%s\ncandidate_sha256=%s\nbusybox_sha256=%s\n' \
	"$P_SHA256" "$Q_SHA256" "$BUSYBOX_SHA256"
printf 'archive=newc-canonical-root-owned-epoch-zero\nmember_allowlist=exact\nhelper=static-aarch64-no-pt-interp\n'
printf 'event_window_seconds=60\ntty1_supervision=respawn\nautomatic_reboot=no\nnetwork_action=none\nstorage_action=none\n'
