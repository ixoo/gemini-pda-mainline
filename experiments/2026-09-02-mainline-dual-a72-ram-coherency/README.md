# Experiment: current-mainline dual-A72 RAM coherency

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-02-mainline-dual-a72-ram-coherency` |
| Status | `complete: RAM integrity pass; topology hypothesis rejected` |
| Subsystem | MT6797 Cortex-A72 topology, affinity, and RAM-backed integrity |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-09-02 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | post-online cluster validation |

## Question or hypothesis

After the exact repeatable patch-`0481` one-shot brings CPUs 8 and 9 online,
can each A72 execute under an exact single-CPU affinity and produce or consume
the same 1,914,704-byte payload through the RAM-backed initramfs with four
matching SHA-256 observations, distinct core IDs, one shared package ID, and
independently advancing scheduler accounting?

## Provenance and environment

- Exact installed full-`boot2` SHA-256:
  `370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e`.
- Kernel release: `7.1.3-gemini-cpu9-progress`.
- Kernel patch commit: `9c0e63dabf634bc645ad6eeb9c9f117c269da2d7`.
- Configuration SHA-256:
  `d450a5135a9689b40699273d09b74cadd873088317603d345ccc66cd25d027a8`.
- Exact parent: two fresh successful runtime cycles recorded by the
  [same-boot CPU9 successor](../2026-08-31-mainline-a72-cpu9-same-boot-successor/README.md).
- Payload: the exact static `/bin/busybox` already present in the candidate
  initramfs, size `1914704`, SHA-256
  `52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`.
- No kernel, DT, configuration, ramdisk, or container input changes. No kernel
  build is required; the already-validated candidate remains installed.

## Safety assessment

The parent pristine gate and one-trigger maximum remain mandatory. The child
probe is boot-ID bound and refuses all payload creation unless CPUs `0-9` are
online, the offline set is empty, `/run` belongs to the `rootfs` RAM backing,
and no `/dev/*` block source is mounted. It creates two fixed, private 1.9 MiB
files below `/run`, removes them on success and failure, and never reads a
partition or writes device storage. CPU_OFF, hotplug, retry, DVFS, thermal,
suspend, regulator, MMIO, and reboot actions are absent. Work is finite: two
copies, six checksums, and one one-second pinned sleep per A72.

## Associated code

- [`DESIGN.md`](DESIGN.md): fixed hypothesis, pass predicate, decision map, and
  safety boundary.
- [`scripts/collect-pretrigger.sh`](scripts/collect-pretrigger.sh): source-pins
  the proven pristine collector and requires a third fresh mainline boot ID.
- [`scripts/execute-attempt.sh`](scripts/execute-attempt.sh): source-pins the
  proven one-shot parent, then opens exactly one additional netcat session for
  the bounded probe.
- [`scripts/device-bounded-ram-coherency.sh`](scripts/device-bounded-ram-coherency.sh):
  fixed device-side RAM, topology, affinity, accounting, and cleanup contract.
- [`scripts/classify-attempt.py`](scripts/classify-attempt.py): strict transcript
  classifier.
- [`scripts/collect-recovery.sh`](scripts/collect-recovery.sh): source-pins the
  terminal retained-lane collector and requires a third fresh Gemian boot ID.
- [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): positive
  fixture, source-pin, forbidden-action, and mutation checks.
- [`results/runtime-tooling-20260902.txt`](results/runtime-tooling-20260902.txt):
  exact tooling identities, eleven rejected mutations, and the corrected
  RAM-only execution check for the candidate's BusyBox `taskset` applet.

Raw transcripts remain mode-`0700`, Git-ignored private evidence below
`artifacts/runtime-captures/` and `artifacts/device-pstore/`.

## Procedure

1. From the current Gemian boot, arm `collect-pretrigger.sh` with deployment
   boot ID `187f5e44-917e-465b-998e-dbc6e29009be` and the exact private output
   namespace.
2. Physically select `boot2`. Accept only a complete pristine, zero-execution
   frame on a new mainline boot ID.
3. Run `execute-attempt.sh`. It spends the admission trigger once. Only a full
   parent `cpu8-cpu9-online-accounting-advanced` result permits the second,
   one-session RAM probe.
4. Require the exact topology/affinity/checksum/accounting/cleanup pass
   predicate in [`DESIGN.md`](DESIGN.md). Never retry within the same boot.
5. After automatic return to a new Gemian boot, collect the terminal retained
   CPU8/CPU9 proof and verify `boot2` unchanged.
6. Publish only a minimal sanitized result and update durable support facts if
   the whole live and recovery chain passes.

## Observations

Before tooling publication, the owner announced one `boot2` start while Gemian
remained reachable with unchanged boot ID
`187f5e44-917e-465b-998e-dbc6e29009be`; the mainline console never appeared.
That event is not an experiment attempt and carries no kernel-failure
attribution.

The complete host/device tooling passes Bash syntax, ShellCheck 0.11.0, one
positive fixture, eleven rejecting transcript mutations, source-pin checks,
and a forbidden-action audit. The exact candidate BusyBox was transferred to
Gemian `tmpfs`, matched its pinned size and checksum, accepted the planned
mask syntax on CPU0, reported allowed list `0`, and was removed. Two setup
errors were rejected before that pass: an empty Darwin-cpio stdout stream and
a temporary executable whose basename was not `busybox`.

A fresh exact mainline boot ID `ce55410c...` passed the inherited pristine
gate. Its one trigger again brought CPUs `0-9` online and advanced CPU8 and
CPU9 independently by 101 and 102 scheduler ticks. The device-side child then
completed its only netcat session and reported `probe_result=pass`:

- exact affinity and executing-processor observations were `8` and `9`;
- CPU8 wrote the pinned 1,914,704-byte payload for CPU9 to read and CPU9 wrote
  the same payload for CPU8 to read;
- both source hashes and all four writer/reader hashes matched
  `52151e7f...`;
- CPU8 and CPU9 advanced another 258 and 256 scheduler ticks;
- both volatile files were absent after cleanup; and
- no partition read, storage write, CPU_OFF, retry, or reboot request occurred.

The strict host classifier correctly rejected the whole predeclared predicate:
both CPUs reported package `0`, distinct core IDs `8` and `9`, and individual
thread siblings, but each reported core siblings `0-9` rather than `8-9`.
Exact candidate-DTB inspection found no `/cpus/cpu-map`. Linux 7.1.3 source
inspection shows that this omission selects the generic fallback of NUMA-node
package ID plus logical-CPU core ID, after which every online CPU in package
zero becomes a core sibling. This exactly predicts the live result.

Automatic return reached fresh Gemian boot ID `de44c0b2...`. Recovery verified
unchanged full `boot2` SHA-256 `370ae4d0...`, CRC-valid terminal CPU8 and CPU9
records, and `cpu9-terminal-online-proof`. The sanitized result is
[`results/runtime-attempt-1-ram-integrity-pass-flat-topology-20260902.txt`](results/runtime-attempt-1-ram-integrity-pass-flat-topology-20260902.txt).

## Analysis

The observation splits cleanly. CPU8 and CPU9 demonstrably execute pinned work,
advance independent scheduler accounting, and exchange RAM-backed data without
a byte change in both directions. The rejected topology predicate is a DT
description defect, not evidence of CPU or RAM-coherency failure: the exact
candidate lacks the standard CPU map and Linux produces the observed flat
fallback deterministically.

Sequential userspace copies and checksums remain a bounded integrity result,
not a general concurrent cache-coherency stress test. Scheduler-sensitive or
concurrent load should wait until the three physical MT6797 clusters are
described and observed correctly.

## Conclusion

`split pass`: the one permitted runtime attempt passes the parent admission,
CPU8/CPU9 affinity, independent execution/accounting, bidirectional volatile-RAM
integrity, cleanup, and recovery gates. It rejects the predeclared topology
hypothesis because the current DT has no `cpu-map` and Linux reports a flat
package.

## Follow-up

Do not repeat this artifact unchanged. Add the standard MT6797 three-cluster
`cpu-map`, validate its DT/schema and Buildbox result, then use one exact runtime
observation to require A53 clusters `0-3` and `4-7`, A72 cluster `8-9`, and the
already-proven RAM/affinity/accounting behavior. Only that result may admit a
separately designed bounded concurrent workload.
