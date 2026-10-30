#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the station boot2 image from a station kernel package.

The kernel and modules come from the Buildbox package, and the board tree
is the package's wifi-service tree through station-dt.sh; the RAM root is
built from a retained soak RAM root by build-station-initramfs.py.
The container and its LK checks are the soak candidates' own.

usage: compose-station.py PACKAGE PARENT_INITRAMFS LID_GUARD OUTPUT_DIR
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BOOT = REPO/'experiments/2026-07-12-boot-contract-recovery/scripts'
NAME, CMDLINE = 'gemini-obs-P', 'bootopt=64S3,32N2,64N2'
DTB = 'mt6797-gemini-pda-wifi-service.dtb'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(package, parent, lid_guard, output):
    package, output = Path(package), Path(output)
    release = (package/'kernel.release').read_text().strip() if (package/'kernel.release').exists() else None
    modules = sorted(package.glob('modules/lib/modules/*/kernel/drivers/net/wireless/mediatek/mt6797/mac.ko'))
    assert len(modules) == 1, ('one mac.ko expected in the package', modules)
    module = modules[0]
    release = release or module.parts[module.parts.index('modules') + 3]
    assert release.endswith('-gemini-a53-station'), release
    config = (package/'kernel.config').read_text()
    for line in ['CONFIG_MODULES=y', 'CONFIG_MT6797_MAC80211=m', 'CONFIG_EXT4_FS=y']:
        assert line in config.splitlines(), line
    output.mkdir(mode=0o700)
    dtb = output/'board.dtb'
    subprocess.run(['sh', str(HERE/'station-dt.sh'), str(package/'dtbs/mediatek'/DTB), str(dtb)],
                   check=True, stdout=subprocess.DEVNULL)
    ram = output/'initramfs.img'
    subprocess.run([sys.executable, str(HERE/'build-station-initramfs.py'), str(parent), str(module),
                    str(lid_guard), release, str(ram)], check=True)
    boot = output/'boot.img'
    subprocess.run([sys.executable, str(BOOT/'build-android-boot-v0.py'),
                    '--kernel', str(package/'Image.gz'), '--ramdisk', str(ram), '--dtb', str(dtb),
                    '--name', NAME, '--cmdline', CMDLINE,
                    '--kernel-addr', '0x40200000', '--ramdisk-addr', '0x45000000',
                    '--second-addr', '0x40f00000', '--tags-addr', '0x44000000',
                    '--lk-android8', '--output', str(boot)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(BOOT/'analyze-lk-boot-image.py'), '--validate-lk',
                    '--expected-image-gz', str(package/'Image.gz'), '--expected-ramdisk', str(ram),
                    '--expected-dtb', str(dtb), '--expected-name', NAME,
                    '--expected-cmdline', CMDLINE, str(boot)], check=True, stdout=subprocess.DEVNULL)
    raw = boot.read_bytes()
    assert len(raw) < 16777216, len(raw)
    padded = output/'boot2-padded.img'
    padded.write_bytes(raw + bytes(16777216 - len(raw)))
    record = {'release': release, 'package': str(package.name), 'parent_initramfs_sha256': sha(parent),
              'image_gz_sha256': sha(package/'Image.gz'), 'dtb_sha256': sha(dtb), 'mac_ko_sha256': sha(module),
              'lid_guard_sha256': sha(lid_guard),
              'initramfs_sha256': sha(ram), 'boot_img_bytes': len(raw), 'boot2_sha256': sha(padded)}
    (output/'station.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
