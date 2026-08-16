# Experiment: arm64 entry four-stage retained ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-16-mainline-arm64-entry-ledger` |
| Status | one exact attempt completed with no valid stage; artifact stopped |
| Subsystem | arm64 primary entry, MMU transition, setup_arch, pstore/ramoops |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline pre-setup_arch localization |

## Question or hypothesis

Does the exact current mainline artifact reach arm64 `primary_entry`, complete
MMU-off CPU setup, enable the MMU, or complete the reserved-memory scan before
its automatic return to known-good Gemian?

Four independent retained records distinguish those boundaries without normal
ramoops registration. This is an entry-localization experiment, not a DA921x,
regulator, CPU-admission, or hardware-support experiment.

## Provenance and environment

- Kernel: pinned Linux 7.1.3 from `kernel/manifest.json`.
- Parent profile: `da921x-resource-only-provider-modules-control`.
- Experiment profile: `da921x-modules-arm64-entry-ledger`.
- Patch: canonical `0281-arm64-add-Gemini-entry-stage-ledger.patch` after the
  exact canonical series through 0280.
- Design authority: the completed
  [entry-ledger safety audit](../2026-08-16-mainline-arm64-entry-ledger-audit/README.md).
- Build backend: explicit Buildbox only; native VM builds remain prohibited.
- Boot path: retained LK Android-v0 container on inactive logical `boot2`.
- Recovery path: ordinary known-good Gemian and changed-cycle pstore/raw-zone
  capture.
- Exact build and package input: commit
  `98996fdfbf09f8de2a6b86e488defef22fcc7968`, Buildbox job
  `98996fdfbf09f8de2a6b86e488defef22fcc7968-da921x-modules-arm64-entry-ledger-m0`,
  release `7.1.3-gemini-entryled-a`.
- Exact raw container: SHA-256
  `1249d907795ab80c5a290887847e497bf672e5bdf2c7617096a1209db464341c`,
  6,879,232 bytes. Exact 16 MiB boot2 payload: SHA-256
  `a81939b41a64a362744580bec559baecb3fe13938187f34b3f1b9ad5f09527f2`.
- Deployment resolved inactive logical `boot2` as `/dev/mmcblk0p30`, recorded
  predecessor SHA-256 `ac849d9aca9454d5d6a29d25a67b5d27fcef94e16bb881f4d14db09d0d29d75f`,
  and verified the exact 16 MiB payload by full readback before clean shutdown.
- Returned Gemian had a changed boot ID. Immediate pstore and bounded raw-zone
  recovery found no valid GAEL stage; post-cycle boot2 still matched the exact
  deployed payload.
- The first full Buildbox link of commit `d126eebf32ca0a4746e5060fb4c4e66479b3300a`
  failed closed before packaging: `.idmap.text` was `0x1124` bytes and violated
  arm64's one-page identity-map assertion. No candidate or device action
  occurred. A 76-byte successor at commit
  `a6777c3b8882a8aa39d65f42f7cd2233e45b0ab7` reduced the generated head
  identity section to `0xe0c`, but the full identity section still exceeded the
  page after other arm64 entry objects were included. The current 34-byte
  token/stage record and bounded header loops preserve the decision and safety
  contract while removing the remaining unrolled entry code.

## Safety assessment

The exact authorized write boundary is token `GAEL-20260816-A`, four existing
4 KiB dmesg zones at `[0x444bb000,0x444bf000)`, and at most one short record per
slot. The first two checkpoints execute without calls, stack access, literal
pools, or writes outside that range. They accept only EL1/EL2 after directly
proving SCTLR translation and data-cache bits clear; require four exact `DBGC`
headers; preserve `x0`--`x8`, `x16`--`x30`, and `sp`; and use aligned 32-bit or
narrower accesses. Later stages map only the four-zone range and accept every
earlier slot only when empty or byte-exact. The final stage also requires the
exact Gemini flat DT, ramoops address/size, `no-map`, and memblock reservation.

Every stage writes data before start and size, issues full-system ordering,
then reads back the signature, lengths, and complete record. No stage retries,
repairs, clears, or overwrites. The runtime patch performs no storage,
filesystem, firmware, I2C, regulator, clock, CPU admission, timer, watchdog,
reset, reboot, or power operation. CPU8 and CPU9 stay closed.

The guarded installer may write only live-GPT-resolved inactive `boot2`, records
but does not newly back up its predecessor, requires full-partition readback,
and shuts Gemian down after success. The project-wide device backup captured at
project start remains the recovery source. Stop on any source, config, package,
record, header, partition, power, or readback mismatch. Visual screen state is
not attributable evidence.

The owner explicitly authorized this exact implementation, Buildbox build, and
one boot2 attempt on 2026-08-16 and granted standing authorization for future
diagnostics within the same documented fail-closed retained-RAM policy. See
`results/owner-authorization-20260816.txt` and `docs/SAFETY.md`.

## Associated code

- `scripts/validate.py`: exact patch/profile/assembly/C safety validator.
- `scripts/test-validate.py`: unsafe mutation rejection suite.
- `scripts/build-candidate.sh`: source-pinned, two-construction exact candidate
  builder.
- `scripts/test-candidate.py`: independent package, ledger, idmap, LK layout,
  and mutation validator.
- `scripts/install-boot2.sh`: source-pinned live-GPT installer with predecessor
  checksum, no new backup, full readback, and shutdown on success.
- `results/offline-implementation-validation-20260816.txt`: patch application,
  compiler-smoke, oracle, manifest, mutation, and checkpatch evidence.
- `results/buildbox-success-20260816.txt`: exact successful full-link and
  fetched-package evidence.
- `results/offline-candidate-validation-20260816.txt`: exact container identity
  and independent validation evidence.
- `results/predeployment-hypothesis-20260816.txt`: frozen hypothesis, unique
  evidence, refusal gates, and decision map for the single physical selection.
- `results/deployment-20260816.txt`: sanitized live-GPT, predecessor, full
  readback, power, and clean-shutdown receipt.
- `results/runtime-attempt-1-no-stage-20260816.txt`: changed-cycle, pstore,
  raw-zone, classifier, and post-cycle candidate-identity evidence.
- The audit's `scripts/record-layout.py` freezes the exact bytes and assembly
  words; its classifier and fixtures own returned-Gemian interpretation.

## Procedure

1. Validate patch application, profile isolation, exact hooks, MMU/cache and
   register gates, record bytes, independent-stage rules, normal-ramoops bypass,
   and prohibited-effect absence.
2. Run manifest invariants, Python/shell checks, strict patch review, and the
   focused mutation suite.
3. Commit and push the exact clean input, build only with explicit Buildbox,
   and fetch only its validated package.
4. Independently validate package provenance, resolved configuration, Image,
   DTB, symbols, and exact source-to-record identity. Construct and validate one
   Android-v0 candidate with the unchanged working initramfs/LK contract.
5. Freeze the exact candidate hypothesis and decision map. Re-read the four
   live headers immediately before deployment and require the expected state.
6. Pre-arm changed-cycle recovery. Install only to live-GPT-resolved inactive
   `boot2`, require full readback, and shut the device down.
7. Select boot2 once. After return to Gemian, immediately recover pstore and the
   bounded four-zone read, classify every independent stage, and stop the exact
   artifact.

Exactly one physical boot selection is authorized. The same candidate must not
be repeated unless repeatability itself is separately justified by new
decision-changing evidence.

## Observations

Canonical patch 0281 applies to the exact managed source through patch 0280.
The initial MMU-off `head.S` and later-stage C translation units compiled
without diagnostics under the Buildbox cross-toolchain, but the first complete
Buildbox link correctly rejected an identity-mapped section of `0x1124` bytes
against arm64's 4 KiB bound. That compile-only evidence is not treated as a
build result. The first compact revision reduced the generated head identity
section from `0x1124` to `0xe0c`, but the complete link still exceeded the one
page bound. The current implementation writes only the exact token and stage
tag; the stage-owned physical zone supplies slot identity, and byte-exact
matching plus the candidate/deployment checksum chain supplies integrity. It
also checks the four and three empty-header ranges with fixed-count loops. Its
validator matches the assembly records byte-for-byte with the frozen generator,
confirms the exact hooks and refusal rules, and rejects all 16 unsafe mutations.
All 79 manifest profiles preserve the canonical-series invariant.

The initial strict checkpatch review had zero checks, five expected warnings,
and the deliberately absent synthetic-author sign-off. The final bounded
revision passed the complete Buildbox link with an identity section of `0xfb8`
bytes, leaving 72 bytes below arm64's 4 KiB hard bound. Its validated fetched
package produced two byte-identical raw containers and two byte-identical 16
MiB payloads using independent padding methods. Independent validation passed
all 32 LK gates and rejected all six container mutations.

The guarded installer resolved inactive, unmounted logical `boot2`, recorded
the predecessor without a fresh backup, wrote the exact candidate, synced and
flushed it, and passed both the remote full checksum and an independent local
full-byte comparison. It then cleanly powered Gemian off. The pre-armed helper
confirmed that disconnect but expired during the long powered-off interval
before physical selection. After the owner reported the one boot2 selection,
the first SSH probe timed out and ordinary Gemian then returned with a boot ID
different from the deployment boot. A replacement read-only capture remained
bound to that returned boot throughout pstore and raw-zone recovery.

Pstore contained no files. The exact 16 KiB read of slots 171--174 had stable
pre/post boot identity, all four headers remained `DBGC` with zero start and
size, and no GAEL token existed. The frozen classifier returned `no-stage`.
Live GPT still resolved boot2 as `/dev/mmcblk0p30`, and its complete post-cycle
checksum remained the exact deployed payload. The one-attempt artifact is
stopped and must not be repeated unchanged.

## Analysis

The previous C-only checkpoint could not distinguish absence of Image entry
from refusal before its post-memblock write. This result adds that distinction
but takes the negative branch: neither of the MMU-off entry records nor either
independent mapped record survived. Because the headers were exact and empty
both before and after the changed cycle, this is not a malformed-record,
duplicate-slot, stale-payload, classifier-only, or wrong-candidate result.

The attributable boundary is now: Image entry remains unestablished, or both
entry writers safely refused and execution stopped before the independent
post-MMU stage. It does not prove an LK defect, because E0 deliberately refuses
unexpected incoming EL/MMU/cache state and retained physical access itself is
part of that observation. It does rule out treating any later DA921x/provider,
initcall, regulator, or CPU-admission code as the next useful boundary.

## Conclusion

The exact candidate produced an attributable `no-stage` result. Image entry is
not established, no DA921x/provider lifecycle evidence exists, and no hardware
support claim changes. CPU8 and CPU9 remain closed.

## Follow-up

Do not repeat this artifact. Follow the lower boot-boundary audit and selected
next observation owned by [`docs/ROADMAP.md`](../../docs/ROADMAP.md).
