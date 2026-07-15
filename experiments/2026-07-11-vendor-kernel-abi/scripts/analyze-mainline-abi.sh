#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Turn the private ELF interface inventory into a sanitized Linux 7.1.3 gap
# report. The report contains counts, presence checks, and source hashes only;
# it does not print proprietary strings or copy extracted binaries.

set -euo pipefail

INTERFACES_TSV=${INTERFACES_TSV:-"$HOME/reverse-engineering/work/vendor-kernel-abi/interfaces.tsv"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
SCANNER=${SCANNER:-"/mnt/gemini-pda-mainline/experiments/2026-07-11-vendor-kernel-abi/scripts/scan-interfaces.py"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v sha256sum >/dev/null || die "sha256sum is required"
command -v awk >/dev/null || die "awk is required"
command -v rg >/dev/null || die "rg is required"

[[ -f "$INTERFACES_TSV" ]] || die "interface inventory is missing: $INTERFACES_TSV"
[[ -d "$LINUX_TREE" ]] || die "Linux source tree is missing: $LINUX_TREE"

echo "Vendor userspace ABI to Linux 7.1.3 gap audit"
echo "interfaces_tsv=$INTERFACES_TSV"
echo "interfaces_sha256=$(sha256sum "$INTERFACES_TSV" | awk '{print $1}')"
echo "scanner=$SCANNER"
if [[ -f "$SCANNER" ]]; then
	echo "scanner_sha256=$(sha256sum "$SCANNER" | awk '{print $1}')"
fi
echo "linux_tree=$LINUX_TREE"
if [[ -f "$LINUX_TREE/Makefile" ]]; then
	printf 'linux_version='
	make -s -C "$LINUX_TREE" kernelversion
fi

echo
echo "[inventory counts]"
awk -F '\t' 'NR > 1 { count[$1]++ } END { for (kind in count) print kind "=" count[kind] }' \
	"$INTERFACES_TSV" | sort

echo
echo "[sanitized scanner-string matches]"
for family in \
	"display_fb|/dev/graphics/fb" \
	"display_manager|/dev/mtk_disp_mgr" \
	"legacy_ion|/dev/ion" \
	"legacy_sync|/dev/swsync" \
	"sensor_misc|/dev/hwmsensor" \
	"sensor_batch|/dev/m_batch_misc" \
	"thermal_proc|/proc/mtktz" \
	"audio_accdet|/dev/accdet" \
	"wmt_character|/dev/stpwmt" \
	"wifi_character|/dev/wmtWifi" \
	"gpu_character|/dev/mali0"; do
	label=${family%%|*}
	needle=${family#*|}
	if rg -F -q "$needle" "$INTERFACES_TSV"; then
		printf '%s=scan_match\n' "$label"
	else
		printf '%s=no_scan_match\n' "$label"
	fi
done

echo
echo "[Linux replacement source hashes]"
for path in \
	drivers/gpu/drm/mediatek/mtk_drm_drv.c \
	drivers/dma-buf/dma-buf.c \
	drivers/dma-buf/sync_file.c \
	drivers/iio/industrialio-core.c \
	drivers/thermal/thermal_core.c \
	sound/soc/mediatek/mt6797/mt6797-afe-pcm.c \
	drivers/usb/roles/class.c \
	net/bluetooth/hci_core.c \
	drivers/gnss/serial.c; do
	if [[ -f "$LINUX_TREE/$path" ]]; then
		printf '%s ' "$path"
		sha256sum "$LINUX_TREE/$path" | awk '{print $1}'
	else
		printf '%s missing\n' "$path"
	fi
done

echo
echo "[mainline decisions]"
cat <<'EOF'
display_fb -> DRM/KMS, dma-buf, dma-fence/sync_file, and MediaTek IOMMU;
  do not reproduce DISP_IOCTL_* or the framebuffer session manager.
sensor_misc/sensor_batch -> physical IIO/input devices plus userspace fusion;
  do not create kernel devices for virtual sensor classes.
thermal_proc -> thermal zones, cooling devices, and OPP throttling only after
  MT6797 calibration and validity rules are recovered.
audio_accdet -> ASoC/ALSA DAPM, standard jack detection, and board amplifier;
  keep modem speech and calibration as separate boundaries.
wmt_character/wifi_character -> standard HCI/cfg80211 interfaces behind a new
  MT6797 transport/firmware owner; do not expose /dev/stpwmt or /dev/wmtWifi.
gpu_character -> Panfrost plus standard clocks, regulators, power domains,
  reset, OPP, and its independent GPU MMU; do not carry GED or /dev/mali0.
EOF
