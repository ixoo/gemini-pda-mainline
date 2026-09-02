# Experiment: MT6797 CPU topology map

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-02-mainline-mt6797-cpu-map` |
| Status | `running: offline candidate passed; deployment pending` |
| Subsystem | MT6797 arm64 CPU topology and scheduler description |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-09-02 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | post-online topology repair |

## Question or hypothesis

Does a standard three-cluster `/cpus/cpu-map` make Linux publish CPU0--3,
CPU4--7, and CPU8--9 as the three MT6797 clusters while preserving the exact
patch-`0481` dual-A72 admission, affinity, accounting, RAM-integrity, recovery,
and serviceability results?

## Provenance and environment

- Repository parent: `cc9a4e58`.
- Kernel baseline: Linux 7.1.3 plus canonical patches through `0481`.
- Candidate profile: `a72-cpu9-progress-candidate`.
- Configuration remains unchanged from SHA-256
  `d450a5135a9689b40699273d09b74cadd873088317603d345ccc66cd25d027a8`.
- Patch: [`0482-arm64-dts-mediatek-mt6797-describe-CPU-topology.patch`](../../patches/v7.1.3/0482-arm64-dts-mediatek-mt6797-describe-CPU-topology.patch).
- Parent runtime: the [dual-A72 RAM-integrity result](../2026-09-02-mainline-dual-a72-ram-coherency/results/runtime-attempt-1-ram-integrity-pass-flat-topology-20260902.txt).

## Safety assessment

Patch `0482` changes only declarative topology under `/cpus/cpu-map`. It does
not alter CPU enable methods, firmware calls, admission, power, clocks,
regulators, CPU_OFF, hotplug, retry, watchdog, storage, or retained RAM. All
source, schema, DTB, and package checks run on Buildbox before any device action.
A later candidate may reach inactive logical `boot2` only through the existing
live-GPT, full-readback, and clean-shutdown gates. One admitted runtime cycle is
the maximum; no unchanged retry is allowed.

## Associated code

- [`DESIGN.md`](DESIGN.md): corrected kernel ABI semantics, exact pass
  predicate, and decision map.
- [`scripts/validate-cpu-map.py`](scripts/validate-cpu-map.py): validates the
  compiled DTB using `fdtget`, including all ten unique CPU references, MPIDR
  `reg` values, CPU types, and exact cluster/core membership.
- [`scripts/build-topology-serviceability-dtb.py`](scripts/build-topology-serviceability-dtb.py):
  imports the package-proven map into the exact serviceability base using ten
  collision-checked phandles and a deterministic transform.
- [`scripts/build-composed-dtb.py`](scripts/build-composed-dtb.py) and
  [`scripts/validate-composed-dtb.py`](scripts/validate-composed-dtb.py):
  compose and independently prove the topology serviceability tree plus the
  exact package-owned provenance leaf.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh) and
  [`scripts/validate-candidate.py`](scripts/validate-candidate.py): construct
  the deterministic Android-v0 image twice and independently validate its LK
  layout, package, topology, serviceability, and mutation rejection gates.
- [`fixtures/mt6797-cpu-map-minimal.dts`](fixtures/mt6797-cpu-map-minimal.dts):
  redistributable positive validator fixture with the exact 4+4+2 topology.
- [`patches/series`](../../patches/series): canonical ordering through `0482`.

## Procedure

1. Replay canonical patches through `0482` on the pinned Linux source and run
   the all-profile series invariant.
2. Compile `a72-cpu9-progress-candidate` only on Buildbox. Validate the package
   and exact compiled Gemini DTB with `validate-cpu-map.py` and the kernel DT
   checks.
3. Construct and independently validate one exact Android-v0 candidate that
   differs from the parent only by the DT topology map.
4. Install it to live-resolved inactive `boot2`, require full-partition
   readback, and shut down cleanly.
5. On one fresh boot, require exact identity, pristine one-shot admission,
   cluster lists `0-3`, `4-7`, and `8-9`, package/core/thread topology, exact
   CPU8/CPU9 affinity, bidirectional volatile-RAM hashes, independent
   accounting, cleanup, changed-ID recovery, terminal retained proofs, and
   unchanged `boot2`.

## Observations

Exact Linux 7.1.3 source inspection established that `core_siblings_list`
represents package membership, whereas `cluster_cpus_list` represents the leaf
cluster. The prior test's expectation of `core_siblings_list=8-9` was therefore
an invalid oracle. The observed `core_siblings_list=0-9` is correct for one SoC
package; the independently confirmed defect is that the exact candidate DTB has
no `cpu-map`, so arm64 has no three-cluster description.

Patch `0482` adds only three leaf clusters matching the existing CPU-node MPIDR
affinity levels: `0x000`--`0x003`, `0x100`--`0x103`, and `0x200`--`0x201`.
It applies cleanly to the prepared Linux 7.1.3 series source, and the
165-profile canonical-series invariant passes. The validator accepts the exact
4+4+2 positive fixture and rejects an exact predecessor package DTB because its
map is absent. Strict checkpatch with the sign-off check disabled reports zero
errors, warnings, or checks. The patch retains the repository's clearly
synthetic experiment identity without a DCO sign-off; it is not
submission-ready and must be reauthored and truthfully certified before any
upstream submission. See
[`results/source-tooling-20260902.txt`](results/source-tooling-20260902.txt).

Buildbox built exact commit `2e661e90` using the
`a72-cpu9-progress-candidate` profile. The Image, compressed Image,
configuration, and System.map are byte-identical to the runtime-proven parent;
only the compiled Gemini DTB changes. The package DTB passes the exact 4+4+2
validator. DT schema tooling was unavailable on Buildbox, so no schema pass is
claimed; normal DTC and package validation passed.

The exact serviceability composition preserves every prior node, imports the
map with collision-checked CPU phandles `0x37`--`0x40`, and adds the exact
Buildbox provenance leaf. The independently reconstructed 16 MiB candidate is
SHA-256 `68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393`.
All 32 LK gates and six negative container mutations pass. See
[`results/offline-production-candidate-20260902.txt`](results/offline-production-candidate-20260902.txt).

## Analysis

The topology repair is narrower than a CPU-power or scheduling-policy change.
With one package and three clusters, the corrected runtime expectation is
`core_siblings_list=0-9` for all CPUs plus `cluster_cpus_list=0-3`, `4-7`, or
`8-9` according to affinity level. A compile-only result will not establish
that the live scheduler consumed the map.

## Conclusion

`offline pass`: the source-level defect, corrected ABI oracle, canonical patch,
Buildbox package, topology/serviceability composition, and exact boot2
container all pass their available offline gates. Device runtime validation is
pending.

## Follow-up

Install the exact candidate to live-resolved inactive `boot2`, require its full
readback checksum, and shut down. On the one admitted boot, verify exact
identity and serviceability before the inherited one-shot trigger. A runtime
pass permits one separately designed bounded concurrent multi-cacheline
workload. A live cluster-list mismatch stops the line without an unchanged
retry.
