# Experiment: DA921x page and BUCKB ownership audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-da921x-page-owner-audit` |
| Status | `completed` (negative source-only audit) |
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

- Repository commit reviewed: `2bbd82d4ba817a649f3041b163f76e5d829429e7`.
- Exact provider patch inputs: `0170`, `0172`, and `0173` in
  [`patches/series`](../../patches/series).
- The latest provider profile was Buildbox-validated separately; this audit
  creates no kernel build and no boot candidate.
- Read-only board-contract evidence:
  [`da921x-i2c6-a72.md`](../../docs/hardware/da921x-i2c6-a72.md) and the linked
  identification lifecycle records.
- A72 prestate model: patch `0164`, with values carried into the dormant C
  ledger rather than a hardware access interface.

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
- No bounded inverse exists for a provider write at or beyond the unresolved
  external-isolation boundary. The release callback therefore remains a
  structured `-EOPNOTSUPP` refusal.

The machine-readable ledger and oracle passed with all six ownership/write
requirements unresolved:

```text
page_encoding=unproven
page_owner=unproven
write_transport=unproven
control_mask=unproven
post_settle_readback=unproven
rollback_owner=unproven
decision=BLOCK_WRITABLE_PROVIDER
hardware_action=none
```

## Analysis

The observed `0x80` and `0x46` values are useful prestate evidence, but they
are not an API contract. The direct-address read path cannot be promoted into
a page-selector or register-data write merely because the values recur in a
natural vendor cycle. A future provider must establish one owner for page
selection and one owner for the rail mutation, serialize them with the
existing I2C6/resource owners, read back the complete affected state after the
settle interval, and release only with a same-generation handle. If any
post-state differs, it must retain/fault rather than guess an inverse.

This negative result is progress: it rules out the tempting but unsafe next
patch and narrows the next evidence request to the exact six missing rows.

## Conclusion

`rejected` for the hypothesis that the current source and evidence authorize a
writable BUCKB provider. The existing resource-only provider and paired
acquire/release refusal boundary remain the correct implementation boundary.

## Follow-up

The next source-only action is to resolve page ownership from an attributable
vendor-source/binary contract or a separately designed read-only observation
that distinguishes page state from the `0x69` client address. Only after that
review closes may a default-off bounded write be designed. It must still pass
Buildbox from a clean pushed commit before any device consideration, and the
P24/P28/P30/P32/A26/A14 gates remain independent blockers.
