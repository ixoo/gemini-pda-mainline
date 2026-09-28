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
The [checksum-only receipt](results/candidate.json) pins all offline inputs.
Its `physical_admission: false` records the pre-install preparation state;
the later device attempt is reported separately below.

## First host-stage attempt

The reviewed installer resolved logical boot2 from the live GPT in Gemian boot
`0dd84ec1-2e97-4f20-962d-b4edf0b22d0c`, passed the device guard, found the
expected previous full checksum, wrote the new image, and matched its full
readback. It confirmed clean shutdown. The 900-second watcher was then armed
and observed preloader followed by the MediaTek `20ff` USB stage, which remained
through expiry. It saw no mainline USB route and made no device SSH attempt;
the Gemian LAN endpoint also timed out. The [sanitized attempt receipt](results/attempt-1.json)
pins the private deployment and stage-log checksums.

Physical boot2 selection and screen state remain unconfirmed for this attempt.
There is no mainline boot ID, kernel log, HIF result, A53 regression or verified
Gemian return. Do not infer an HIF failure from `20ff` or repeat an identical
host-only watch without a decision-changing physical observation. The verified
boot2 image remains installed; the device has not been otherwise manipulated.

The owner later reported that boot2 started. A second finite watch was armed
after that report, while the host still showed `20ff`. Its [receipt](results/attempt-2.json)
records no USB-stage transition or mainline route over 900 seconds, and no
device SSH attempt. Because the watch started after the reported selection, it
cannot establish that this selection passed through preloader. The screen state
remains pending. Neither attempt reached the kernel log, so the HIF hypothesis
is still untested. Establish the device's physical state before any recovery or
another boot; a third identical host-only watch has no decision value.

## Prearmed mainline result

The owner then confirmed the PDA was powered off. With the same verified boot2
image still installed, a fresh collector was armed before physical boot2
selection. The stale `20ff` listing cleared, the mainline gadget appeared, and
the authenticated collector obtained a changed mainline boot ID and complete
sealed kernel log. The [sanitized runtime receipt](results/runtime-1.json) pins
the private watch, log and result hashes. The same-boot power, chip-ID, powered
EMI and reset-release gates passed. Before function enable, BT and Wi-Fi VCN33
control both read `0x1800`, and IOEx/IORx read `0x00/0x00`. After enabling Wi-Fi
function 1, IOEx/IORx both read `0x02`; WCIR read `0x00100279`. There was one
ready record and no HIF stop record. The A53 RAM-service regression passed.
The passive WLAN child also requested the staged firmware and accepted its
complete four-section plan: two ordinary sections of 14,832 bytes and two EMI
sections of 396,688 bytes. No section was submitted to hardware.

The reviewed recovery reached a changed Gemian boot, and an independent
read-only check found `wlan0/carrier=1`. This validates the one-shot pre-firmware
HIF sequence in one boot. It does not establish firmware execution, EMI writer
exclusion or policy, AP-DMA ownership, radio operation, or usable mainline
Wi-Fi. The next executor needs a same-boot admission gate, owned EMI protection
transaction and retained-fault resource lifetime before a firmware transfer;
another firmware-request-only probe is unnecessary.
