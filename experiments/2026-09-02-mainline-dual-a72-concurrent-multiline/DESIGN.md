# Concurrent dual-A72 multiline design

## Scope

The accepted CPU-map result establishes one package, physical 4+4+2 cluster
membership, both A72 CPUs online, exact single-CPU affinity, bidirectional
volatile-RAM integrity, and independent accounting. This child changes one
dimension: CPU8 and CPU9 execute bounded data work at the same time.

It does not alter or exercise CPU_OFF, hotplug, clocks, regulators, OPPs,
cpufreq, idle, thermal control, suspend, firmware policy, device storage, the
kernel, DT, or boot container.

## Single-session sequence

1. Admit one fresh exact boot with the inherited candidate, serviceability,
   mount, and zero-execution gates.
2. Spend the inherited one-shot admission trigger.
3. Reprove all ten topology records and the accepted two-direction RAM
   exchange before the network session can close.
4. Start CPU8 and CPU9 writers using a bounded file-publication barrier. Each
   writes and validates a disjoint 1,914,704-byte rootfs file for four rounds.
5. Start CPU8 and CPU9 peer readers using a second bounded barrier. Each hashes
   the other CPU's complete file for four rounds.
6. Capture per-worker affinity, processor, progress, status, hashes, and CPU
   accounting; remove every temporary file.
7. After return to fresh-ID Gemian, require unchanged full-partition boot2 and
   both terminal retained A72 proofs.

The barriers synchronize start opportunity without shared writable payload
cache lines. The payloads span many cache lines; exact peer hashes test visible
completed data across the two A72 execution contexts. This is a finite
coherency/progress observation, not a general stress or cache-correctness proof.

## Pass predicate

The parent classification must remain
`mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass`. The child must report
the same boot ID and kernel, CPUs `0-9` online, RAM-backed rootfs with no block
mounts, exact CPU8/CPU9 affinity and processor IDs, four rounds from every
writer and reader, all sixteen hashes equal to the pinned BusyBox payload,
positive non-retrograde accounting on both CPUs, zero child failures, complete
cleanup, and explicit absence of partition, CPU_OFF, retry, and reboot action.

Changed-ID recovery must independently preserve both terminal online proofs and
the exact installed boot2 checksum. A screen state or automatic Gemian return
without those identities cannot decide the predicate.

## Boundaries

- One fresh attempt and one trigger maximum per admitted boot.
- No retry inside the device script.
- Barrier spins stop after 1,000,000 tests.
- Only two files under RAM-backed `/run`; no device node is opened.
- No CPU-online sysfs write, CPU_OFF request, poweroff, or reboot.
- No Buildbox build: all kernel and container inputs are unchanged.
