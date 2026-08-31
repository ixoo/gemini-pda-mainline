# Experiment: repair P30E production READY identity

The first P30E boot was serviceable, but its one trigger terminated with
`-EAGAIN` before admission-core consumption or any CPU request. Same-boot
`dmesg` identifies the cause: the production arm64 profile rejected the
package-exact runtime provenance at proof mask `0x40000` because patch `0436`
still pins the pre-P30E config-input identity `5968c24f...`. The package and
composed DT correctly carry `1e7f3047...`.

Patch `0456` updates only that production identity. This experiment will build
the exact successor on Buildbox, compose and independently validate it, then
spend at most one CPU8 trigger after a corrected pretrigger gate proves READY.
CPU9, CPU_OFF, retry, automatic reboot, and device-filesystem backup remain out
of scope.

The predecessor's exact terminal result is owned by the
[P30E entry diagnostic](../2026-08-31-mainline-a72-p30e-entry-diagnostic/results/runtime-attempt-1-stale-ready-identity-20260831.txt).

Buildbox produced the exact successor from repository commit `8fa0757b...`.
Two independent assemblies are byte-identical and two independent validations
pass all 32 LK-container gates plus all six negative mutations. Exact padded
candidate `459bcf66...` is therefore selected for one deployment; no device
write or CPU request occurred during this offline qualification.

The guarded deployment resolved logical `boot2` as inactive
`/dev/mmcblk0p30`, confirmed exact predecessor `a4ad4915...`, wrote and fully
read back padded candidate `459bcf66...`, and then shut the device down. The
successor pretrigger now counts every `arm64-late-cpu-profile: ... blocked:`
wording, fixing the stale collector that missed proof mask `0x40000`.
The boot-bound executor is also pinned to this candidate and corrected
validator. It durably revalidates the accepted pretrigger frame, sends exactly
one CPU8 token, forbids CPU9/CPU_OFF/retry/reboot, and classifies the existing
ARMED, CLAIMED, PUBLISHED, online, transport-loss, and fail-closed outcomes.

The first physical boot proved READY and consumed the one allowed CPU8 trigger.
P27, provider acquisition, isolation, stable masked SRAM validation, and P28
all completed; one CPU8 request then returned `-EIO`. P30E preparation and
arming succeeded, and controller readback found target state `CLAIMED`, target
sequence `0`, and controller sequence `1`. CPU8 therefore executed the early
`secondary_entry` claim but did not reach the later publication in
`secondary_start_kernel()`. CPU0--7 remained online, CPU8--9 remained offline,
and CPU9, CPU_OFF, retry, and native-reboot counts remained zero. The recovery
watchdog returned the device to changed-ID Gemian; its sole 72-byte ramoops
record had no attributable candidate trace.

The first local classification rejected this otherwise complete transcript
because the decision map incorrectly expected CLAIMED/PUBLISHED target
sequences `1`/`2`. The wire implementation and focused fake both establish
`0`/`1`; correcting that contract reclassifies the preserved transcript as
`p30e-target-claimed` without another device action. See the
[runtime result](results/runtime-attempt-1-p30e-claimed-20260831.txt).

Status: experiment complete; candidate retired. The next experiment must add
bounded P30E checkpoints between the successful claim and
`secondary_start_kernel()` publication. An identical retry is forbidden and
CPU9 remains vetoed.
