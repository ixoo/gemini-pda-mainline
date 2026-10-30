#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the station RAM root from a retained soak RAM root.

Keeps the parent's binaries, libraries, keys, keymap and Wi-Fi firmware;
replaces its bounded session scripts with this directory's initramfs/ files;
adds the mac module under lib/modules/<release>/. Writes a newc archive with
zero timestamps, compressed with gzip -n -9 like the parent.

usage: build-station-initramfs.py PARENT_INITRAMFS MAC_KO RELEASE OUTPUT
"""
import hashlib
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


def main(parent, module, release, output):
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
    for d in ['mnt', 'mnt/data', 'tmp', 'lib/modules', 'lib/modules/' + release]:
        files[d] = (DIR | 0o755, b'')
    files['lib/modules/%s/mac.ko' % release] = (FILE | 0o644, Path(module).read_bytes())
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
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
