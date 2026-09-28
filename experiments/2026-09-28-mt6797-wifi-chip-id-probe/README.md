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

## Prepared candidate

The clean Buildbox build of commit
`82dfa4994b0f8df808bb33a1116dd74705a5a077` produced validated package
`451a3794a51952ca879a495446101bb987dd037c29a081e5f0235fb597a37c41`
with release `7.1.3-gemini-a53-wifi-chip-id-probe`. The exact binding passed
`dt-doc-validate`, and the compiled Gemini DTB passed focused `dt-validate`
against that binding. The DTB's `reg` and `reg-names` readback shows the
additional four-byte `0x18070008` entry. The broader DT validator reported
an unrelated `keyboard-matrix-col-pins` core-schema type warning; the focused
CONSYS validation emitted no finding. A full `dt_binding_check` was not run
because Buildbox lacks the dtschema tools; the separate validation VM supplied
the focused schema tools, not a kernel build.

The [checksum-only candidate receipt](results/candidate.json) pins the exact
Buildbox package, parent power-on image, 52-member private RAM root, boot
container and full boot2 padding. The padded boot2 SHA-256 is
`18e21f27326a48681acb532080e84d6989276934ce645a9ce1d2fe2620fa2cb5`.
Private image and retained firmware bytes remain ignored. The derived guarded
installer passed offline syntax and ShellCheck, with the preceding installed
power image pinned as its only permitted predecessor. No device action or
chip-ID result is claimed by these preparation checks.

## Hardware result

The guarded boot2 installer matched the full candidate readback and shut down
the PDA. The owner selected boot2. In changed mainline boot
`aec46336-db37-43e1-8c8f-181166b07649`, one complete sealed kernel log
recorded the CONN domain confirmed ON with CONMCU reset held, followed by one
chip-ID read of `0x00000000`. There was no power-probe stop or chip-ID skip.
The four-section retained-firmware plan passed without executing firmware.
The A53 RAM-service regression passed, and the reviewed return reached changed
Gemian boot `4d6fe3bf-c67e-4a5d-a238-7336c1144e53`; an independent bounded
read found `wlan0` carrier 1. The [sanitized runtime receipt](results/runtime-1.json)
pins the candidate, boot identities, deployment summary and complete private
log checksum. Raw logs and firmware remain outside Git.

The zero is a negative result for this exact one-shot 30-µs sample, not proof
that the register stays zero. The selected Gemian source permits delayed
20-ms retry reads after an initial miss. No delayed sample, reset release,
firmware execution or mainline Wi-Fi operation was tested. A follow-up must
distinguish settling from a power, clock or bus-access discrepancy before any
reset or firmware step.
