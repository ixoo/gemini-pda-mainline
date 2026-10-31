#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the station RAM root from a retained soak RAM root.

Keeps the parent's binaries, libraries, keys, keymap and Wi-Fi firmware;
replaces its bounded session scripts with this directory's initramfs/ files;
adds the Wi-Fi modules under lib/modules/<release>/ and, from TOOLS, the static
lid-guard, power-status and charge-guard binaries (built from their .c
files; charge-guard is not started); gives Fn+B and Fn+N no console action, since lid-guard
uses them for brightness. Writes a newc archive with zero timestamps,
compressed with gzip -n -9 like the parent.

usage: build-station-initramfs.py PARENT_INITRAMFS MODULES TOOLS RELEASE OUTPUT
(MODULES: colon-separated .ko paths, each kept under its own name)
"""
import hashlib
import struct
import runpy
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
parse_newc = runpy.run_path(
    str(REPO/'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']

# The parent's session scripts and logger, replaced or not needed here.
DROP = {'init', 'etc/inittab', 'etc/passwd', 'etc/shells', 'bin/usb-auth',
        'bin/reboot', 'bin/reboot-dispatch.env', 'bin/admin-shell',
        'bin/console-status', 'bin/kmsg-capture', 'bin/kmsg-seal', 'bin/x-record'}
DIR, FILE, CHR = 0o040000, 0o100000, 0o020000
KEY_B, KEY_N, K_HOLE = 48, 49, 0x0200
# The kernel opens /dev/console from the archive before init mounts devtmpfs.
CONSOLE = ('dev/console', CHR | 0o600, (5, 1))


def newc(entries):
    out = bytearray()
    for ino, (name, mode, data) in enumerate(entries + [('TRAILER!!!', 0, b'')], 1):
        raw = name.encode() + b'\0'
        rdev = CONSOLE[2] if (name, mode) == CONSOLE[:2] else (0, 0)
        fields = [ino if name != 'TRAILER!!!' else 0, mode, 0, 0, 1, 0, len(data), 0, 0, *rdev,
                  len(raw), 0]
        out += b'070701' + b''.join(b'%08x' % f for f in fields) + raw
        out += bytes(-len(out) % 4)
        out += data
        out += bytes(-len(out) % 4)
    return bytes(out + bytes(-len(out) % 512))


def quiet_brightness_keys(keymap):
    """In the busybox bkeymap, set AltGr (Fn) + B and + N to K_HOLE."""
    assert keymap[:7] == b'bkeymap'
    flags = keymap[7:263]
    altgr = 2
    assert flags[altgr]
    offset = 263 + 256 * sum(1 for t in range(altgr) if flags[t])
    table = list(struct.unpack('<128H', keymap[offset:offset + 256]))
    # Fn+B was the hex digit B for typed code input, Fn+N the letter n.
    assert (table[KEY_B], table[KEY_N]) == (0x0915, 0x0b6e), (hex(table[KEY_B]), hex(table[KEY_N]))
    table[KEY_B] = table[KEY_N] = K_HOLE
    return keymap[:offset] + struct.pack('<128H', *table) + keymap[offset + 256:]


def main(parent, modules, tools, release, output):
    ram = parse_newc(Path(parent).read_bytes())
    missing = DROP - set(ram)
    assert not missing, ('parent lacks', sorted(missing))
    files = {n: (m.mode, m.data) for n, m in ram.items() if n not in DROP}
    for name in ['bin/busybox', 'bin/dropbear', 'bin/console-unicode-mode', 'etc/gemini-us.bkeymap',
                 'etc/dropbear/host_key', 'root/.ssh/authorized_keys', 'lib/firmware/mediatek/mt6797']:
        assert name in files, ('parent lacks', name)
    src = HERE/'initramfs'
    files['init'] = (FILE | 0o755, (src/'init').read_bytes())
    files['etc/inittab'] = (FILE | 0o644, (src/'inittab').read_bytes())
    files['etc/profile'] = (FILE | 0o644, (src/'profile').read_bytes())
    files['etc/passwd'] = (FILE | 0o644, b'root:x:0:0:root:/root:/bin/sh\n')
    files['etc/shells'] = (FILE | 0o644, b'/bin/sh\n')
    files['bin/usb-ssh'] = (FILE | 0o755, (src/'usb-ssh').read_bytes())
    files['bin/console-shell'] = (FILE | 0o755, (src/'console-shell').read_bytes())
    files['bin/setterm'] = (FILE | 0o755, (src/'setterm').read_bytes())
    files['bin/flash-boot2'] = (FILE | 0o755, (src/'flash-boot2').read_bytes())
    for tool in ['lid-guard', 'power-status', 'charge-guard']:
        files['bin/' + tool] = (FILE | 0o755, (Path(tools)/tool).read_bytes())
    mode, keymap = files['etc/gemini-us.bkeymap']
    files['etc/gemini-us.bkeymap'] = (mode, quiet_brightness_keys(keymap))
    for d in ['mnt', 'mnt/data', 'tmp', 'lib/modules', 'lib/modules/' + release]:
        files[d] = (DIR | 0o755, b'')
    for module in modules.split(':'):
        files['lib/modules/%s/%s' % (release, Path(module).name)] = (FILE | 0o644, Path(module).read_bytes())
    assert 'dev/console' not in files
    files[CONSOLE[0]] = (CONSOLE[1], b'')
    for name in files:
        parent_dir = name.rpartition('/')[0]
        assert not parent_dir or files.get(parent_dir, (0,))[0] & DIR, ('no directory for', name)
    data = subprocess.run(['gzip', '-n', '-9', '-c'], check=True, capture_output=True,
                          input=newc(sorted((n, mode, d) for n, (mode, d) in files.items()))).stdout
    back = parse_newc(data)
    assert {n: (m.mode, m.data) for n, m in back.items()} == files
    assert (back[CONSOLE[0]].rdevmajor, back[CONSOLE[0]].rdevminor) == CONSOLE[2]
    Path(output).write_bytes(data)
    print('%s  %s  %d bytes, %d members' % (hashlib.sha256(data).hexdigest(), output, len(data), len(files)))


if __name__ == '__main__':
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    main(*sys.argv[1:])
