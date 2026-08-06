# Experiment: DA921x page and BUCKB ownership audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-da921x-page-owner-audit` |
| Status | `completed` (partial source/image reconciliation; writable path rejected) |
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

The audit is deliberately hardware-independent. It distinguishes observed
bytes, source constants, and bounded scans of the retained private images from
a proven page-selector protocol, writer owner, and inverse operation. It does
not try another device boot or repeat a successful natural CPU8 cycle.

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
- The retained full-backup LK, TEE/ATF, and SCP images were scanned separately;
  the bounded result is recorded in
  [`results/secure-owner-image-scan-20260806.txt`](results/secure-owner-image-scan-20260806.txt).

## Safety assessment

This is a read-only repository audit. It performs no I2C transfer, page
selection, register-data write, regulator vote, CPU request, device access,
boot, reboot, or power transition. It reads only the already-retained,
Git-ignored full-backup images; no new device backup is created or needed.

The current standing boot2 authorization is not relevant: the audit does not
produce a candidate eligible for installation. A writable provider remains
forbidden until the missing owner and rollback evidence is closed.

## Associated code

- [`scripts/oracle.py`](scripts/oracle.py) checks the exact source facts and
  rejects the audit if the selected provider path gains a write or page-control
  operation.
- [`scripts/audit-secure-owner-images.sh`](scripts/audit-secure-owner-images.sh)
  performs the bounded read-only LK/TEE/SCP image scan without staging raw
  contents.
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
5. Scan the retained LK, TEE/ATF, and SCP images for bounded owner markers and
   direct controller/CSPM literals, retaining only hashes and sanitized counts.

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
  for a PCM restart writer; it attributes ATF secure clock/semaphore access,
  while an SCP computed/local alias remains unexcluded. Linux therefore cannot
  claim the `SEMA_I2C_DRV` firmware owner from the current evidence; the
  provider stays fail-closed.
  Candidate AO already validated the receiver-side stopped PCM signature and
  one balanced ungated-to-gated I2C_APPM transition with a stable 45-second
  late check while I2C6 remained disabled. That result must not be repeated;
  the receiver patch contains no `PAUSE_I2CDRV` or `FW_DONE` protocol, so the
  remaining question is whether the validated stopped receiver is authoritative
  for the vendor per-transfer lease.
- The retained Gemian archive was scanned read-only for a direct literal owner
  implementation. The nine `pcm_*.bin` files contain no raw little-endian CSPM
  base (`0x11015000`), PCM control address (`0x11015018`), CSRAM base
  (`0x0012a000`), or `FW_DONE` (`0x8000`) literal. The three vcorefs blobs each
  contain one encoded occurrence of the CSPM key and several `0x2000` values,
  but the raw scan is not a PCM-instruction decoder and cannot turn those
  values into proof of the `SEMA_I2C_DRV` protocol. The archive contains
  userspace SPM blobs only; it does not contain the LK, TEE, or SCP payloads
  needed to close the external-owner question. The bounded result is in
  [`results/pcm-firmware-owner-scan-20260806.txt`](results/pcm-firmware-owner-scan-20260806.txt).
- The retained secure images add a bounded negative cross-domain check. LK
  contains generic bootloader I2C markers but no named `SEMA_I2C_DRV` marker;
  TEE/ATF contains the MT6797 PSCI/iDVFS paths, and the existing direct-
  immediate audit attributes its CSPM/secure-semaphore writes; SCP contains
  CM4-A DVFS/SPM/IPI paths but no I2C6 or `SEMA_I2C_DRV` marker. The exact
  external audit still finds no PCM-restart writer, while an SCP-local alias
  remains unexcluded. None of the six images contains a direct little-endian
  `0x1100e000`, `0x11015000`, `0x11015018`, or `0x0012a000` literal. The new
  scan is therefore only a bounded strings/literal cross-check; computed
  accesses and secure aliases remain unexcluded, and no `SEMA_I2C_DRV` owner
  is promoted. See
  [`results/secure-owner-image-scan-20260806.txt`](results/secure-owner-image-scan-20260806.txt).
- A bounded AArch64 disassembly of the retained TEE tightens that result. Its
  20 direct CSPM accesses are limited to the keyed `+0` write (`0x0b160001`)
  and the secure-semaphore `+0x448` write/poll on bit 0; no direct PCM
  `+0x18` kick/reset or `SW_RSV0..6` lease words appear in the exact code
  extent. This identifies ATF as an interfering secure control/semaphore
  owner, not the missing `SEMA_I2C_DRV` receiver. Computed or secure aliases
  remain out of scope. See
  [`results/tee-owner-disassembly-20260806.txt`](results/tee-owner-disassembly-20260806.txt).
- A bounded Thumb disassembly of the retained SCP image narrows the remaining
  alias ambiguity without promoting an owner. The bit-13 test at the DMA
  remap initializer is paired with the `Support 4GB DRAM`/`Not support 4GB
  DRAM` messages and writes the DMA remap register. A nearby `0x2000` write
  targets the Cortex-M NVIC pending-clear window from an interrupt-control
  path. The DVFS/SPM function logs `SPM_SW_RSV_3` and polls local status, but
  exposes no physical CSPM/PCM base, I2C6 owner, or pause/release transaction.
  These paths are generic DMA, interrupt, clock, and SPM plumbing—not
  `SEMA_I2C_DRV` proof. Computed or secure aliases remain unexcluded. See
  [`results/scp-owner-disassembly-20260806.txt`](results/scp-owner-disassembly-20260806.txt)
  and the exact [SCP alias inventory](results/scp-alias-inventory-20260806.txt).
- A follow-up bounded computed-address scan followed every PC-relative literal
  in the DVFS/SPM, clock-setting, and interrupt-control windows and checked
  immediate address construction. It adds `0xa000601c`, `0x400a4010`, and
  `0x400a4004` to the classified SCP-local control/clock/IRQ set; the only
  address-like immediate (`orr #0xa0000`) builds an encoded SPM request/status
  value and is not dereferenced as a pointer. No AP I2C6/CSPM/PCM/CSRAM or
  shared-memory target is constructed in these paths, and no pause/release
  transaction appears. Complete CM4 and secure address translation remains
  unavailable, so this strengthens but does not close the owner proof. See
  the [computed-address audit](results/scp-computed-address-audit-20260806.txt).
- Patch `0175` now defines the separately reviewed firmware callback contract:
  it carries the vendor pause source, `SW_PAUSE`/`FW_DONE` masks, 2 ms bound,
  Linux generation/cookie, and a paired opaque release handle. It is
  default-unregistered and contains no MMIO or I2C operation, so it narrows the
  protocol boundary without proving that the receiver or any external domain
  is authoritative. Its exact Buildbox validation is recorded in the contract
  experiment; attributable firmware evidence remains required. The contract is
  tracked in the [firmware lease experiment](../2026-08-06-mt6797-dvfsp-firmware-lease/)
  and still requires external-owner evidence.
- The exact retained vendor-kernel ELF provides positive Linux-side evidence
  for the same contract: semaphore user 1 routes to
  `cspm_pause_pcm_running(PAUSE_I2CDRV)`, writes SW_PAUSE bit 13 for all three
  clusters, polls FW_DONE bit 15 for all three status words within 2 ms, and
  releases the paired clock/reference state around the I2C transaction. This
  validates the historical caller contract but does not establish that the
  Candidate AO stopped receiver is authoritative or identify a separate
  secure/SCP writer. See the [vendor-kernel contract](../2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-kernel-sema-contract-20260806.txt).
- The vendor ELF and Candidate AN observer also match exactly on the CSPM
  register window and offsets: `0x11015000..0x11015fff`, `CON1 0x01c`,
  `PWR_IO_EN 0x02c`, `REG15 0x13c`, timer `0x150`, FSM `0x178`, and
  `SW_RSV0..6 0x608..0x620`, including the three pause and three FW_DONE
  words. This proves receiver register-window identity, not authority:
  Candidate AN did not exercise the handshake, observed no FW_DONE response,
  and left I2C_APPM ungated. See the [register identity reconciliation](../2026-08-06-mt6797-dvfsp-firmware-lease/results/receiver-register-identity-20260806.txt).
- No bounded inverse exists for a provider write at or beyond the unresolved
  external-isolation boundary. The release callback therefore remains a
  structured `-EOPNOTSUPP` refusal.

The machine-readable ledger and oracle passed with the source facts separated
from the still-blocking mainline gaps:

```text
page_encoding=partially-proven
page_owner=candidate-owner;ready-gate-only;firmware-lease-unproven
receiver_register_identity=exact-offset-match-proven
receiver_authority=unproven-no-handshake
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

The next source-only action is to prove that the already validated one-way
receiver is authoritative for the firmware ownership lease corresponding to
`SEMA_I2C_DRV`, or to obtain a separately reviewed firmware protocol. Do not
repeat Candidate AO's stopped-state/clock-normalization boot. In parallel,
close the DA921x page/control-mask, settled readback, and rollback-owner
boundaries. The validated Linux lease maps the mainline handoff into a
default-off provider without claiming hardware support. Only after those
ownership and rollback gates close may a writable implementation be designed.
The P24/P28/P30/P32/A26/A14 gates remain independent blockers.
