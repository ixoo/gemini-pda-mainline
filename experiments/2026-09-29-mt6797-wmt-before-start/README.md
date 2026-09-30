# WMT preparation before one deferred WLAN firmware start

The [first firmware START](../2026-09-28-mt6797-firmware-start-probe/results/runtime-1.json)
submitted both ordinary sections, then panicked in delayed-work scheduling
without a WLAN-ready result. The [later WMT setup](../2026-09-29-mt6797-region19-wmt-memory/results/runtime-1.json)
proved a separate missing prepower step: a region-19 policy, shared remap and
343 KiB clear read back with CONN held off. It did not run firmware or explain
the panic. This distinct candidate tests whether that setup changes the START
outcome, while identifying the workqueue if the same null-pool fault recurs.

The named `mt6797-a53-wifi-wmt-start` profile selects three additional
format-patches after the validated WMT observer. Patch 0049 permits the
deferred combination in the binding; patch 0050 keeps the active resources
idle at probe and exposes a root-only, single-use
`firmware_start_after_wmt` trigger. The trigger requires completed one-shot
WMT setup and rechecks the OFF domain, region 19, empty regions 18/23 and
the remap immediately before the existing bounded power, EMI-copy and HIF
firmware-start path. Patch 0051 logs the workqueue and work function only if
the previous null-pool condition recurs; normal queueing is unchanged. These
are internal diagnostics with synthetic non-certifying authorship, not
upstream submissions or usable Wi-Fi support.

The boot hypothesis is that the prepared WMT control window permits the
previously accepted CONFIG/PDA and one START to reach a WLAN-ready result
without the delayed-work panic. First validate the exact build, package,
firmware plan, DT flags and full boot2 image. Install only through the
reviewed live-GPT `boot2` guard and full readback, then shut down cleanly;
the owner physically selects boot2 after the direct USB watcher is armed.
Verify the new boot ID and release. Preserve two equal, full 512 KiB private
region-19 reads *before* a write. The baseline root mounts `/sys` read-only:
temporarily remount it read-write for one `region19_prepare` write, restore
read-only, and verify the full post-window clear and unchanged suffix. Only
then remount briefly for one `firmware_start_after_wmt` write and restore it.
Keep the complete log, A53 regression if the boot survives, and the reviewed
changed-boot Gemian return. Private windows, firmware, credentials and full
logs remain ignored under `artifacts/`.

A WMT admission refusal or mismatched window forbids START. A firmware
precondition, CONFIG/PDA, policy or readiness failure forbids replay and
directs its own diagnosis. A recurrence of the null-pool panic is recovered
through retained pstore and the known-good Gemian path before considering
another candidate. Neither a successful START nor a workqueue name alone
establishes effective CONSYS permissions, the region-23 overlap rule,
firmware image identity on the coprocessor, calibration, radio operation or
working mainline Wi-Fi. No packet DMA, association or network interface is
enabled by this profile.

The [first candidate](results/candidate-1.json) used Buildbox commit
`d4849f689d35c034468d4bb786306f403ead6ed0` and release
`7.1.3-gemini-a53-wifi-wmt-start`, but its [two physical boot attempts](results/attempt-1.json)
returned to Gemian before a mainline USB route. The second boot2 selection was
confirmed by the owner; there was no candidate console and retained pstore was
empty. Neither WMT nor START was triggered. Offline comparison found that the
assembler had used the full compiled DT, changing unrelated board nodes,
including disabling USB and keyboard paths. This is a concrete candidate
defect; the exact reset cause remains unobserved.

The [second candidate](results/candidate-2.json) retains the same compiled
kernel and private RAM root while modifying only the CONSYS node in the last
booting parent DT. A 180-node semantic comparison proves no other DT node
changed. Its full boot2 SHA-256 is
`d693e23ced511d6473a81d25e7c30eb792a7328b570755325b4492bb9bac1749`.
The private firmware remains excluded from the repository. `watch-boot.py`
runs `capture-private.py` once the direct USB route appears. That capture verifies
two identical pre-write 512 KiB reads, uses a temporary `/sys` read-write
remount for WMT preparation, restores read-only, validates the full post-window
and five kernel records, then makes one separately remounted START request.
If the boot survives, `passive-host.py` preserves the complete session and
uses the reviewed return path. A crash instead requires retained-pstore
inspection from known-good Gemian.

The [corrected candidate's boot](results/runtime-2.json) reached mainline. Two
full private region-19 reads matched; WMT preparation verified the 343 KiB clear,
and the one-time START sysfs write returned success. The complete kernel log
shows only prepower admission and a powered chip ID of `0x0279`: CONMCU reset
release stopped at the older EMI gate because it still required region 19 to
be empty. No firmware transfer or WLAN-ready event occurred. The A53 regression
passed and a changed-boot Gemian return was confirmed. A separate later EMI
copy gate also requires empty region 19, so patch 0052 admits the exact WMT
range and policy at both gates while preserving the zero-only requirement for
other profiles and checking that the policy is unchanged after the copy.
The [third candidate](results/candidate.json) contains patch 0052 from Buildbox
commit `c36ea4925d6acc8c16f6e6b639ffa22260a56864`. The same 180-node booting
DT and private RAM root are retained. Its full boot2 SHA-256 is
`42c3c298b88e31757a7d1c8e785afe3494a10937e70bb87d2e6bb31704f2073e`.
The installer pinned the second candidate as predecessor, wrote only the
live-GPT `boot2` partition after the identity and power gates passed, and
verified its full-partition readback before a clean shutdown. The owner
selected boot2 before the watcher armed; the already-present direct USB route
was authenticated to a fresh mainline boot before `capture-private.py` ran
directly. The fresh capture and session directories are numbered 3.

The [third runtime result](results/runtime-3.json) verified two equal private
prewrite reads and the same WMT clear. Region 19 retained its expected range
and policy while the corrected gate admitted CONMCU reset release. The Wi-Fi HIF
function became ready, two EMI sections totaling 396,688 bytes were copied
and sealed, two ordinary sections totaling 14,832 bytes transferred, and a single
START reached WCIR `0x00300279` with the firmware-ready record. There was no
null-workqueue-pool record or kernel panic. The complete log, A53 regression
and changed-boot Gemian return passed. This candidate held radio commands
and packet DMA, so it demonstrates neither a network interface nor
association or traffic. The executing firmware image, region overlap and
effective bus permissions remain distinct questions.
