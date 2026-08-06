# Experiment: DA921x page and BUCKB ownership audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-da921x-page-owner-audit` |
| Status | `completed` (partial source reconciliation; writable path rejected) |
| Subsystem | legacy DA9213/DA9214/DA9215 page, BUCKB, and provider ownership |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4; provider-owner R01/R02 |
| Conclusion | `rejected` for a currently authorized writable transaction |

## Question or hypothesis

Do the pinned read-only source, the dormant A36 model, and the sanitized
runtime observations establish enough DA921x page/selector ownership to add a
single bounded BUCKB write with readback and rollback?

The audit is deliberately source-only. It distinguishes observed bytes and
source constants from a proven page-selector protocol, writer owner, and
inverse operation. It does not try another device boot or repeat a successful
natural CPU8 cycle.

## Provenance and environment

- Repository commit reviewed: `8b9bf76f81484551d759f8753ecf9b3979324d6f`.
- Exact provider patch inputs: `0170`, `0172`, and `0173` in
  [`patches/series`](../../patches/series).
- The provider-owner refusal profile's earlier baseline was Buildbox-validated
  at commit `aaec484bacff7789ae445e3553da235219028dd0`. Its exact result,
  including the final configuration and checksums, is recorded in
  [`results/buildbox-handoff-profile-20260806.txt`](results/buildbox-handoff-profile-20260806.txt).
  The build remains compile-only and creates no boot candidate.
- The lease implementation was validated from the exact pushed reviewed
  commit by Buildbox. Its package identity, patch/config checksums, and
  no-write result are recorded in
  [`results/buildbox-transfer-lease-20260806.txt`](results/buildbox-transfer-lease-20260806.txt).
- Read-only board-contract evidence:
  [`da921x-i2c6-a72.md`](../../docs/hardware/da921x-i2c6-a72.md) and the linked
  identification lifecycle records.
- A72 prestate model: patch `0164`, with values carried into the dormant C
  ledger rather than a hardware access interface.
- The managed immutable userspace payload was searched separately; the
  bounded result is recorded in
  [`results/vendor-payload-search-20260806.txt`](results/vendor-payload-search-20260806.txt).

## Safety assessment

This is a read-only repository audit. It performs no I2C transfer, page
selection, register-data write, regulator vote, CPU request, partition access,
boot, reboot, or power transition. No device backup is created or needed.

The current standing boot2 authorization is not relevant: the audit does not
produce a candidate eligible for installation. A writable provider remains
forbidden until the missing owner and rollback evidence is closed.

## Associated code

- [`scripts/oracle.py`](scripts/oracle.py) checks the exact source facts and
  rejects the audit if the selected provider path gains a write or page-control
  operation.
- [`results/source-audit.tsv`](results/source-audit.tsv) is the sanitized
  row-by-row evidence ledger.
- [`results/oracle.txt`](results/oracle.txt) records the repeatable result.

Run from the repository root:

```sh
python3 experiments/2026-08-06-da921x-page-owner-audit/scripts/oracle.py
```

## Procedure

1. Inspect the fixed direct-address identity reads and the resource-only
   provider descriptors.
2. Compare the dormant A36 `page`/`BUCKB_VSEL` values with the independent
   read-only runtime record.
3. Check whether the source identifies a unique page owner, write transport,
   preserved control-byte mask, post-settle readback, generation handle, and
   inverse owner.
4. Fail closed if any of those requirements is absent or if the selected
   provider path contains a state-changing transfer.

## Observations

The source and sanitized runtime record establish these facts:

- The identity driver uses primary address `0x68` and a separate page-2 dummy
  address `0x69`; its fixed transcript is read-only.
- The resource-only provider reads VSEL registers `0xd7`/`0xd9` and control
  registers `0x5d`/`0x5e` through a combined pointer/read transfer. It uses
  masks `0x7f` and `0x01`, but no write operation.
- The dormant A36 ledger carries `da921x_page = 0x80` and
  `buckb_vsel = 0x46`. Those values are model/prestate assertions; no selected
  source path proves that `0x80` is the DA921x page-selector encoding or that
  the model owns the corresponding hardware state.
- The natural-cycle evidence records page `0x80` restoration and BUCKB/VSEL
  transitions, but it does not identify which Linux or firmware writer owns the
  page state, nor does it prove an arbitrary write/readback protocol.
- No source path proves that the `0x5e` bit-0 interpretation is safe to modify,
  that the two linear voltage tables match the populated rail, or that the
  primary/page-2 client split is the same ownership boundary used by the A72
  power sequence.
- The extracted userspace payload has no DA921x/page/BUCKB strings. This is a
  negative inventory result only; it does not substitute for private firmware
  or vendor-kernel ownership evidence.
- A prior pinned datasheet/source cross-check does provide partial page
  semantics: legacy `REG_PAGE 0x0`/`0x1` address windows and the `0x80`
  `PAGE_REVERT` behavior are documented, and the public Gemian driver fixes
  the owner-local mutex and vendor-shaped read/modify/write sequence. The
  reconciliation is recorded in
  [`results/source-reconciliation-20260806.txt`](results/source-reconciliation-20260806.txt).
- That vendor evidence does not transfer ownership to the current mainline
  I2C6 path. The vendor driver pauses DVFSP around each transfer, while the
  current mainline provider has no matching arbitration proof. The vendor
  observer's post-settle readbacks and pre-isolation inverse are useful
  evidence, but the mainline provider still has no equivalent transaction.
- The selected profile now enables the existing MT6797 DVFSP handoff owner
  before the I2C6-backed provider path. Buildbox confirms
  `CONFIG_MTK_MT6797_DVFSP_HANDOFF=y` together with the provider-owner
  refusal boundary. This closes a configuration omission; it does not prove
  a writable transaction or change the fail-closed refusal.
- The source chain now has an attributable handoff gate: the Gemini I2C6 DT
  node names `dvfsp_handoff`, the MT65xx transfer entry checks
  `mt6797_dvfsp_handoff_require_ready()`, and the selected profile enables the
  supplier. The provider still reaches the adapter through `__i2c_transfer()`
  and remains read-only. The pinned kernel-core excerpt now proves that this
  call reaches `adap->algo->master_xfer()`, so there is no provider-side
  dispatch bypass; the exact excerpt and hash are in
  [`results/i2c-core-dispatch-20260806.txt`](results/i2c-core-dispatch-20260806.txt).
  The provider also takes the root adapter lock required by the core. The
  handoff audit initially showed the precise remaining gap: readiness was
  checked at transfer entry, but no lease/token was held across the transfer
  and the vendor `SEMA_I2C_DRV` ownership operation was not represented. Patch
  `0174` now closes the Linux-side transfer lifetime with a generation/cookie,
  paired cleanup, and PM serialization; Buildbox validated the exact result.
  The vendor semaphore/firmware owner is still unproven. See
  [`results/dvfsp-lease-audit-20260806.txt`](results/dvfsp-lease-audit-20260806.txt).
  This still does not authorize a write.
- Patch `0174` is now a Buildbox-validated implementation of that Linux-side lease:
  it carries a generation/cookie across the complete MT65xx I2C6 transfer,
  serializes suspend/resume permission changes, and faults stale or duplicate
  release. Its exact compile/package result is recorded in
  [`results/buildbox-transfer-lease-20260806.txt`](results/buildbox-transfer-lease-20260806.txt).
  It does not
  represent the vendor `SEMA_I2C_DRV` semaphore, add a DA921x write, or
  authorize a device action.
- The retained vendor contract is reconciled explicitly in
  [`results/firmware-owner-lease-20260806.txt`](results/firmware-owner-lease-20260806.txt):
  `SEMA_I2C_DRV` is a firmware pause-source lease, not a Linux generation
  token or a hardware semaphore. The direct LK/TEE/SCP audit remains negative
  for a PCM restart writer, but ATF secure clock/semaphore access and an SCP
  computed/local alias remain unexcluded. Linux therefore cannot claim the
  firmware owner from the current evidence; the provider stays fail-closed.
- No bounded inverse exists for a provider write at or beyond the unresolved
  external-isolation boundary. The release callback therefore remains a
  structured `-EOPNOTSUPP` refusal.

The machine-readable ledger and oracle passed with the source facts separated
from the still-blocking mainline gaps:

```text
page_encoding=partially-proven
page_owner=candidate-owner;ready-gate-only;firmware-lease-unproven
write_transport=vendor-shape-known;mainline-arbitration-unproven
control_mask=vendor-bit0-known;mainline-contract-unproven
post_settle_readback=vendor-observed;provider-unimplemented
rollback_owner=pre-isolation-accepted;post-isolation-unresolved
decision=BLOCK_WRITABLE_PROVIDER
hardware_action=none
```

## Analysis

The existing evidence does establish more than the first pass of this audit:
the legacy page windows, `PAGE_REVERT`, register addresses, vendor mutex, and
vendor transfer shape are attributable. It still does not make those vendor
operations a mainline API. A future provider must transfer I2C6/DVFSP
ownership explicitly, establish one owner for page selection and one owner for
the rail mutation, read back the complete affected state after the settle
interval, and release only with a same-generation handle. If any post-state
differs, it must retain/fault rather than guess an inverse.

This reconciliation is progress: it rules out both an unsafe direct write and
an unnecessary search for already-recorded page semantics. The next work is a
source-only mainline ownership/arbitration seam, not a device boot.

## Conclusion

`rejected` for the hypothesis that the current source and evidence authorize a
writable BUCKB provider. The existing resource-only provider and paired
acquire/release refusal boundary remain the correct implementation boundary.

## Follow-up

The next source-only action is to obtain receiver-side proof of the firmware
ownership lease corresponding to `SEMA_I2C_DRV`, including stopped-state and
shared-clock validation, rather than infer it from the validated Linux lease.
In parallel, close the DA921x page/control-mask, settled readback, and
rollback-owner boundaries. The validated Linux lease maps the mainline handoff
into a default-off provider without claiming hardware support. Only after
those ownership and rollback gates close may a writable implementation be
designed. The P24/P28/P30/P32/A26/A14 gates remain independent blockers.
