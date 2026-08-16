# Experiment: LK handoff DTB control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-16-mainline-lk-handoff-dtb-control` |
| Status | exact candidate deployed and powered off; one boot2 selection pending |
| Subsystem | Planet LK Android-v0 handoff, appended DTB, arm64 primary entry |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | GAEL no-stage lower-boundary localization |

## Question or hypothesis

Does the exact stopped `GAEL-20260816-A` kernel reach an arm64 entry-ledger
stage when its current DTB is replaced by the exact Stage-27 DTB already proven
serviceable through the same device bootloader?

The kernel, configuration, initramfs, load addresses, command line, retained
ledger, and CPU policy remain exact. The DTB is the one decision-changing
input. Any valid E0 or later record proves that LK decompressed and branched to
the current Image, while implicating current-DTB processing before that branch
in the prior `no-stage` result. Another exact `no-stage` result means the
current DTB alone does not explain the failure and keeps the boundary at the
current Image/gzip/final handoff or the E0 refusal path.

## Provenance and environment

- Current kernel package: exact Buildbox output from commit
  `98996fdfbf09f8de2a6b86e488defef22fcc7968`, profile
  `da921x-modules-arm64-entry-ledger`, release
  `7.1.3-gemini-entryled-a`.
- Current `Image.gz`: SHA-256
  `539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe`.
- Control DTB: exact Stage-27
  `mt6797-gemini-pda-da921x-lifecycle.dtb`, SHA-256
  `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806`.
  Stage 27 was serviceable on this device and used the same LK addresses,
  command line, module-free initramfs, board compatibility, memory map, and
  retained ramoops reservation.
- Initramfs: exact serviceability image, SHA-256
  `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f`.
- Public loader reference: Planet LK repository
  `https://github.com/dguidipc/gemini-lk-android8`, commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`. It is source-contract
  evidence, not a byte-identity claim for the installed loader.
- Boot path: LK Android-v0 container on inactive logical `boot2`.
- No kernel compilation was needed: this is a recontainer of the exact
  Buildbox-validated kernel with an exact runtime-proven DTB. No native VM
  build was run.
- Exact raw container: SHA-256
  `e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086`,
  6,879,232 bytes. Exact 16 MiB boot2 payload: SHA-256
  `68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67`.

## Safety assessment

The GAEL implementation and its fail-closed write boundary are byte-identical
to the stopped candidate. It may write only one short record per existing 4
KiB slot in `[0x444bb000,0x444bf000)`. The Stage-27 DTB retains the exact
`ramoops@44410000` reservation, `[0x44410000,0x444f0000)`, `no-map`, and the
same four dmesg zones. The first two entry stages still require EL1/EL2 with
translation and data cache off plus four exact empty `DBGC` headers. The later
stages retain byte-exact earlier-slot and flat-DT/reservation checks.

There are no DA921x register-data writes, regulator actions, CPU admission,
storage operations from the kernel, or retry/repair/clear paths. CPU8 and CPU9
remain closed. The only device storage change is the standing-authorized,
guarded write to live-GPT-resolved inactive logical `boot2`; it records the
predecessor checksum, uses the project-start backup as recovery, requires
stable power and complete readback, and shuts the device down after success.
No fresh device backup is required or created.

Stop without a write on any source, checksum, manifest, partition, active-root,
mount, size, writable-state, power, ledger-header, or readback mismatch. Never
substitute another partition and never reboot automatically. Visual screen or
reboot behavior is not attributable evidence.

## Associated code

- `scripts/build-candidate.sh`: exact-input, two-construction Android-v0
  candidate builder using an explicit control DTB.
- `scripts/test-candidate.py`: independent package, DTB, ledger, idmap,
  serialization, LK-gate, and negative-mutation validator.
- `scripts/install-boot2.sh`: source-pinned guarded installer with live GPT
  resolution, no new backup, full readback, and clean shutdown.
- `results/lower-boundary-audit-20260816.txt`: stopped/control container,
  Image-entry, public-LK, load-range, and DTB comparison.
- `results/offline-candidate-validation-20260816.txt`: exact construction and
  independent validation identities.
- `results/predeployment-hypothesis-20260816.txt`: frozen one-attempt
  hypothesis, refusal gates, and decision map.
- `results/deployment-20260816.txt`: sanitized live-GPT, empty-ledger,
  predecessor, full-readback, observer, power, and shutdown receipt.

The ignored candidate and private runtime captures remain below `artifacts/`.

## Procedure

1. Compare the stopped GAEL candidate with the last serviceable Stage-27
   candidate at every boundary before `primary_entry`, including Android-v0
   fields, gzip stream, load ranges, Image header/branch, loader state teardown,
   appended-DTB scan, and DTB structure.
2. Freeze one discriminator only: exact GAEL kernel plus exact Stage-27 DTB.
   Preserve the initramfs, addresses, command line, GAEL code/configuration,
   retained zones, and CPU policy.
3. Construct the raw image twice and the 16 MiB payload by two independent
   padding methods. Require byte identity, all 32 LK gates, exact hashes, and
   rejection of six structural mutations.
4. Commit and push the exact experiment definition and candidate identities.
   Pre-arm a long changed-cycle capture so a powered-off owner interval cannot
   expire the observer.
5. Re-read the four live ledger headers. Resolve inactive logical `boot2` from
   the live GPT, record its predecessor, write only if different, require full
   readback, and shut Gemian down cleanly.
6. Select boot2 once. On the changed return to Gemian, immediately capture
   pstore and a boot-ID-bounded, read-only 16 KiB snapshot of slots 171--174,
   classify the highest exact GAEL stage, confirm boot2 identity, and stop this
   exact artifact.

Exactly one physical selection is permitted. Do not repeat the exact artifact
without a new decision-changing measurement.

## Observations

The lower-boundary audit eliminated malformed Android-v0 fields, gzip validity,
decompression bounds, load overlaps, Image-header size/flags, and final branch
encoding as discriminators. Both Images branch exactly to their respective
`primary_entry`. The pinned public LK source disables unified cache and the MMU
before the final arm64 branch, so the normal E0 state gate should accept that
contract. The installed loader is not asserted byte-identical to the public
source, but the same device loader successfully handed off Stage 27.

The remaining meaningful pre-branch input difference is the appended DTB,
which LK scans, opens, merges, and mutates before its final branch. Both DTBs
retain the exact board, memory, and ramoops/GAEL reservation contract. The
current DTB nevertheless has a large structural delta from Stage 27, including
`/chosen` children and multiple potential LK overlay/handoff targets. Static
analysis cannot prove that the installed LK accepts and rewrites that exact
current DTB.

Two independent control assemblies were byte-identical; two independent 16 MiB
constructions were byte-identical. All 32 LK container gates passed and all six
independent structural mutations were rejected. Device access and hardware
writes were absent during construction and validation.

Before deployment, a 12-hour changed-cycle observer was armed on known-good
Gemian. A bounded read-only 16 KiB capture kept the same boot identity and
found all four headers exact and empty. The guarded installer resolved the one
inactive, unmounted live-GPT `boot2`, recorded the stopped GAEL predecessor,
wrote the exact control, synchronized and flushed it, and matched both its
complete device checksum and an independent full-byte readback. It then
cleanly powered Gemian off. The observer independently confirmed the
disconnect and remains armed for the physical selection and changed return.

## Analysis

This is not a marker-only or kernel/config-identical repeat. The DTB is changed
to a runtime-proven control specifically at the only unresolved input that LK
actively processes before the arm64 branch. A valid E0 is sufficient to close
the LK-to-Image handoff for the current kernel. A later stage adds localization
but is not required for the primary decision. Another `no-stage` result is also
useful: it rejects the current DTB as the sole cause and focuses the next audit
on current gzip/Image acceptance, the actual installed loader's final handoff,
or the retained E0 observation gate.

## Conclusion

Deployment result: the lower audit selected one safe, falsifiable
discriminator, the exact candidate passed construction and independent
validation, and guarded deployment plus shutdown passed. No runtime conclusion
or hardware-support change exists until the one boot2 attempt is recovered.

## Follow-up

Deploy and recover the one frozen attempt. The ordered action after its exact
stage classification belongs in [`docs/ROADMAP.md`](../../docs/ROADMAP.md).
