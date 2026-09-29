# One-shot WMT memory setup

The [first firmware START](../2026-09-28-mt6797-firmware-start-probe/results/runtime-1.json)
ended in a workqueue panic. Its compiled CONSYS owner maps the shared remap
word at `0x10001340` but never reads or writes it. An earlier passive mainline
boot read `0x180e0000` there, with the common mapping disabled. The pinned
[Gemian source](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L1105-L1138)
programs region 19, ORs the reservation's MiB address and enable bit into that
word, then clears the first 343 KiB of the second 512 KiB. Its
[header](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h#L192-L198)
defines the exact clear length. The missing remap is a source-proven gap, not
yet an attributed cause of the panic.

[Patch 0048](../../patches/proposals/0048-soc-mediatek-prepare-one-shot-MT6797-WMT-memory.patch)
adds a root-only, single-use `region19_prepare` trigger to the existing passive
region-19 observer. It accepts only a confirmed-OFF CONN domain, the observed
remap baseline, a positive secure-read control, and empty region 18/19/23
registers. It requests the Gemian region-19 policy, checks the secure status
and exact readback, writes and checks the remap, then clears and verifies the
first 343 KiB. It retains state after any attempted transition. No CONN power,
reset release, firmware, DMA or radio action is in this candidate. The profile
selects the patch only for `mt6797-a53-wifi-region19-wmtmem`; older profiles
retain their selections.

Before the trigger, capture the complete 512 KiB private window twice in the
same authenticated boot and preserve both reads. The one-boot hypothesis is
that the admitted policy and remap read back exactly and the bounded WMT clear
leaves the rest of the captured window unchanged. Preserve a full private
post-trigger read, complete kernel log, boot identity, A53 regression and a
changed-boot Gemian return. A failed admission, secure result, remap readback,
clear verification, log, regression or return stops this line of execution;
none permits firmware START or an identical replay. A successful diagnostic
would establish only AP-visible setup and readback, not effective CONSYS
permissions, region-overlap priority or Wi-Fi support. Those unresolved facts
must inform a distinct, reviewed firmware candidate.

The named profile built from clean pushed commit
`41541e37fd451ff45ec0b8a0c0df0ddc1ed4d190` on Buildbox. The validated
package inventory is
`433d441def588063ee1aa5dfa5ddb8982114e78ae9a6cd1ff623c5aa21f8369c`.
The compiled Gemini DTB matches the preceding passive profile byte for byte;
the new kernel contains `region19_prepare`. The private RAM root changed only
its release gate. The [candidate receipt](results/candidate.json) pins the
checked LK container and full boot2 image SHA-256
`0083834cea0e62d004dc92bf087c8167dfcf6dbbe6cf764a3e8d04d487261b8f`.

The [guarded installer](install-passive.py) accepts only the preceding boot2
checksum, resolves logical `boot2` from live GPT and uses the project device
guard. A matching full-partition readback precedes a clean shutdown; the owner
selects boot2 physically. The [watcher](watch-boot.py) pre-arms the direct USB
route. Its [collector](capture-private.py) verifies release and boot ID, saves
two identical private pre-write windows, sends one sysfs trigger, then saves a
full post-attempt window after a reported trigger error when USB SSH remains
available. The
[session collector](passive-host.py) seals the log, checks exact WMT records,
runs the A53 regression and uses the reviewed return to Gemian. Device
observations are pending. Raw window contents, firmware, credentials and full
logs stay in ignored private artifacts.
