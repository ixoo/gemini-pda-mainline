# Experiment: MT6797 thermal-ledger live-model repair

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-thermal-ledger-live-model-repair` |
| Status | patch defined; hardware-free and Buildbox validation pending |
| Subsystem | optional thermal-stage ledger admission |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-04 |
| Tracking goal | remove the proven pre-transaction blocker to thermal observability before CPU8/CPU9 load |

## Question or hypothesis

Changing only the optional ledger's root-model predicate from the pre-LK DT
string to the established live `MT6797X` identity will let the exact thermal
probe advance past ledger admission without broadening its device, compatible,
ramoops, address, size, reset, thermal, or zone gates.

## Provenance and environment

- Runtime frame:
  `969735f26636c12fb06eb96f2f484f2eb6dfb02f2e7369f2d5501630e88fa364`.
- Mainline boot: `3e6d06e4-b89f-4db5-b292-c5df56dc6372`.
- Exact failing release: `7.1.3-gemini-mt6797-thermal-stage-ledger`.
- Exact installed payload:
  `ca3c25889b92673aa341fa97fc347c3469bc3b532d81045659a3afa1f563636a`.
- Canonical parent ledger patch:
  `patches/v7.1.3/0521-pstore-add-Gemini-MT6797-thermal-stage-ledger.patch`.
- Successor patch:
  `patches/v7.1.3/0524-pstore-match-Gemini-thermal-ledger-after-LK-model-rewrite.patch`.

## Safety assessment

The source change performs no new read or hardware action. It changes one
string predicate only. The ledger remains default-off, empty-only, bounded,
CRC-valid, two-copy, single-attempt, and terminal-sealing. All existing DT,
ramoops, address, size, thermal reset, node status, and zone-shape gates remain.
The hardware-free test and Buildbox build perform no device action. A successor
device attempt remains separately gated and must preserve the exact live-proven
USB/console/PWRAP/eMMC DT.

## Associated code

- `scripts/generate_patch.py` reconstructs the exact ledger source from pinned
  patch `0521`, performs the one edit in a temporary Git repository, and
  reproduces patch `0524` byte-for-byte.
- `scripts/validate_patch.py` checks exact generation, one-file/one-string
  scope, source evidence, canonical ordering, and rejection mutations.

## Procedure

1. Pin the exact decision-bearing runtime evidence and parent patch.
2. Reconstruct the parent ledger source and generate the one-predicate patch.
3. Require byte-identical reproduction, exact one-file scope, strict patch
   review, canonical-series invariants, and rejecting mutations.
4. Commit and push the exact change, then build the production thermal-stage
   profile on Buildbox and run its focused no-network KUnit suite.
5. Only after those gates pass, construct a successor from the same exact
   runtime-proven DT/initramfs, publish its identity, install inactive `boot2`,
   and make one fresh read-only thermal observation.

## Observations

The preceding live frame proves the kernel, USB/netcat, PWRAP/MT6351, eMMC,
console, calibration-provider, and CPU0--7 baselines. It also proves live model
`MT6797X`, thermal retry after provider bind, errno 19, no thermal driver, and
zero zones. Exact source places the failure at `gemini_mt6797_thermal_ledger_begin()`
before calibration and all thermal transaction operations.

## Analysis

The new predicate is not a guess: `MT6797X` is the bootloader-published live
identity already used by the established Gemini A72 ledgers. Retaining every
other gate prevents the diagnostic record from becoming generally active. A
successor live frame can therefore test the previously unexecuted calibration
and thermal transaction; it must not be interpreted as CPU8/CPU9 support until
temperature observation itself passes.

## Conclusion

The exact repair is defined but not yet admitted. No build or device action is
claimed by this experiment yet.

## Follow-up

The ordered Buildbox, candidate, and runtime gates are owned by
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
