# Experiment: manual checkpoint raw-write qualification

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-22-mainline-manual-checkpoint-raw-write-qualification` |
| Status | runtime complete: write/readback and warm retention passed; sparse record 173 was not enumerated |
| Subsystem | retained ramoops record writer / cross-version recovery |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-22 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, retained checkpoint qualification |

## Question or hypothesis

Can the known serviceable manual late initcall commit one exact record from the
runtime-proven all-ones entry state, read it back locally, and have known-good
Gemian recover it?

This experiment deliberately does not instantiate the protected observer or a
clock backend. It reuses the already proven late initcall and parallel
`ioremap_wc()` view. The exact hypothesis is:

1. records 171--174 enter mainline with all three header words equal to
   `0xffffffff`;
2. the first manual checkpoint accepts that prefix;
3. it writes only record 173 in payload, start, size, signature order;
4. the full header and payload read back exactly; and
5. after an identity-gated native return, Gemian recovers the exact
   `manual-first` record.

## Provenance and environment

- Serviceability and mapping foundation: exact runtime mapping-control evidence
  at commit `c9bcfdbb86b674b24ff3c1f3b6906df7d3156989`.
- Negative protected raw-ledger result: signed and pushed commit
  `7728980ee9aef449801b253c38dd50815c9a4cb8`.
- Parent profile: `da921x-manual-checkpoint-stage-control`.
- New profile: `da921x-manual-checkpoint-raw-write`.
- Canonical patch: `0332-pstore-qualify-Gemini-manual-raw-entry-write.patch`.
- Expected release: `7.1.3-gemini-checkpoint-raw-write`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The mode is default off. It keeps the exact DT/resource, mapping, stage, record
size, and full-readback gates of the manual control. It requires all-ones
headers on every not-yet-owned slot, commits only record 173, writes the valid
signature last, and makes checkpoint one unavailable. It never clears,
overwrites, or retries.

The selected profile has no clock backend, protected observer, BigiDVFS
backend, protected call, DA921x action, transition owner, CPU request, storage
access, timer, watchdog, reset, or power operation. Normal ramoops registration
remains skipped so Gemian is the independent recovery oracle. CPU8 and CPU9
admission remain closed.

## Associated code

- `patches/v7.1.3/0332-pstore-qualify-Gemini-manual-raw-entry-write.patch`
- `configs/gemini-manual-checkpoint-raw-write.fragment`
- `contract.json`
- `scripts/validate.py`
- `scripts/test-validate.py`
- `scripts/build-serviceability-dtb.sh`
- `scripts/build-candidate.sh`
- `scripts/test-candidate.sh`
- `scripts/install-boot2.sh`
- `scripts/collect-runtime.sh`
- `scripts/remote-runtime-probe.sh`
- `scripts/validate-runtime.py`
- `scripts/validate-retained.py`
- `scripts/test-runtime-tools.py`

## Admitted candidate

- Repository build commit: `24f0a696e1cedbf80f382ca04e9d812254c7e18f`
- Buildbox job:
  `24f0a696e1cedbf80f382ca04e9d812254c7e18f-da921x-manual-checkpoint-raw-write-m0`
- Package:
  `linux-7.1.3-gemini-da921x-manual-checkpoint-raw-write-998c2550-6b67b930`
- Raw Android-v0 image SHA-256:
  `6a2f698fe05a67a96ccb8ff282ac62668170e229125fe3ddeae3257ac135adf3`
- Exact 16 MiB boot2 SHA-256:
  `c10f2c03490fe1aa8ded11895a2d1817dd649edaffa307d0635fe2d69ce1c631`

The fetched package passed its complete checksum inventory. Two independent DT
constructions, raw assemblies, and padding constructions were byte-identical;
all 32 LK gates passed; 15 DT mutations, 24 unsafe live mutations, and 9 unsafe
retained-recovery mutations were rejected offline. The guarded installer then
resolved the live GPT and passed every inactive-target, geometry, power,
write, readback, and shutdown gate. See the
[deployment receipt](results/deployment-c10f2c03.txt).

## Procedure

1. Validate the exact patch, profile, canonical-series placement, default-off
   mode, all-ones prefix, one-record ceiling, signature-last ordering, full
   readback, live stage, and complete protected/CPU veto inventory.
2. Commit and push the definition with a clean worktree.
3. Build the exact commit on Buildbox with
   `KERNEL_PROFILE=da921x-manual-checkpoint-raw-write ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package and construct the current serviceability
   DT plus Android-v0 container twice independently.
5. Require the complete configuration, symbol, DT, LK, padding, and mutation
   gates before admitting one guarded `boot2` deployment.
6. Arm exact USB and changed-ID recovery before one physical selection. Return
   natively only after the live identity, serviceability, and write-stage
   result are attributable; then classify the recovered record before any
   successor.

## Decision map

- Live `commit=1 stage=success writes=1` plus exact Gemian recovery proves the
  raw writer and cross-version record format.
- Live success without recovery localizes the remaining defect to retained
  record format or Gemian recovery semantics.
- A live refusal remains inside its exact reported validation, mapping, prefix,
  write-precondition, metadata-readback, or payload-readback stage.
- Loss of serviceability without a valid recovered record is inconclusive and
  rejects this artifact without repetition.

No branch authorizes a protected clock call or CPU8/CPU9 admission.

## Conclusion

The one guarded deployment and physical selection are complete. Exact mainline
identity and serviceability passed, and the live marker reported
`commit=1 stage=success writes=1` with exactly one local full readback and zero
protected, clock, BigiDVFS, DA921x-write, or CPU actions. After the collector's
identity-gated native reboot, changed-ID Gemian found the exact committed
record 173 still valid in retained RAM and record 174 still empty. The writer,
signature-last commit, local readback, and warm-retention boundaries therefore
pass. See the
[runtime receipt](results/runtime-attempt-1-live-pass-retained-sparse-record-20260822.txt).

Gemian exposed no pstore file, so the original strict retained classifier
correctly rejected the stronger cross-version-recovery claim. The pinned
reader audit explains the result: record 173 is a sparse dmesg record behind
172 empty records, while the downstream reader advances only one dmesg index
per backend call and pstore stops when the backend returns zero. Its parser
accepts the record prefix, so this is an enumeration-position failure rather
than a raw-format failure. A live read-only probe also confirmed exact empty
headers in records 1--4 and a nonempty primary console, selecting record 1 as
the safe successor rather than overwriting the active console ring. See the
[post-runtime audit](results/post-runtime-sparse-dmesg-enumeration-audit-20260822.txt).

This makes no hardware-support claim and does not open CPU8 or CPU9 admission.

## Follow-up

Do not repeat this artifact. The ordered successor after this qualification is
owned by Roadmap Gate 7.
