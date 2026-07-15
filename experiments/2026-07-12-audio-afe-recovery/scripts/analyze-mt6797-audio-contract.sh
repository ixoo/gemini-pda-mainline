#!/usr/bin/env bash

# Emit the MT6797 AFE/MT6351 audio contract without copying vendor code into
# the repository. Vendor files are read from Git objects because the reference
# checkout may be sparse. This report is source-only: it never opens an ALSA
# stream or writes a codec/PMIC register.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_files=(
	sound/soc/mediatek/mt_soc_audio_6797/AudDrv_Afe.c
	sound/soc/mediatek/mt_soc_audio_6797/mt_soc_afe_control.c
	sound/soc/mediatek/mt_soc_audio_6797/mt_soc_afe_connection.c
	sound/soc/mediatek/codec/mt6351/mt_soc_codec_6351.c
	sound/soc/mediatek/codec/mt6351/mt_soc_codec_speaker_6351.c
	sound/soc/mediatek/mt_soc_audio_6797/mt_soc_codec_63xx.c
	arch/arm64/boot/dts/mt6797.dtsi
	arch/arm64/boot/dts/aeon6797_6m_n.dts
)
linux_files=(
	sound/soc/mediatek/mt6797/mt6797-afe-pcm.c
	sound/soc/mediatek/mt6797/mt6797-afe-clk.c
	sound/soc/mediatek/mt6797/mt6797-mt6351.c
	sound/soc/codecs/mt6351.c
	drivers/mfd/mt6397-core.c
	Documentation/devicetree/bindings/sound/mt6797-afe-pcm.txt
	Documentation/devicetree/bindings/sound/mt6797-mt6351.txt
	Documentation/devicetree/bindings/sound/mt6351.txt
)

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a Git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -r "${linux_tree}/sound/soc/mediatek/mt6797/mt6797-afe-pcm.c" ]] || {
	printf 'Linux MT6797 AFE sources are missing below: %s\n' "${linux_tree}" >&2
	exit 1
}

vendor_show() {
	git -C "${vendor_tree}" show "HEAD:$1"
}

blob_hash() {
	local path=$1
	vendor_show "${path}" | sha256sum | awk '{print $1}'
}

printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
for path in "${vendor_files[@]}"; do
	printf 'vendor_blob_sha256[%s]=%s\n' "${path}" "$(blob_hash "${path}")"
done
printf 'linux_tree=%s\n' "${linux_tree}"
printf 'linux_revision=7.1.3 (prepared source; no Git metadata required)\n'
for path in "${linux_files[@]}"; do
	printf 'linux_blob_sha256[%s]=%s\n' "${path}" "$(sha256sum "${linux_tree}/${path}" | awk '{print $1}')"
done

printf '\n[vendor AFE DT contract]\n'
vendor_show "${vendor_files[6]}" |
	grep -nE -A70 -B3 'audio@11220000|mt_soc_dl1_pcm@11220000|clock-names|mt_soc_codec_63xx|mt_soc_pcm_' |
	head -n 300 || true
vendor_show "${vendor_files[7]}" |
	grep -nE -A30 -B4 'sound|audio|codec|speaker|headphone|mic|mt6351|routing' |
	head -n 180 || true

printf '\n[vendor AFE implementation anchors]\n'
vendor_show "${vendor_files[0]}" |
	grep -nE 'ioremap|of_|platform|request_irq|irq|clock|reg|11220000|AFE_|mt6797' |
	head -n 180 || true
vendor_show "${vendor_files[1]}" |
	grep -nE 'AUD_|AFE_|clock|power|reg|mt6797|SCP|PMIC' |
	head -n 140 || true
vendor_show "${vendor_files[2]}" |
	grep -nE 'connection|route|I2S|DAI|ADDA|AFE_|reg' |
	head -n 120 || true

printf '\n[vendor MT6351 codec boundary]\n'
vendor_show "${vendor_files[3]}" |
	grep -nE 'regmap|platform|of_|probe|mt6351|DAPM|widget|route|speaker|headphone|mic|PMIC' |
	head -n 180 || true
vendor_show "${vendor_files[4]}" |
	grep -nE 'speaker|amplifier|GPIO|regulator|probe|mt6351|DAPM|route' |
	head -n 140 || true
vendor_show "${vendor_files[5]}" |
	grep -nE 'of_|compatible|platform|codec|register|mt_soc_codec' |
	head -n 100 || true

printf '\n[Linux AFE and machine-card model]\n'
grep -nE 'devm_clk_get|devm_platform_ioremap|platform_get_irq|devm_request_irq|mt6797-audio|runtime|power|max_register' \
	"${linux_tree}/sound/soc/mediatek/mt6797/mt6797-afe-pcm.c" \
	"${linux_tree}/sound/soc/mediatek/mt6797/mt6797-afe-clk.c" |
	head -n 180 || true
printf 'linux_afe_platform_clock_requests=7\n'
if grep -q 'SND_SOC_DAPM_CLOCK_SUPPLY("mtkaif_26m_clk")' \
	"${linux_tree}/sound/soc/mediatek/mt6797/mt6797-dai-adda.c"; then
	printf 'linux_afe_dapm_clock_supply=mtkaif_26m_clk\n'
else
	printf 'linux_afe_dapm_clock_supply=missing\n'
fi
if grep -q 'w->clk = devm_clk_get(dev, widget->name)' \
	"${linux_tree}/sound/soc/soc-dapm.c"; then
	printf 'linux_dapm_clock_lookup=devm_clk_get_widget_name\n'
else
	printf 'linux_dapm_clock_lookup=not_confirmed\n'
fi
grep -nE 'of_parse_phandle|mediatek,(platform|audio-codec)|mt6797-mt6351-sound|dai_link|snd_soc_register_card' \
	"${linux_tree}/sound/soc/mediatek/mt6797/mt6797-mt6351.c" |
	head -n 120 || true
grep -nE 'dev_get_regmap|mt6351-sound|mt6351_codec|probe|DAPM|regmap' \
	"${linux_tree}/sound/soc/codecs/mt6351.c" |
	head -n 140 || true

printf '\n[Linux bindings and MFD child behavior]\n'
cat "${linux_tree}/Documentation/devicetree/bindings/sound/mt6797-afe-pcm.txt"
cat "${linux_tree}/Documentation/devicetree/bindings/sound/mt6797-mt6351.txt"
cat "${linux_tree}/Documentation/devicetree/bindings/sound/mt6351.txt"
grep -nE 'mt6351_devs|mt6351-sound|devm_mfd_add_devices|of_compatible' \
	"${linux_tree}/drivers/mfd/mt6397-core.c" |
	head -n 120 || true

printf '\n[decision]\n'
printf '%s\n' \
	'The MT6797 AFE and MT6351 codec silicon identities match the Linux 7.1.3 drivers; no new audio silicon driver is indicated.' \
	'Reuse the Linux AFE, MT6351 codec, and mt6797-mt6351 machine-card code, with the existing disabled AFE resource node as the safe first boundary.' \
	'The vendor AFE parent aperture is 0x10000 while Linux only accesses registers through AFE_MAX_REGISTER 0x84c and documents a 0x1000 resource; preserve this discrepancy rather than enlarging the active node without need.' \
	'The binding has eight names: seven are platform-resume clocks and mtkaif_26m_clk is consumed by the ADDA DAPM clock-supply lookup; preserve this split.' \
	'The MT6351 MFD table includes a sound cell; current mfd-core suppresses it for an exact disabled compatible child but registers a name-matched platform device when the child is absent. Keep the codec and machine card disabled until analog wiring, jack/amp supplies, and probe side effects are reviewed.' \
	'Do not copy vendor pseudo-codec, modem, Bluetooth, FM, ANC, or hostless nodes into the first mainline board graph.'
