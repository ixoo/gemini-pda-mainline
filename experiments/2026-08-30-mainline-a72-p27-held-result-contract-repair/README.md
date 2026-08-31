# Experiment: accept the held P27 acquire result

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-p27-held-result-contract-repair` |
| Status | `patch generated and admitted; focused Buildbox validation pending` |
| Subsystem | MT6797 CPU8 binder and platform-effect owner contract |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact P27 runtime attempt returned a complete successful physical acquire
with `p27_owned=1` and `sealed=0`, but the binder rejected it with `-EPROTO`.
Does matching the binder's acquire-result seal expectation to the platform
owner's intentional held state allow membership P27 completion without
weakening release or later-stage validation?

## Provenance and environment

- Parent: canonical Linux 7.1.3 series through patch `0449`.
- Parent source state: `7c82a444be80afc47304f2b620e49c7853600770bc2409d0d715bbcbc44b105c`.
- Parent integrity: `c76cb7d15244a1891f5e2d144ce92a4c30909e716e3fa746e82edc0d3ff80260`.
- Build and patch generation backend: Buildbox only.
- Runtime source: the single-trigger result in the preceding
  [P27 attribution experiment](../2026-08-30-mainline-a72-p27-runtime-attribution/README.md).

## Safety assessment

The repair changes only a binder validation predicate and its KUnit fake. A
successful P27 acquire must be unsealed because ownership remains held for the
provider, isolation, SRAM, CPU_ON, and DCM stages; a release must remain sealed.
The patch adds no hardware operation, CPU request, CPU9 path, CPU_OFF path,
retry, retained-RAM write, storage access, timing change, or device action.

No device candidate may be constructed until deterministic replay, strict
style review, focused KUnit, and the production profile build all pass. CPU9
remains vetoed until CPU8 is reproducibly online.

## Associated code

- `scripts/source_edits.py` performs the two exact source edits.
- `scripts/generate_patch.py` creates and replays canonical patch `0450` from
  the pinned managed source.
- `scripts/generate-on-buildbox` enforces the clean Git-pinned Buildbox lane.

These scripts require no device access. The generator writes only a temporary
Git tree and a checksum-covered patch-review package on Buildbox.

## Procedure

1. Generate one normal format-patch from the exact post-`0449` source.
2. Require the binder result-shape helper to compare an explicit expected seal
   state: false only for P27 acquire and true for release, isolation, and DCM.
3. Make the KUnit P27 fake reproduce the production held-owner contract and
   preserve the malformed sealed-acquire rejection.
4. Replay the patch deterministically and reject any hardware/request call-count
   change or forbidden path.
5. Admit the patch canonically, run focused binder/transition KUnit on Buildbox,
   then build the production live-trigger profile on Buildbox.

## Observations

- Buildbox generated exactly one patch from the checksum-pinned post-`0449`
  source, and deterministic replay reproduced it.
- The patch changes no physical-effect or CPU-request call count and adds no
  CPU9, CPU_OFF, retry, retained-RAM, storage, or device path.
- Strict Checkpatch reported zero warnings and zero checks. Its sole error is
  the intentionally absent DCO sign-off on the synthetic experiment author;
  this internal archive is not submission-ready.
- The exact generated patch SHA-256 is
  `bb050d483a31f79214e0fb7abd49408770a69998fdb771f9074c9da487e38fbc`.

## Analysis

The runtime's complete `0x7` acquire mask and `error=0` exclude a physical P27
failure. Production source intentionally leaves `sealed=false` while the owner
is `P27_HELD`; only failure and release paths seal the result. The current test
fake instead returns `sealed=true` for success, so its green success path does
not model the production contract.

## Conclusion

Patch generation and deterministic replay pass. Focused KUnit and the
production-profile Buildbox build remain required before any candidate exists.

## Follow-up

If the offline proof passes, construct one successor boot2 candidate whose
unique result distinguishes provider, isolation, SRAM, PSCI CPU_ON, secondary
execution, and membership publication. Do not prepare CPU9 until CPU8 is
reproducibly online.
