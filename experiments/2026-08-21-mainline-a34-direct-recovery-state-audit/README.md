# Experiment: mainline A34 direct recovery-state audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-a34-direct-recovery-state-audit` |
| Status | completed offline audit; complete current-mainline attestation absent |
| Subsystem | MT6797 A72 A34 recovery-state ownership |
| Device variant | Planet Gemini PDA named development unit |
| Date | 2026-08-21 America/New_York |
| Tracking issue | Roadmap Gate 7, production A34 owner |

## Question

Can exact current mainline prove every reset-dependent A34 prefix directly,
without classifying the reset that preceded Linux?

The required proof is stronger than a collection of plausible values. Every
field must have an exact reference, a fresh read through its real owner, a
bounded failure mode, and serialization against every writer until the
observation is consumed. The proof must also include the generic CPU and Linux
owner state and the already-audited secure replay initialization contract.

## Provenance and safety

- Repository input: signed and pushed commit
  `7a955db19d90450f4243a0334ea82ff3736af17e`.
- Canonical full-series source state:
  `905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e`.
- Canonical patchset:
  `1916a4a627d7d0d9512a1387557001e6ca3556750c57a1f17e0bb0771d984c09`.
- The exact prepared Linux 7.1.3 tree was inspected read-only on Buildbox.
  No source tree was copied to or from it.
- The exact historical first natural CPU8 cycle is pinned by SHA-256
  `6db6ea41ba4689541cb504a0486c0a1b7249834ebdb8613f0e73b0bf56e808f5`.

This audit performed no build, device contact, SMC, MMIO access, I2C transfer,
partition access, boot2 write, reboot, or CPU request. It does not authorize a
boot or A34 publication.

Exact source hashes and bounded facts are in
[`results/provenance-20260821.txt`](results/provenance-20260821.txt). The
field-by-field decision is in
[`results/state-matrix.tsv`](results/state-matrix.tsv).

## Observations

The historical identity-gated Gemian observer provides a valuable reference,
not current-mainline authority. Immediately before the first natural CPU8
transition and again after its natural off path, it recorded the same:

- DA921x page `0x80`, Buck B disabled, selector `0x46`;
- SPM offsets `0x180`, `0x184`, `0x188`, `0x18c`, `0x218`, and `0x290` as
  `0x2a00005c`, `0x2a00004c`, `0x00350c08`, `0x00350cff`, `0x00010132`, and
  `0x00000002`;
- all twelve fixed secure-register words as zero with a stable sentinel;
- protected B/CCI clock observation `pll_con1=0xc1130000`,
  `muxsel=0x00000054`, and `ckdiv=0x00042168`; and
- MP2 DCM as zero.

That before/after identity shows a complete direct-state approach is worth
pursuing. It does not make the old record an immutable input to a later boot.

The exact current source has only partial pieces:

- The DA921x positive provider owns a root-adapter-locked five-byte snapshot
  and exact initial-state predicate, but the read-only snapshot function is
  private to the mutating acquire transaction. The earlier preflight is a
  one-shot stored diagnostic, not an exported fresh A34 source.
- `mt6797-a72-power.c` samples two SPM words, MP2 DCM, and one PLL word only at
  probe. It stores those values without a refresh or generation and reports
  only that the PWRAP reset was acquired, not its state. The Gemini DTS deletes
  this node entirely.
- The watchdog reset controller serializes `WDT_SWSYSRST` changes but has no
  reset-status operation or typed snapshot for bit 11.
- The bounded MCUMIXED/CSPM and secure BigiDVFS readback transports exist, but
  both DT nodes are disabled. Their target runtime is unvalidated for this
  A34 use, and neither is composed with the A72 owner.
- MT6797 has no current CCI node or owner-safe A72-port state getter. The
  protected clock reader's CCI frequency is not CCI snoop/DVM membership.
- The current A34 structure carries caller-supplied generic CPU and Linux
  owner state but no hardware tuple and has no production collector. It also
  still requires a reset-provenance enum, so it cannot express direct-state
  authority.

## Analysis

There is no positive direct-state row in the current canonical tree. The old
A36 prestate is explicitly caller-supplied and its constants are not hardware
observations. The current A72 observer is stale and incomplete even if its
deleted DT node were restored. Enabling the two protected backends would still
leave CCI coherency, per-core physical state, PWRAP reset state, fresh DA921x
export, current-boot secure replay applicability, and cross-owner atomicity
unproved.

The negative result is narrower than the failed reset classifier. Exact prior
runtime evidence already supplies a coherent reference tuple, and canonical
mainline contains reusable owner-local read mechanisms for several fields.
The missing work is to define and implement owner-safe current observations,
not to infer state from reset cause.

The first missing ownership boundary is the platform-local raw state source:
exact SPM physical status/control, TOPRGU PWRAP reset, MP2 DCM, and A72 CCI
port state. CCI is the least specified member and must be source-audited before
any new mapping. The authoritative implementation order remains only in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).

## Conclusion

`confirmed`: the exact historical first CPU8 cycle returned the named direct
hardware tuple to its identical pre-attempt values.

`confirmed`: current mainline contains bounded partial readers for DA921x,
protected clock state, and secure BigiDVFS state.

`rejected`: the old A36 constants, the probe-time A72 snapshot, or simply
enabling the protected backends as a complete A34 attestation.

`missing`: fresh owner-safe PWRAP, SPM physical, per-core, DCM, CCI, DA921x,
secure/current-boot, generic/Linux-owner composition and one atomic immutable
publication.

A34, the production lifecycle opener, CPU8 request, boot candidate, and device
attempt remain closed.

## Validation

Run from the repository root:

```sh
python3 experiments/2026-08-21-mainline-a34-direct-recovery-state-audit/scripts/validate.py
```
