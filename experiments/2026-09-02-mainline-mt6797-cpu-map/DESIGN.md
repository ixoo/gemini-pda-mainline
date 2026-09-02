# MT6797 CPU-map design

## Corrected topology semantics

Linux exposes `core_siblings_list` as all CPUs in the same physical package and
`cluster_cpus_list` as CPUs in the same leaf cluster. MT6797 is one package with
three non-SMT clusters, so the expected live topology is:

| CPUs | Package | Cluster members | Core IDs | Thread members |
| --- | --- | --- | --- | --- |
| 0--3 | 0 | `0-3` | 0--3 | self |
| 4--7 | 0 | `4-7` | 0--3 | self |
| 8--9 | 0 | `8-9` | 0--1 | self |

Every CPU's correct `core_siblings_list` remains `0-9`. The prior
`core_siblings_list=8-9` predicate confused package and cluster ABIs and is not
carried forward.

## Patch boundary

The SoC DTS gains one standard `cpu-map`. Cluster 0 references CPU0--3,
cluster 1 references CPU4--7, and cluster 2 references CPU8--9. Each CPU appears
exactly once. The existing CPU compatible, `reg`, and enable-method properties
are unchanged. No capacity, OPP, idle, cache, power-domain, clock, regulator,
firmware, admission, or hotplug policy is added.

## Offline pass predicate

1. Patch `0482` applies after the canonical `0481` sequence and the 165-profile
   series invariant passes.
2. The Buildbox production profile compiles and packages successfully.
3. The compiled Gemini DTB contains exactly clusters 0--2, exact core counts
   4/4/2, ten unique CPU phandles, existing MPIDR `reg` values, and A53/A53/A72
   compatible membership.
4. DT schema/check output has no new error attributable to the map.
5. Kernel Image, configuration, ramdisk, and all non-DT candidate inputs remain
   attributable; the composed DT and container identities are recorded and
   independently reproduced.

## Runtime pass predicate

One fresh candidate boot must pass the existing pristine single-trigger parent,
then report all CPUs online, package siblings `0-9`, cluster members `0-3`,
`4-7`, and `8-9`, core IDs 0--3/0--3/0--1, self-only thread siblings, exact
CPU8/CPU9 affinity, the two matching volatile-RAM directions, positive
independent accounting, cleanup, zero storage/CPU_OFF/retry, changed-ID
recovery, terminal retained proofs, and unchanged `boot2`.

## Decision map

- Full offline and runtime pass: admit one finite concurrent multi-cacheline
  workload as a separate experiment.
- DT compile/schema failure: repair the description offline; no device boot.
- Live topology mismatch with exact DT present: inspect parser and scheduler
  topology consumption; no unchanged retry.
- Admission, affinity, RAM, accounting, recovery, or serviceability regression:
  reject the candidate and isolate the first changed boundary.

CPU_OFF/hotplug, cpufreq/OPP, idle, thermal, suspend, and default-profile
integration remain independent later gates.
