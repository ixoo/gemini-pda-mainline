# One-shot powered MT6797 CONSYS chip-ID probe

The preceding [power-on result](../2026-09-28-mt6797-wifi-power-probe/results/runtime-1.json)
showed the modern provider's point-in-time dual-status ON result while CONMCU
reset remained asserted. It did not access the CONSYS device window. The
selected [Gemian source](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L405-L450)
reads `0x18070008` after the power-domain transition and before releasing
CONMCU reset. Its selected AHB-clock branch is disabled, as established in the
[power-domain contract](../2026-09-05-mt6797-wifi-contract/POWER_DOMAIN.md).
Gemian's instrumented boot reported `0x0279`; that reference value was
obtained after the vendor transition in a different boot.

This profile adds one exact four-byte, read-only MMIO resource for that chip-ID
register. It keeps the prior one-shot admission and retained power effects.
After a successful ON check it waits 30 µs, checks both ON status and asserted
CONMCU reset again, then performs exactly one `readl` and logs the value. It
does not release reset, write the CONSYS window, transfer firmware, register a
radio or power off. The incremental [patch](../../patches/proposals/0037-soc-mediatek-sample-powered-MT6797-CONSYS-chip-id.patch)
is selected only by `mt6797-a53-wifi-chip-id-probe`. Its synthetic author is
not DCO-certified.

Before any device boot, require a clean pushed Buildbox build, matching kernel
package and boot2 candidate, guarded live-GPT installation, full readback, and
a fresh finite host collector. The hypothesis is that the powered,
reset-held window returns `0x0279`. One matching record, complete kernel log,
changed mainline boot identity and confirmed Gemian return would admit a
subsequent reset/ACR design. An unmapped-resource refusal or skipped read
points to admission or power/reset state. A different ID is a hardware or
source-contract discrepancy; do not release reset. A bus fault requires
preserving available evidence and reviewed Gemian recovery, with no same-image
retry. None of these outcomes alone demonstrates firmware execution or Wi-Fi.
