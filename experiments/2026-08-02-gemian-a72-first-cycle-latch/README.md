# Experiment: Gemian A72 first-complete-cycle latch

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-gemian-a72-first-cycle-latch` |
| Status | `running`: exact boot2 write/readback and shutdown pass; manual boot2 selection and passive ABI-v2 runtime retrieval remain |
| Subsystem | MT6797 CPU8 hotplug observer and owner-local diagnostic sampling |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-08-02 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the existing read-only Gemian A72 observer preserve the first attributable
natural CPU8 online/offline pair even when userspace retrieval is delayed, by
automatically latching a bounded record and suppressing all later
observer-only sampling without changing any vendor power operation?

This experiment does not test CPU9, suspend/resume, failure rollback, or a
mainline A72 request. Those remain separate Gate 4 boundaries.

## Provenance and environment

- Parent observer source experiment:
  `2026-07-23-gemian-a72-owner-observer`, five-patch revision ending at source
  patch commit `718f297ae97ab3738d624129b814e921a8371227`.
- Runtime reason for the revision: the exact first live ring was full at 256
  records with 3474 earlier records overwritten. It retained internally valid
  natural transitions but could not establish clean initial attribution.
- Exact deployed padded parent image SHA-256:
  `33ace2c30a8877be2a4b917135aa994ad718201f98ec36d8506a3b1f1d03a7aa`.
- Selected vendor source remains hook-equivalent public commit
  `59e00a9144d782e148332009a835b99c43382467`; it is not claimed to be the
  unrecovered exact active source.
- Any kernel build must use the pinned 2017 toolchain through Buildbox from an
  exact clean pushed project commit. A native VM kernel build is prohibited
  unless the owner explicitly requests that specific build.
- Boot path, candidate identity and target partition are intentionally unset
  until source, compiler, timing, package and assembly gates pass.

## Safety assessment

The proposed revision is recorder policy, not a CPU policy or power driver. It
adds no userspace write operation, ring-clear operation, hotplug request,
register selector, SMC selector, retry, delay, warning or panic. Before the
first CPU8 HPS-up begin it records nothing and performs no observer-only broad
snapshot. Once that begin is seen, the existing bounded observer is active
until the matching successful HPS-up end and then the next matching CPU8
HPS-down end.

The record freezes on a complete pair or on the first decision-relevant
failure: CPU8 up failure, CPU8 down failure, CPU9 overlap, protocol mismatch or
capacity exhaustion. Frozen means both that the ring is immutable and that
future pure diagnostic snapshots return before I2C, secure-call, mapping,
semaphore or register-read work. Real vendor mutations must still execute.
Where an instrumented helper wraps a real SPM, buck or DCM operation, a false
capture gate must select the exact original vendor operation rather than skip
it.

No device filesystem backup is required or planned. If a later validated image
is installed, the standing guarded-`boot2` procedure resolves the logical
partition live, verifies it is inactive and unmounted, records the predecessor
checksum, performs exact-size write/readback verification, and shuts the device
down so the owner can manually select `boot2`.

## Associated code

- [`DESIGN.md`](DESIGN.md): state, concurrency, owner-effect and ABI contract.
- [`scripts/latch_model.py`](scripts/latch_model.py): executable reference
  model; it performs no hardware or network access.
- [`scripts/test_latch_model.py`](scripts/test_latch_model.py): positive and
  fail-closed model tests.
- [`scripts/assemble.py`](scripts/assemble.py): source-pinned Android-v0
  serializer retaining the exact Gemian container contract.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): exact-input,
  two-assembly, two-padding and private-manifest orchestration.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): source-pinned guarded
  logical-boot2 installer with exact predecessor/candidate gates, no fresh
  backup, full readback and mandatory clean shutdown.
- [`scripts/remote-passive-capture.sh`](scripts/remote-passive-capture.sh):
  exact kernel/ABI-gated two-read observer retrieval before optional power
  reporting, with no load or writable operation.
- [`scripts/collect-passive.sh`](scripts/collect-passive.sh): bounded,
  exact-dependency authenticated collector with ignored mode-0600 output.
- [`scripts/validate-passive.py`](scripts/validate-passive.py): strict ABI-v2,
  stability, state, transaction and complete owner-transition validator.
- [`scripts/test-passive.py`](scripts/test-passive.py): real retained-pair
  positive fixture and twelve fail-closed/no-stimulus checks.
- [`results/buildbox-compiler-lock-timing-review-20260802.txt`](results/buildbox-compiler-lock-timing-review-20260802.txt):
  exact final Buildbox and host-bundle validation, selected stack frames,
  lock/timing review, and the decision authorizing only image preparation.
- [`results/offline-container-validation-20260802.txt`](results/offline-container-validation-20260802.txt):
  exact candidate identity and independent Android-v0 structural review.
- [`results/predeployment-expectations-20260802.txt`](results/predeployment-expectations-20260802.txt):
  owner-visible boot expectations, passive runtime hypothesis, stable evidence
  gate, outcome matrix and guarded deployment boundary.
- [`results/installer-validation-20260802.txt`](results/installer-validation-20260802.txt):
  exact derivation, source/token gates, retained live-GPT protections, syntax,
  and managed-VM ShellCheck.
- [`results/passive-collector-validation-20260802.txt`](results/passive-collector-validation-20260802.txt):
  exact dependency hashes, evidence-first ordering, semantic classification,
  positive real-pair fixture, safety checks and managed-VM ShellCheck.
- [`results/deployment-20260802.txt`](results/deployment-20260802.txt): exact
  live-GPT target, predecessor, candidate/readback identity, power state,
  cleanup, confirmed shutdown and owner handoff.

Local model validation:

```sh
python3 experiments/2026-08-02-gemian-a72-first-cycle-latch/scripts/test_latch_model.py
```

## Procedure

1. Freeze the state-machine and owner-effect contracts in `DESIGN.md` and the
   executable model.
2. Add logical recorder and owner-effect patches to the parent observer series.
   Generate them from the selected vendor source on Buildbox; do not create or
   copy a vendor source tree onto the host.
3. Extend static validation so mutations of every latch, ABI, no-overwrite,
   pure-snapshot guard and real-operation fallback invariant are rejected.
4. Commit and push the exact clean project revision, then run only the
   dedicated Buildbox observer build with its baseline/compiler/stack checks.
5. Review the resulting code paths and compiled stack/timing evidence. A
   successful compile is not permission to boot.
6. Only after a separately recorded package and assembly review, install the
   exact candidate to guarded logical `boot2`, verify full readback, and shut
   down. Before selection, tell the owner that the UI will look like ordinary
   Gemian and state the identity and retrieval expectations.
7. On the candidate, retrieve the root-only observer file without generating
   synthetic load. Validate the frozen ABI and exact transaction pair, then
   return to ordinary Gemian.

## Observations

- The parent candidate booted and was serviceable, but delayed retrieval found
  `count=256 overwritten=3474`.
- The retained tail contains five complete CPU8-up and six complete CPU8-down
  transactions, proving that natural Gemian policy supplies cycles without a
  synthetic pulse.
- Patches 6 and 7 are real Buildbox-generated `git format-patch` files. The
  complete source passes the parent validator, 17 mutation tripwires and the
  executable model. Exact commit `a5b22fa59a4e45169a5c31f976b3f19df4e00bfa`
  also passes observer/baseline compilation, identical diagnostic attribution,
  2484-report stack validation, lock review and the one-cycle timing bound.
  Exact candidate padded SHA-256 `6dcbda0cb264...` now passes two independent
  assembly and padding constructions plus independent Android-v0 parsing. It
  retains the exact Gemian ramdisk and visible userspace, so screen appearance
  will not distinguish it from ordinary Gemian. The exact derived installer
  also passes its static, manifest, syntax and managed-VM ShellCheck gates and
  retains full readback plus shutdown. Deployment and runtime observations
  remain open. The passive collector now also passes its exact identity,
  two-read terminal-stability, complete-pair semantic and twelve fail-closed
  gates; critically, it copies the observer before optional USB reporting.
- The guarded installer resolved logical boot2 as `/dev/mmcblk0p30` while
  ordinary Gemian remained rooted on `/dev/mmcblk0p29`. The predecessor matched
  the exact parent observer, power was present and the battery was 100%/Good.
  The synchronized write, post-flush checksum and independent full readback all
  matched padded SHA-256 `6dcbda0cb264...`. No backup was created, temporary
  copies were removed, and clean shutdown was confirmed.

## Analysis

An automatic latch is the smallest independent observation path that changes
the previous outcome: it removes userspace retrieval latency from retention.
Merely enlarging the ring or reading the identical image sooner would not
protect attribution and would spend another boot on a non-durable timing race.

Suppressing writes to a frozen ring alone is unsafe and incomplete. The parent
observer's fixed snapshots can themselves perform I2C transactions, secure
reads and clock arbitration. Therefore the latch must also disable those pure
diagnostic actions after freeze, while leaving all real power mutations intact.

## Conclusion

`inconclusive`: source, compiler and offline container gates pass, but the
candidate has not been installed or booted and provides no hardware evidence.

## Follow-up

The owner manually selects boot2 from the current powered-off state. Expect
ordinary Gemian visuals and possibly delayed console/USB service. Then run the
passive collector once and return to known-good Gemian for review. Do not
repeat the image, run the pulse, request CPU8/CPU9, or perform a native VM
kernel build.
