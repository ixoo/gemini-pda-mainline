# Mainline MT6797 A72 serialized platform-effect owner

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-27-mainline-a72-platform-effect-owner` |
| Status | first compile exposed an enum/macro collision; namespaced-state regeneration pending |
| Subsystem | MT6797 CPU8 P27, external isolation, PWRAP, and MP2 DCM |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-27 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, CPU8 physical binding |

## Question or hypothesis

Can the existing read-only platform-state source safely grow one serialized,
attempt-bound effect transaction for P27 acquire/release, external-isolation
clear, and post-online DCM without splitting resource ownership or connecting a
production CPU8 caller?

## Provenance and environment

- Parent repository commit: `67b3225f2e5105f4d5e71ae1b8fd61afb5de9c61`.
- Canonical parent series: 389 patches through `0389`.
- Patch-generation repository commit: `f0d504fc48928a36740c3c584f5576471a7f9e24`.
- Prepared-source state: `ac9c2a550c465d56500045017afd7110e0ffb545538ac9ddda1c0d0d56a5853b`.
- Build backend: Buildbox only.
- Boot path and target partition: none in this phase.

## Safety assessment

Patch generation, compilation, and QEMU use no device. The production effects
are behind a new default-off option and have no caller. The focused KUnit suite
uses injected memory and records calls instead of invoking the physical SPM,
PWRAP, MCUCFG, delay, provider, watchdog, pstore, SMC, or CPU paths. No boot
image or candidate is selected.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the ownership, exact word transitions,
  one-shot state, inverse boundary, and proof contract.
- `templates/` contains the production snippets and injected KUnit suite used
  for deterministic patch generation.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the production
  and test changes to the exact prepared source.
- [`scripts/validate_source.py`](scripts/validate_source.py) rejects ownership,
  order, one-shot, caller, and hardware-free-test drift.
- [`scripts/generate-patches.py`](scripts/generate-patches.py) creates, checks,
  and replays two normal format patches.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) pins the exact
  managed source state and bounded output package.
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) accepts only the exact
  pushed Buildbox package and one no-network suite.
- [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires the eight
  named cases, exact totals, and post-test rootfs panic boundary.

## Patch-generation result

Buildbox generated and replayed the two exact patches from the pinned prepared
source. Strict Checkpatch passed both patches with zero errors, warnings, or
checks. Production and test source validation passed with one serialized
platform-state resource owner, eight focused KUnit cases, zero production
callers, zero physical-effect calls, and no device action or boot candidate.
The generated format patches retain the experiment's synthetic archive
identity, contain no synthetic `Signed-off-by`, and are not submission-ready;
an upstream submission must identify the actual author and truthful DCO signer.

- `0390-soc-mediatek-add-serialized-A72-platform-effects.patch`:
  `76011b229fc61ba770520acf1ce3d7bbe0442768152081ae6edcb43d7f731cec`
- `0391-soc-mediatek-test-serialized-A72-platform-effects.patch`:
  `ca29af1b0e889ce652d3cb482eea547115de4ae06ee2c9556ef773b20124edfb`
- Exact generation chronology and machine-readable provenance:
  [`results/patch-generation-f0d504fc.txt`](results/patch-generation-f0d504fc.txt).

The first exact compile at repository commit `870c83b0` rejected the production
and KUnit objects because the P27-held register-value macro and one owner-state
enumerator had the same preprocessor name. The later undeclared-state messages
were cascading diagnostics. The remediation namespaces every owner state as
`MT6797_A72_EFFECT_STATE_*` and makes the validator reject recurrence. See
[`results/build-attempt-870c83b0.txt`](results/build-attempt-870c83b0.txt).

## Planned procedure

1. Generate one production-owner patch and one injected-test patch from the
   exact through-`0389` prepared source. **Complete.**
2. Require strict Checkpatch, production/test validation, exact replay, and
   package checksum validation before admission. **Complete.**
3. Admit the two exact patches and one focused configuration profile.
   **Complete.**
4. Build the exact clean pushed commit on Buildbox.
5. Run the sole eight-case suite in bounded no-network arm64 QEMU.
6. Publish sanitized evidence before beginning the BigiDVFS SRAM-LDO owner.

No result in this experiment establishes an MT6797 hardware effect until a
later complete binder and decision-bearing device candidate cross their own
gates.
