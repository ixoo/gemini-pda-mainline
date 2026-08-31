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

Status: implementation and Buildbox validation pending.
