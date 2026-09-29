# One-shot mainline WLAN EMI copy diagnostic

The prior [policy probe](../2026-09-28-mt6797-emi-set-probe/README.md) showed
that this mainline boot can request and directly read back the temporary
region-18 policy `0xb6da28` and final `0xb6da2d` over the first 512 KiB of
the boot-reserved CONSYS window. It transferred no firmware. The working
instrumented Gemian v9 boot copied both WLAN EMI sections under those requested
policies and reached carrier, but that does not prove the AP can write the
mainline reservation or that the CONSYS master can fetch it. This proposal
measures the AP copy/readback step; it never starts firmware.

[Patch 0044](../../patches/proposals/0044-soc-mediatek-copy-bounded-MT6797-WLAN-EMI.patch)
extends the named one-shot owner, not the default board profile. The
`mt6797-a53-wifi-emi-copy-probe` profile adds one DT flag to the already tested
power/reset/HIF/EMI gates. In the same boot it requires the selector, nonzero
EMI read control and empty region-18/19/23 ranges; obtains and validates the
complete pinned MTKE image through `request_firmware()`; and maps only the first
512 KiB of the existing 2 MiB no-map reservation. It then makes the first
region-18 secure call, requires zero signed status and direct readback of the
requested range/policy, copies the two parsed EMI sections using bounded
`memcpy_toio`, and compares each copied byte with `memcpy_fromio` before the
final secure call. The region-18 final request is attempted once even after a
partial copy failure, provided the temporary policy had matched. The owner
retains the powered resources, image and mapping after any secure or copy
effect until the reviewed reboot/recovery path. It does not issue ordinary
HIF DOWNLOAD_CONFIG/PDA, firmware START, packet DMA, radio or calibration
operations.

The **one-boot hypothesis** is that AP writes to the reserved WLAN EMI window
under the accepted temporary policy can be read back byte-for-byte for both
pinned firmware sections, and the final region-18 policy can then be read
back. The unique observation joins exact boot2 checksum and changed mainline
boot identity to the two secure statuses/readbacks, count of fully copied
sections and bytes, complete sealed log, A53 regression and changed-boot
Gemian return. Precondition refusal makes no secure set or memory write and
redirects identity/plan investigation. A failed first set/readback makes no
copy and stops with state held. Copy or verification failure leads to one
bounded final-seal attempt and retained state, with no replay; the result
redirects mapping/policy investigation. A failed final seal also stops and
retains state. Success admits a later complete-section executor design but
does not prove effective CONSYS fetch permissions, master-domain routing,
region-23 overlap behavior, independent-writer exclusion, firmware execution
or usable mainline Wi-Fi. The policy-only image must not be repeated.

The maximum new effect is two region-18 secure set calls plus 396,688 bytes
written to, and read from, the owned reserved WLAN subrange, once per boot.
The existing one-shot power/reset/HIF effects remain. No software deadline
can cancel a stalled MMIO or SMC; an unexpected external abort, logger loss,
missing identity, regression failure or recovery mismatch stops this
candidate. Preserve available evidence before the already reviewed native
recovery. Do not use an automatic boot2 reboot or an alternate partition.

Build only the clean pushed commit with `./scripts/build-kernel --backend
buildbox` and the exact named profile. Validate the full package, DT binding
and built Gemini DTB before assembling a private boot2 candidate with the
same retained firmware and RAM root. The reviewed live-GPT guard, predecessor,
full-partition readback and clean shutdown remain required; the owner selects
boot2 physically. Raw logs, firmware, credentials and the boot image remain
ignored under `artifacts/`. The patch is an internal experiment with synthetic,
non-certifying authorship, not an upstream submission.
