# Experiment: current-mainline dual-A72 RAM coherency

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-02-mainline-dual-a72-ram-coherency` |
| Status | `running` |
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

No bounded-coherency runtime observation has been made yet.

## Analysis

Tooling is ready; runtime evidence is pending. A pass will establish only short bidirectional
RAM-backed data integrity plus topology, affinity, and accounting on the exact
current-mainline candidate. Sequential userspace copies and checksums are not a
general concurrent cache-coherency stress test.

## Conclusion

`inconclusive`: tooling validation passed; no selected runtime attempt exists.

## Follow-up

Run exactly one admitted cycle. A full pass permits a separately designed,
bounded concurrent workload. A mismatch or incomplete frame stops unchanged
repetition and selects a narrower diagnostic from the failed field.
