# Gated Wi-Fi HIF startup probe

The [reset-release boot](../2026-09-28-mt6797-wifi-reset-release/results/runtime-1.json)
confirmed that CONN remained ON, CONMCU reset released, and the chip ID stayed
`0x0279`. It did not turn on the Wi-Fi VCN33 rail or access the AHB HIF.
This experiment tests one additional startup boundary before firmware or DMA.

The pinned Gemian gen3 HIF source calls `mtk_wcn_consys_hw_wifi_paldo_ctrl(1)`
before WLAN probe. Its compiled Device Tree path sets VCN33-Wi-Fi to 3.3 V and
enables its regulator. `sdio_open()` then enables function 1 by reading CCCR
IOEx with CMD52, setting bit 1, and reading IORx before `glSetHifInfo()` reads
WCIR with a function-1, byte-mode CMD53 transfer. The `wifi-dma` clock lookup
and PDMA setup occur after that WCIR read. The source files are
`connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c` and
`connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/{ahb.c,sdio_bus_driver.c,include/sdio.h}`
in the retained Gemian tree. This is a source sequence, not yet a mainline
hardware observation.

The `mt6797-a53-wifi-hif-probe` profile adds one format-patch after the tested
reset-release candidate. The CONSYS owner exclusively claims the exact
`0x180f0000+0x1100` HIF aperture before any power effect. If all existing
power, chip-ID and powered-EMI gates pass, it performs the one-shot ACR and
reset release, verifies that release, then checks that neither BT nor Wi-Fi
VCN33 control is active before changing their shared voltage selector. It
enables only VCN33-Wi-Fi at 3.3 V.
It verifies the regulator and CONN/reset state again, requires IOEx and IORx
initially zero, sets only function 1 in IOEx, checks both register readbacks,
and reads WCIR once. It retains power and function state for the reviewed
recovery path. There is no block-size, IRQ, firmware, EMI-policy or DMA action.

The hypothesis is that IOEx/IORx both become `0x02` and WCIR's low 16 bits
equal `0x0279`. If the existing gate fails, no HIF access occurs. A missing
resource or initial nonzero IOEx/IORx refuses before function enable. A failed
readback or WCIR mismatch stops with exact values in the retained log and no
retry. A matching WCIR admits HIF transport for later firmware work but is
not working Wi-Fi.

Before device use, require a clean pushed Buildbox build, validated package
and candidate, guarded live-GPT boot2 installation and full readback, clean
shutdown, a prearmed finite USB collector, and owner physical boot2 selection.
Preserve the complete mainline log and regression checks, then return through
the reviewed native recovery path and confirm a changed-boot Gemian Wi-Fi
carrier. The format-patch has synthetic non-certifying authorship and is not
an upstream submission.

## Prepared candidate

The clean pushed commit `e0a8f36fa0a59d98f6ca20ee8fe3c1ac1f4fa68d`
built on Buildbox with `KERNEL_PROFILE=mt6797-a53-wifi-hif-probe`. Its
validated package has inventory SHA-256
`d4e691b8d9bf80c44d0e6db272af27cbf0ca26ecd0469dfce82ad151462c1f4c`.
The focused binding/example check and compiled Gemini DTB schema check passed
with the retained `dtschema-2026.9` environment. The private RAM root retains
52 members and identical firmware bytes; only `init`'s release gate changed.
The candidate preserves the observed reset-release board DTB and adds only the
HIF resource and one-shot flag. The LK boot-container validator passed. Its
full 16-MiB boot2 SHA-256 is
`8e6d80e9c22b658ee8e79c7e4813d0ad80365d26907f2c374a69a2193c1c9049`.
The [checksum-only receipt](results/candidate.json) pins all inputs. No device
action has occurred for this candidate; `physical_admission` remains false
until the guarded installer and collector are ready.
