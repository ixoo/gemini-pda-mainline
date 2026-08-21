# Experiment: mainline secure replay epoch audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-secure-replay-epoch-audit` |
| Status | completed offline audit; private replay-zero initialization confirmed |
| Subsystem | MT6797 preloader, BL31 primary entry, and private A72 replay state |
| Device variant | Planet Gemini PDA named development unit |
| Date | 2026-08-21 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, production A34 provenance owner |

## Question or hypothesis

Does the exact boot chain initialize the secure firmware's private A72 replay
ledger to zero on primary BL31 entry, or can that byte survive because it lies
outside the file-backed secure payload?

The positive hypothesis requires one complete static chain: the retained
preloader must load either authenticated TEE slot before secure handoff, both
slots must contain the audited payload, primary BL31 entry must explicitly
zero a range containing the replay byte, and no pre-A34 writer may set it.
Reset-history fields and preserved ATF logs are not substitutes for that
chain.

## Provenance and environment

- Repository input: signed and pushed commit
  `b597ea85c3069b477ae41ad62f025b498e62cf17`.
- The two retained preloader boot-region images are byte-identical at SHA-256
  `25319ce877bd17b204fa264645aebf4583ec10ae2f05f6d8a7fff5efe4c06246`.
- The retained logical `tee1` and `tee2` images are byte-identical at SHA-256
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
- Private images were inspected read-only. Only hashes, analysis addresses,
  bounded control-flow facts, and conclusions are recorded here; no firmware
  bytes or private paths are committed.
- Secure-payload addresses use the previously published analysis mapping
  convention with base `0xff3c0`; they are not physical access proposals.
- The managed analysis VM was used only for bounded static disassembly. There
  was no kernel build, Buildbox job, device contact, or runtime attempt.

Exact sanitized facts are frozen in
[`results/provenance-20260821.txt`](results/provenance-20260821.txt), and the
decision chain is in
[`results/control-flow.tsv`](results/control-flow.tsv).

## Safety assessment

This audit was offline and read-only. It did not contact the Gemini, issue an
SMC, read or write a live partition, build a kernel, create a boot image,
request CPU hotplug, change MMIO or regulator state, reboot, or shut down the
device.

The result does not authorize a CPU request. A34 still requires a separately
proven platform or external reset and the complete immutable Linux owner
tuple. Ordinary Linux reboot provenance remains rejected.

## Procedure

1. Verify both retained preloader boot-region images and both retained TEE
   slots byte-for-byte.
2. Separate the preloader's USB-download path from its regular boot-loader
   path.
3. Trace the regular path's primary `tee1` load, `tee2` fallback, MediaTek
   header validation, success join, and ATF handoff.
4. Reconstruct the exact BL31 primary-entry calls and their literal arguments.
5. Disassemble the called memory helper and verify its complete write
   behavior.
6. Prove the private replay byte lies inside the first cleared range.
7. Reconcile that initialization with the previously frozen writer inventory
   and A26 boot veto.
8. Recheck whether ATF logs or known reset-history fields add an independent
   current-epoch attestation signal.

## Observations

The exact preloader's regular boot-loader function converges its boot-mode
branches before loading LK and secure firmware. It first calls the authenticated
image loader for `tee1` at analysis address `0x20e4d2`; on failure it retries
the `tee2` name at `0x20e4fc`. Both retained slots are byte-identical. The
MediaTek header parser at `0x2134a8` requires magic `0x58881688`. Only the
success path reaches the ATF handoff call at `0x20e540`.

The exact BL31 primary entry at analysis address `0x100000` calls helper
`0x11053c` at `0x1000f4` with start `0x11d340` and size `0x578c`. The helper
requires 16-byte alignment, computes the exclusive end, writes pairs of zero
registers in 16-byte steps, and zeroes any byte tail. The resulting cleared
range is `[0x11d340, 0x122acc)`.

The private replay ledger byte is at `0x11ea24`, offset `0x16e4` from that
range's start. It is therefore explicitly overwritten with zero by primary
BL31 entry even though it is outside the file-backed payload extent. This is
stronger than the earlier on-image-zero observation.

The previously frozen complete static writer inventory remains unchanged:
the A72 CPU-on family sets target bits and deferred teardown clears them. The
existing A26 veto prevents the set path before A34 publication. Once primary
entry has cleared the byte, no known writer changes it before the future owner
evaluates the initial tuple.

ATF log setup is not the proof. Its non-secure control buffer can preserve
prior content on abnormal boots and exposes no unique secure generation.
Likewise, raw TOPRGU status, retained preloader status, and LK boot reason are
still reset-path observations. They do not become independent secure-image
attestation merely by being combined.

## Analysis

The secure replay prerequisite has two parts that must stay separate. This
audit confirms the firmware initialization half: whenever the accepted boot
path reaches primary entry of either retained TEE slot, the exact BL31 code
actively clears the complete BSS range containing the private replay ledger.
The fact no longer depends on storage padding, DRAM power loss, Linux zero
state, an active affinity query, or retained ATF-log contents.

This does not classify the reset that led to that entry. A34 intentionally
requires a known-good platform or external reset because a prior partial A72
attempt can leave hardware and cross-owner state outside this single byte.
The raw TOPRGU and ram-console snapshots must therefore be reconsidered only
as inputs to a strict platform-reset classifier. An ordinary Linux reboot
cannot be renamed as platform reset by this result.

There is also no new kernel-visible runtime measurement of the secure image.
The exact duplicate-slot identity and entry behavior form a pinned board
firmware contract for this named device and revision. A production owner must
fail closed if that contract is not selected and must still consume a
separately proven current reset provenance before asserting
`OWNER_SAFE_ZERO`.

## Conclusion

`confirmed` for explicit primary-entry zero initialization of the private A72
replay ledger by the exact retained BL31 payload.

`confirmed` for byte-identical `tee1`/`tee2` fallback inputs and the regular
preloader load-to-handoff chain.

`rejected` for using preserved ATF logs, raw TOPRGU status, ram-console status,
LK boot reason, Linux zero state, or an ordinary reboot as standalone secure
epoch authority.

The private replay-zero half of A34 is now closed conditionally on separate
platform/external-reset provenance. The production A34 owner, lifecycle
publication, CPU8 request, boot candidate, and device attempt remain closed.

## Associated records

- [`DESIGN.md`](DESIGN.md) freezes the refined A34 authority boundary.
- [`results/control-flow.tsv`](results/control-flow.tsv) records the exact
  static chain and rejected shortcuts.
- [`results/provenance-20260821.txt`](results/provenance-20260821.txt) records
  exact sanitized identities and range arithmetic.
- [`scripts/validate.py`](scripts/validate.py) validates the frozen audit.
- [`results/audit-validation-20260821.txt`](results/audit-validation-20260821.txt)
  is the passing validation receipt.

Run from the repository root:

```sh
python3 experiments/2026-08-21-mainline-secure-replay-epoch-audit/scripts/validate.py
```

## Follow-up

The authoritative next action is maintained in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Audit a strict platform/external
reset classifier using the already implemented immutable TOPRGU and retained
ram-console snapshots. Require source-backed reset-to-primary-entry semantics;
unknown or ordinary-Linux reset provenance must keep A34 CLOSED. Do not add a
production owner, CPU request, boot candidate, or device action until that
classifier is frozen and proven.
