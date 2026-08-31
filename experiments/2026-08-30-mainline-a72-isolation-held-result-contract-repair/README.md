# Experiment: accept the held isolation result

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-isolation-held-result-contract-repair` |
| Status | `exact candidate installed and fully read back; device shut down for selected boot2 run` |
| Subsystem | MT6797 CPU8 binder and platform-effect owner contract |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact repaired-P27 runtime crossed P27 and provider acquisition, then
returned `-EPROTO` at isolation while retaining both owners. Does matching the
binder's isolation-result seal expectation to the production owner's
intentional open `ISOLATED` state allow the transition to reach SRAM without
weakening release or final DCM validation?

## Provenance and environment

- Parent: canonical Linux 7.1.3 series through patch `0450`.
- Parent source state: `34ade30031aa46d49fb7411594d95b8ec2e4931fccff112f0d4904977f68e2ba`.
- Parent integrity: `db70aea751c7cce86930d81dab01503c8b79f5a29d75d4bba060be7b2451837d`.
- Build and patch generation backend: Buildbox only.
- Runtime source: the single-trigger result in the preceding
  [P27 held-result repair](../2026-08-30-mainline-a72-p27-held-result-contract-repair/README.md).

## Safety assessment

The proposed repair changes one binder validation argument and one KUnit fake.
A successful isolation operation remains unsealed because P27 and provider
ownership continue through SRAM, CPU_ON, and DCM; release and final DCM
completion remain sealed. The change adds no hardware operation, CPU request,
CPU9 path, CPU_OFF path, retry, retained-RAM write, storage access, timing
change, or device action.

No device candidate may be constructed until deterministic replay, strict
style review, focused KUnit, and the production profile build all pass. CPU9
remains vetoed until CPU8 is reproducibly online.

## Associated code

- `scripts/source_edits.py` performs the two exact source edits.
- `scripts/generate_patch.py` creates and replays canonical patch `0451` from
  the pinned managed source.
- `scripts/generate-on-buildbox` enforces the clean Git-pinned Buildbox lane.

These scripts require no device access. The generator writes only a temporary
Git tree and a checksum-covered patch-review package on Buildbox.

## Procedure

1. Generate one normal format-patch from the exact post-`0450` source.
2. Require the binder result-shape helper to expect an unsealed successful
   isolation result while preserving unsealed P27 acquire and sealed P27
   release and DCM completion.
3. Make the KUnit isolation fake reproduce the production held-owner contract
   and preserve rejection of a malformed sealed result.
4. Replay the patch deterministically and reject any hardware/request call-count
   change or forbidden path.
5. Admit the patch canonically, run focused binder/transition KUnit on Buildbox,
   then build the production live-trigger profile on Buildbox.

## Observations

- The prior runtime returned exactly `-EPROTO` at transition stage 4 with P27
  and provider ownership retained, one CPU8 request, and no CPU9, CPU_OFF,
  retry, or reboot request.
- Production isolation completes its isolation clear, PWRAP deassertion, and
  guard delay, enters `ISOLATED`, and returns success without setting
  `sealed=true`.
- The binder currently requires sealed isolation success, and the KUnit fake
  currently returns sealed success. The test model therefore disagrees with
  the production result at the exact runtime failure boundary.
- Buildbox generated exactly one patch from the checksum-pinned post-`0450`
  source, and deterministic replay reproduced it.
- The patch changes no physical-effect or CPU-request call count and adds no
  CPU9, CPU_OFF, retry, retained-RAM, storage, or device path.
- Strict Checkpatch reported zero warnings and zero checks. Its sole error is
  the intentionally absent DCO sign-off on the synthetic experiment author;
  this internal archive is not submission-ready.
- The exact generated patch SHA-256 is
  `248dd2271daedc8a106ea4bea628108d99da143be8bdbbfb9aacb815af3154da`.
- The focused Buildbox/QEMU run passes all 48 P24-owner, transition-executor,
  and binder cases with zero physical CPU requests, CPU_OFF requests, retries,
  or network access.
- The production Buildbox package is pinned to commit `62557cd2...`, patchset
  `39dfc426...`, and kernel release `7.1.3-gemini-a72-admission-live`.
- Two independent serviceability/provenance DT compositions are byte-identical
  at `57fb4aae...`; two independent Android-v0 containers and two independent
  16 MiB padding constructions are byte-identical.
- Independent validation accepts exact padded candidate `510cb652...`, all 32
  LK gates pass, and six container mutations are rejected. The image contains
  one CPU8 request route and no CPU9, CPU_OFF, or retry route.
- Live GPT resolved inactive, unmounted 16 MiB `boot2` with exact predecessor
  `fbe0bf76...`; power was stable and the retained generation-8 isolation
  predecessor record passed exact validation.
- Exact padded image `510cb652...` was written, synced and flushed, and its
  full-partition readback matched. The device then shut down cleanly and TCP/22
  remained closed for three consecutive checks. No fresh backup or automatic
  reboot was performed.

## Analysis

The terminal stage and errno localize the rejection to the binder's isolation
callback. The production owner and KUnit fake have opposite successful seal
states, while every other binder-validated isolation field is produced by the
same successful production path. The seal predicate is therefore the narrow
source-level explanation to test. SRAM and later stages remain unobserved and
must not be inferred from this result.

## Conclusion

All offline and deployment gates pass and exact changed candidate `510cb652...`
is installed on `boot2`. This remains a runtime candidate, not CPU8
hardware-support evidence: only its single boot-bound trigger can distinguish a
new transition stage or CPU8 online state.

## Follow-up

Physically select `boot2`. Accept only the exact pristine baseline, then issue
one boot-bound trigger and classify its exact transition stage, terminal state,
retained ownership, and live CPU list. Do not repeat either predecessor image
or prepare CPU9 until CPU8 is reproducibly online.
