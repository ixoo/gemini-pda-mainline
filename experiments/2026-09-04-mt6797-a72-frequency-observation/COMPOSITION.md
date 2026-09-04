# Stage-18 thermal/frequency composition

## Hypothesis

The hardware-free-proved three-attempt frequency observer can be added to the
exact successful stage-18 lifecycle and thermal configuration without changing
CPU admission, CPU9 down/restore, voltage, frequency, policy, or workload. One
later fresh boot can then attribute the B-cluster clock before the workers are
created, while both affinity-pinned writers are alive at their start barrier,
and after the already-proven finite dual-A72 volatile-RAM exchange.

## Configuration boundary

The `gemini-a72-frequency-thermal-candidate` profile retains the complete
`gemini-a72-hotplug-physical-candidate` fragment sequence in the same order,
then adds:

1. `gemini-emmc-development.fragment`, already used by the successful thermal
   runtime;
2. `gemini-mt6797-thermal-stage-ledger.fragment`, whose live-model-repaired
   form produced the successful thermal frame; and
3. `gemini-a72-frequency-thermal-candidate.fragment`, which enables only the
   read-only observer and gives the composition a unique release.

KUnit, cpufreq, OPP policy, CPU idle, and suspend remain disabled. The physical
lifecycle remains one-shot and public CPU hotplug remains closed.

After the first live pretrigger, canonical patch `0529` binds this exact
profile's `18ded825...` configuration identity without changing the profile
fragments. Canonical patch `0530` makes the already-bound admission controller
own the observer endpoint: its existing DT phandles resolve the platform-state,
protected-clock, and BigiDVFS devices, initialize the snapshot source, and only
then publish one top-level read-only attribute. No snapshot-adapter DT node is
added, and the later one-shot trigger reuses the prepared devices.

The exact clean successor package is built from published repository commit
`5d892a1c83b8ae5099bbfd5d379f726d04c4ebde`, source identity `be41c068...`,
patchset `0f2a0357...`, and configuration input identity `18ded825...`. Its
production image is `02eea298...`; its static registration oracle finds the
observer render path once, the admission probe once, and the attribute in the
two expected compiled declarations while excluding all KUnit suites. The
focused observer and production-binding packages pass 5/5 and 14/14 cases in
isolated no-network arm64 QEMU.

## Device-tree boundary

The structural base is exact topology/serviceability DT
`4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923`,
which owns the successful 4+4+2 map and omits package-specific provenance. The
thermal transform is the already-reviewed overlay source
`2f0a9a424d75f3042cabcb54fce0518133deb89a065d5671b87fce287b8cc91a`.
It may change only the root model, thermal reset/status/phandle, and the one
policy-free thermal zone. The final transform adds only the exact new
Buildbox package's A41 provenance leaf.

An independent validator must prove both deltas, unique phandles, the exact
4+4+2 map, enabled USB/keyboard/eMMC/PWRAP serviceability, enabled calibrated
thermal controller, one policy-free zone, all physical lifecycle nodes, and
the package-exact provenance record.

That validation produces exact successor DT `a4bf5774...` with package record
identity `018de915...`. Deterministic Android-v0/LK composition produces raw
container `24cb227b...` (7,133,184 bytes) and padded candidate `54a02dd0...`
(16,777,216 bytes). The latter is the only selected `boot2` identity; retired
candidate `03cbaa72...` must not be repeated.

## Runtime boundary

No device boot is selected by profile compilation. After package, DT,
initramfs, Android-v0 container, runtime-tool, and mutation gates pass, one
candidate may be installed to live-GPT-resolved inactive `boot2` under the
standing full-readback and shutdown policy.

The one fresh boot must take exactly three successful frequency observations:
before the finite dual-A72 RAM exchange, while both affinity-pinned writers are
alive on both sides of the middle sample and waiting at their start barrier,
and after both finish the four released rounds. The same boot-ID-bound frame
must also prove:

- stage-18 completion and exact CPUs 0--9 online;
- package/cluster/core/thread topology matching 4+4+2;
- CPU8 and CPU9 exact affinity and independent accounting movement;
- all four bounded volatile-RAM hashes and cleanup;
- one bound policy-free thermal zone with plausible temperatures; and
- the raw and decoded clock records for all three observer attempts.

Any observer transport/decoder failure selects observer repair without more
load. A lifecycle failure selects the existing lifecycle evidence path. A
thermal anomaly stops the run. No retry, CPU_OFF beyond the inherited one-shot
CPU9 transaction, cpufreq/OPP change, longer load, idle, suspend, partition
access, or same-artifact repeat is permitted.

The new pretrigger is pinned to candidate `54a02dd0...` and record identity
`018de915...`. Visible console state is explicitly non-authoritative: admission
requires the direct-USB netcat frame to prove the exact release, changed boot
ID, one read-only observer, ready late profile, thermal serviceability, CPUs
0--7 online, CPUs 8--9 offline, and zero observer or lifecycle attempts.
