#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the station RAM root from a retained soak RAM root.

Keeps the parent's binaries, libraries, keys, keymap and Wi-Fi firmware;
replaces its bounded session scripts with this directory's initramfs/ files;
adds the Wi-Fi, gemini-lid and, on the station, leds-aw9120 and regulator-haptic modules under lib/modules/<release>/ and, from TOOLS, the static
backlight-policy and power-status binaries (built from their .c files), the static ALSA tools and their alsa/
configuration (from build-alsa-tools.sh); gives Fn+B and Fn+N no console action, since backlight-policy
uses them for brightness. Writes a newc archive with zero timestamps,
compressed with gzip -n -9 like the parent.

With AUTHORIZED_KEY the parent must be release/build-parent.sh's public one, holding no
keys or firmware. init and usb-ssh come from release/ and radio-start, hw-start and firmware-get are added,
power-status is left out, and that one-line public key is the only way in.

usage: build-station-initramfs.py PARENT_INITRAMFS MODULES TOOLS RELEASE OUTPUT [AUTHORIZED_KEY]
(MODULES: colon-separated .ko paths, each kept under its own name)
"""
import base64
import hashlib
import re
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
DIR, FILE, CHR, LNK = 0o040000, 0o100000, 0o020000, 0o120000
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


def public_key_line(path):
    """One whole public key line of a type dropbear takes: a bad one locks the tester out of SSH."""
    key = Path(path).read_bytes()
    line = re.fullmatch(rb'(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)|sk-[\w@.-]+) ([A-Za-z0-9+/]+=*)( [^\n]*)?\n', key)
    assert line, 'AUTHORIZED_KEY is not one public key line'
    blob, fields = base64.b64decode(line[2], validate=True), []
    while blob:
        size = int.from_bytes(blob[:4], 'big')
        assert len(blob) >= 4 + size, 'AUTHORIZED_KEY is truncated'
        fields.append(blob[4:4 + size])
        blob = blob[4 + size:]
    assert len(fields) >= 2 and fields[0] == line[1], 'AUTHORIZED_KEY is damaged'
    return key


def main(parent, modules, tools, release, output, authorized_key=None):
    public = authorized_key is not None
    ram = parse_newc(Path(parent).read_bytes())
    drop = set() if public else DROP
    missing = drop - set(ram)
    assert not missing, ('parent lacks', sorted(missing))
    files = {n: (m.mode, m.data) for n, m in ram.items() if n not in drop}
    needed = ['bin/busybox', 'bin/dropbear', 'bin/console-unicode-mode', 'etc/gemini-us.bkeymap',
              'lib/firmware/mediatek/mt6797']
    needed += ['bin/dropbearkey', 'bin/iw', 'root/.ssh', 'etc/dropbear'] if public else [
        'etc/dropbear/host_key', 'root/.ssh/authorized_keys']
    for name in needed:
        assert name in files, ('parent lacks', name)
    if public:
        private = [n for n, (mode, _) in files.items() if n.startswith(('lib/firmware/', 'etc/dropbear/', 'root/'))
                   and not mode & DIR]
        assert not private, ('a public parent holds', private)
    src = HERE/'initramfs'
    first = HERE/'release' if public else src
    files['init'] = (FILE | 0o755, (first/'init').read_bytes())
    files['etc/inittab'] = (FILE | 0o644, (src/'inittab').read_bytes())
    files['etc/profile'] = (FILE | 0o644, (src/'profile').read_bytes())
    files['etc/passwd'] = (FILE | 0o644, b'root:x:0:0:root:/root:/bin/sh\n')
    files['etc/shells'] = (FILE | 0o644, b'/bin/sh\n')
    files['bin/usb-ssh'] = (FILE | 0o755, (first/'usb-ssh').read_bytes())
    files['bin/console-shell'] = (FILE | 0o755, (src/'console-shell').read_bytes())
    files['bin/setterm'] = (FILE | 0o755, (src/'setterm').read_bytes())
    files['bin/flash-boot2'] = (FILE | 0o755, (src/'flash-boot2').read_bytes())
    files['bin/audio-start'] = (FILE | 0o755, (src/'audio-start').read_bytes())
    files['bin/display-start'] = (FILE | 0o755, (src/'display-start').read_bytes())
    files['bin/arecord'] = (LNK | 0o777, b'aplay')
    for d in ['usr', 'usr/share']:
        files.setdefault(d, (DIR | 0o755, b''))
    alsa = Path(tools)/'alsa'
    assert (alsa/'alsa.conf').is_file(), ('tools lack', alsa)
    for path in [alsa, *sorted(alsa.rglob('*'))]:
        name = 'usr/share/alsa/' + str(path.relative_to(alsa)) if path != alsa else 'usr/share/alsa'
        files[name] = (DIR | 0o755, b'') if path.is_dir() else (FILE | 0o644, path.read_bytes())
    if public:
        files['bin/radio-start'] = (FILE | 0o755, (first/'radio-start').read_bytes())
        files['bin/hw-start'] = (FILE | 0o755, (first/'hw-start').read_bytes())
        files['bin/firmware-get'] = (FILE | 0o755, (first/'firmware-get').read_bytes())
        files['root/.ssh/authorized_keys'] = (FILE | 0o600, public_key_line(authorized_key))
    # The release config has no /dev/i2c, which power-status opens.
    for tool in ['backlight-policy', 'amixer', 'aplay'] if public else ['backlight-policy', 'power-status', 'amixer', 'aplay']:
        data = (Path(tools)/tool).read_bytes()
        # An empty or foreign binary here would boot, and only fail at init's respawn.
        assert data[:4] == b'\x7fELF' and data[4] == 2 and data[18:20] == b'\xb7\x00', ('not an arm64 ELF', tool)
        files['bin/' + tool] = (FILE | 0o755, data)
    # wireless-regdb's signed database, for cfg80211's country rules.
    for name in ['regulatory.db', 'regulatory.db.p7s']:
        files['lib/firmware/' + name] = (FILE | 0o644, (Path(tools)/name).read_bytes())
    mode, keymap = files['etc/gemini-us.bkeymap']
    files['etc/gemini-us.bkeymap'] = (mode, quiet_brightness_keys(keymap))
    # The calibration record is linked from nvdata at boot, never carried.
    files.pop('lib/firmware/mediatek/mt6797/WIFI.storage', None)
    for d in ['mnt', 'mnt/data', 'nvdata', 'tmp', 'lib/modules', 'lib/modules/' + release]:
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
    if len(sys.argv) not in (6, 7):
        sys.exit(__doc__)
    main(*sys.argv[1:])
