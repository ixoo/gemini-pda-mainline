# Experiment: concurrent dual-A72 multi-cacheline load

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-02-mainline-dual-a72-concurrent-multiline` |
| Status | `runtime tooling passed; fresh attempt 2 pending` |
| Subsystem | MT6797 CPU8/CPU9 concurrent execution and volatile-RAM coherency |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-09-02 |
| Investigator(s) | Gemini mainline project |
| Parent | `2026-09-02-mainline-mt6797-cpu-map` |

## Question or hypothesis

Can the two online Cortex-A72 CPUs sustain simultaneous finite work on disjoint
multi-cacheline rootfs files, then simultaneously validate one another's
files, while retaining the accepted 4+4+2 topology, exact affinity,
independent accounting, serviceability, cleanup, and no-storage/no-CPU_OFF
contracts?

This is the Roadmap-selected first concurrent-load child of the accepted CPU
topology experiment. It does not attempt hotplug, CPU_OFF, cpufreq, thermal,
idle, or suspend validation.

## Provenance and inherited state

- Repository parent: `9dcb165a`.
- Kernel: `7.1.3-gemini-cpu9-progress` from the accepted patch-`0482`
  candidate; no kernel, configuration, DT, ramdisk, or boot-container input is
  changed.
- Installed padded boot2 SHA-256:
  `68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393`.
- Parent runtime classification:
  `mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass`.
- The first fresh namespace armed after the reported boot2 cycle had already
  returned to the same Gemian boot ID. No mainline session, trigger, workload,
  CPU_OFF, retry, reboot request, or device-storage action occurred. This is an
  inconclusive timing miss, not a kernel result. See
  [`results/runtime-attempt-1-no-live-session-20260902.txt`](results/runtime-attempt-1-no-live-session-20260902.txt).

Because this child changes only host/device runtime tooling, no Buildbox kernel
build is required. The exact already-validated boot2 candidate is reused for a
new decision-bearing measurement rather than an identical observation.

## Bounded workload

One netcat session performs the inherited pristine admission, trigger, all-CPU
topology, and bidirectional RAM-integrity checks before entering this child.
CPU8 and CPU9 then start together and each writes the 1,914,704-byte BusyBox
payload to a distinct rootfs file four times, hashing every completed write.
They next start together and each hashes the peer CPU's file four times.

The strict oracle requires eight matching writer hashes, eight matching peer
reader hashes, exact CPU8/CPU9 affinity and observed processor IDs, four
completed rounds per worker, independently advanced accounting, absent
temporary files, RAM-backed `/` and `/run`, no mounted block device, and no
partition, CPU_OFF, retry, or reboot operation. Start publication loops are
finite and bounded at 1,000,000 iterations. The primary concurrent write
volume is 15,317,632 bytes and the peer-read volume is 15,317,632 bytes.

## Associated code

- [`DESIGN.md`](DESIGN.md): scope, predicates, and decision map.
- [`scripts/device-concurrent-multiline.sh`](scripts/device-concurrent-multiline.sh):
  finite target-side child.
- [`scripts/remote-integrated-concurrent-multiline.sh`](scripts/remote-integrated-concurrent-multiline.sh):
  materializes the inherited trigger/topology/RAM transaction followed by the
  concurrent child.
- [`scripts/classify-attempt.py`](scripts/classify-attempt.py): requires the
  parent pass and classifies the concurrent boundary.
- [`scripts/collect-pretrigger.sh`](scripts/collect-pretrigger.sh),
  [`scripts/execute-attempt.sh`](scripts/execute-attempt.sh), and
  [`scripts/collect-recovery.sh`](scripts/collect-recovery.sh): allocate fresh
  attempt-2 evidence, run one exact session, and recover changed-ID terminal
  proofs plus unchanged boot2.
- [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): validates
  source pins, materialization order, the positive oracle, and representative
  unsafe or corrupt mutations.

## Offline result

`pass`: shell syntax and ShellCheck pass. The materialized script preserves
strict trigger, topology/RAM, then concurrent ordering. One positive fixture
passes and 17 representative mutations fail. Forbidden-action checks confirm
that the child has no remount, partition, CPU-online-sysfs, CPU_OFF, poweroff,
or reboot path. The full transaction retains only the inherited single
read-write/read-only sysfs remount around the admitted trigger. See
[`results/runtime-tooling-20260902.txt`](results/runtime-tooling-20260902.txt).

## Runtime decision map

- Full pass plus changed-ID recovery and unchanged boot2: admit a separately
  designed hotplug/CPU_OFF gate; do not infer cpufreq, thermal, or suspend.
- Admission or inherited topology/RAM failure: treat it as a regression before
  concurrency and isolate that boundary.
- Writer/reader, checksum, accounting, cleanup, or affinity failure: reject
  this workload result and preserve the first exact failure; do not repeat it
  unchanged.
- No attributable mainline session: preserve as an inconclusive timing miss
  and use a fresh namespace; do not classify the screen or fallback alone.

## Conclusion

Runtime pending. The exact attempt-2 tools are ready for one fresh boot of the
unchanged accepted candidate.
