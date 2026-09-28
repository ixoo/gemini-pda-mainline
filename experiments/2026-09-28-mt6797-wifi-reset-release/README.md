# Gated CONMCU reset-release diagnostic

The [powered EMI boot](../2026-09-28-mt6797-wifi-powered-emi/results/runtime-1.json)
found empty region-18/19/23 ranges with a nonzero secure-read control after
CONN reached ON and chip ID settled to `0x0279`. It did not release CONMCU
reset. The selected Gemian `CONFIG_OF` path sets MCU ACR bit 18 before its
TOPRGU release and waits 20 ms afterward. This experiment tests that next
common-owner transition once, without an EMI write or firmware transfer.

The named `mt6797-a53-wifi-reset-release` profile extends the previous
candidate with [patch 0040](../../patches/proposals/0040-soc-mediatek-probe-gated-MT6797-CONMCU-reset-release.patch).
It requires confirmed CONN ON, held CONMCU reset, chip ID `0x0279`, and a
same-boot powered EMI snapshot: region-1 control exactly `0x44604460`, both
region-23 range reads zero, and region-18/19 range and policy reads zero.
Only then does it read and set ACR bit 18 through its four-byte claimed
resource, require readback, release its exclusive TOPRGU reset once, and
check reset, domain and chip ID after 20 ms. The owner retains all power and
reset effects on success or failure until reviewed recovery. The patch has
synthetic non-certifying authorship and is not an upstream submission.

The hypothesis is that the release returns success, TOPRGU status becomes
deasserted, CONN remains confirmed ON and chip ID remains `0x0279`. A failed
power, reset, ID or EMI gate stops before the ACR write. Failed ACR readback
keeps reset held. A reset operation or post-release check failure retains
state, preserves logs and proceeds only through reviewed recovery, with no
second release, speculative reassertion, firmware transfer, EMI policy write,
radio action or DMA use. A successful result admits subsequent HIF/downloader
work; it does not prove firmware readiness or usable Wi-Fi.

Before device use, require a clean pushed Buildbox build, validated package
and boot candidate, live-GPT guarded boot2 installation with matching full
readback, clean shutdown, an armed finite USB collector, and physical boot2
selection by the owner. Preserve the complete log and A53 regression, then
confirm a changed-boot Gemian Wi-Fi return through the reviewed path.
