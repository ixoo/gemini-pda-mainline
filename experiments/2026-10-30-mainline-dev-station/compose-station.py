#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the station boot2 image from a station kernel package.

The kernel and modules come from the Buildbox package, and the board tree
is the package's station tree (the wifi-service tree with SoC thermal)
through station-dt.sh; the RAM root is
built from a retained soak RAM root by build-station-initramfs.py.
The container and its LK checks are the soak candidates' own.

With AUTHORIZED_KEY (the tester's one-line SSH public key) it composes the
release instead: a mt6797-a53-release package and release/build-parent.sh's public
parent and tools, with no keys but that one and no firmware.

usage: compose-station.py PACKAGE PARENT_INITRAMFS TOOLS OUTPUT_DIR [AUTHORIZED_KEY]
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
DTB = 'mt6797-gemini-pda-station-a72.dtb'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(package, parent, tools, output, authorized_key=None):
    public = authorized_key is not None
    package, output = Path(package), Path(output)
    release = (package/'kernel.release').read_text().strip() if (package/'kernel.release').exists() else None
    modules = []
    for path in ['net/wireless/mediatek/mt6797/mac.ko', 'net/wireless/mediatek/mt6797/mt6797-wlan-core.ko',
                 'soc/mediatek/mt6797-consys.ko', 'input/misc/gemini-lid.ko'] + ([] if public else ['leds/rgb/leds-aw9120.ko']):
        found = sorted(package.glob('modules/lib/modules/*/kernel/drivers/' + path))
        assert len(found) == 1, ('one module expected in the package', path, found)
        modules += found
    # Loaded by audio-start, in its order.
    for path in ['core/snd.ko', 'core/snd-timer.ko', 'core/snd-pcm.ko', 'core/snd-pcm-dmaengine.ko',
                 'soc/snd-soc-core.ko', 'soc/mediatek/common/snd-soc-mtk-common.ko',
                 'soc/codecs/snd-soc-mt6351.ko', 'soc/codecs/snd-soc-aw8738.ko',
                 'soc/mediatek/mt6797/snd-soc-mt6797-afe.ko', 'soc/mediatek/mt6797/mt6797-mt6351.ko']:
        found = sorted(package.glob('modules/lib/modules/*/kernel/sound/' + path))
        assert len(found) == 1, ('one module expected in the package', path, found)
        modules += found
    # Loaded by display-start, in its order.
    for path in ['phy/mediatek/phy-mtk-mipi-dsi-drv.ko', 'clk/mediatek/clk-mt6797-mm.ko',
                 'soc/mediatek/mtk-mmsys.ko', 'soc/mediatek/mtk-mutex.ko',
                 'gpu/drm/drm_panel_orientation_quirks.ko', 'gpu/drm/drm.ko',
                 'gpu/drm/panel/panel-novatek-nt36672e.ko', 'gpu/drm/drm_kms_helper.ko',
                 'gpu/drm/drm_dma_helper.ko', 'media/cec/core/cec.ko',
                 'gpu/drm/display/drm_display_helper.ko', 'gpu/drm/clients/drm_client_lib.ko',
                 'gpu/drm/mediatek/mediatek-drm.ko']:
        found = sorted(package.glob('modules/lib/modules/*/kernel/drivers/' + path))
        assert len(found) == 1, ('one module expected in the package', path, found)
        modules += found
    module = modules[0]
    release = release or module.parts[module.parts.index('modules') + 3]
    assert release.endswith('-gemini-a53-release' if public else '-gemini-a53-station'), release
    config = (package/'kernel.config').read_text()
    for line in ['CONFIG_MODULES=y', 'CONFIG_MT6797_MAC80211=m', 'CONFIG_MT6797_HIF_CORE=m',
                 'CONFIG_MTK_MT6797_CONSYS=m', 'CONFIG_INPUT_GEMINI_LID=m', 'CONFIG_MTK_SOC_THERMAL=y', 'CONFIG_THERMAL=y',
                 'CONFIG_MEDIATEK_MT6359_AUXADC=y', 'CONFIG_GENERIC_ADC_THERMAL=y',
                 'CONFIG_EXT4_FS=y', 'CONFIG_CHARGER_BQ25890=y', 'CONFIG_DRM_FBDEV_EMULATION=y']:
        assert line in config.splitlines(), line
    assert public or 'CONFIG_LEDS_AW9120=m' in config.splitlines()
    for line in ['# CONFIG_DEVMEM is not set', '# CONFIG_I2C_CHARDEV is not set', '# CONFIG_DEBUG_FS is not set',
                 'CONFIG_EXTRA_FIRMWARE=""'] if public else []:
        assert line in config.splitlines(), line
    output.mkdir(mode=0o700)
    dtb = output/'board.dtb'
    subprocess.run(['sh', str(HERE/'station-dt.sh'), str(package/'dtbs/mediatek'/DTB), str(dtb)],
                   check=True, stdout=subprocess.DEVNULL)
    ram = output/'initramfs.img'
    subprocess.run([sys.executable, str(HERE/'build-station-initramfs.py'), str(parent), ':'.join(map(str, modules)),
                    str(tools), release, str(ram)] + ([str(authorized_key)] if public else []), check=True)
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
              'image_gz_sha256': sha(package/'Image.gz'), 'dtb_sha256': sha(dtb), 'modules_sha256': {m.name: sha(m) for m in modules},
              'backlight_policy_sha256': sha(Path(tools)/'backlight-policy'),
              **({} if public else {'power_status_sha256': sha(Path(tools)/'power-status')}),
              'regulatory_db_sha256': sha(Path(tools)/'regulatory.db'),
              'amixer_sha256': sha(Path(tools)/'amixer'), 'aplay_sha256': sha(Path(tools)/'aplay'),
              'initramfs_sha256': sha(ram), 'boot_img_bytes': len(raw), 'boot2_sha256': sha(padded)}
    (output/'station.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    if len(sys.argv) not in (5, 6):
        sys.exit(__doc__)
    main(*sys.argv[1:])
