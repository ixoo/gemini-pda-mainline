# Experiment: observe exact READY plan values

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-plan-value-diagnostic` |
| Status | `complete` |
| Subsystem | arm64 late-CPU plan value diagnostics |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact predicate observer proves that the live plan differs from profile
expectations for early, target, required, and per-target local capability
bitmaps, and that the collected SMCCC conduit differs from the assumed SMC
value. Which exact bitmap values and conduit enum did the production producers
publish?

The value-observer hypothesis is falsifiable: an otherwise identical candidate
must preserve the validator return and original predicate line while emitting
exactly one `A72_READY_PLAN_VALUES_V1` line on the same failure. That line must
contain `ARM64_NCAPS`, the three global bitmaps, both per-target local bitmaps,
and both target policy conduits in that documented positional order. It must
not change READY, CPU, power, storage, retry, CPU_OFF, or CPU9 behavior.

## Provenance and environment

- Parent repository commit: `285f53a5...`.
- Parent kernel series: canonical Linux 7.1.3 through patch `0438`.
- Parent prepared source state: `a5a27faa...`.
- Parent `mt6797_psci.c` SHA-256: `a850c6b5...`.
- Runtime parent candidate: exact boot2 SHA-256 `7ac6f429...`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The patch changes only the existing failure-only validator wrapper. It keeps
the original contract call and returns its result unchanged. When that result
is nonzero and the plan pointer is valid, it prints immutable in-memory plan
bitmaps and two one-byte policy enum values. It adds no CPU operation,
device-tree change, hardware read or write, retained-RAM write, storage access,
retry, CPU_OFF, reboot, or firmware call. CPU9 remains vetoed. The candidate
must never receive the CPU8 trigger.

## Procedure

1. Generate and replay one format-patch from exact post-`0438` Buildbox source.
2. Reject mutations that change the validator return, success guard, null
   guard, exact value fields, profile callback, or add a CPU action.
3. Admit the patch canonically and build default plus exact live profiles only
   on Buildbox.
4. Recompose the unchanged serviceability/provenance DT and ramdisk, validate
   the container independently, and deploy exact boot2.
5. Capture one complete read-only frame and exactly one value line; do not send
   a trigger.

## Observations

Buildbox generated exactly one format-patch from prepared source state
`a5a27faa...` and integrity `f1b7972a...`. The parent and final
`mt6797_psci.c` hashes are `a850c6b5...` and `08f3be5c...`; generated patch
`0439` is `570f4d92...`. Strict checkpatch, deterministic replay, exact field
coverage, return-owner validation, and all seven unsafe source mutations pass.
The generation performed no native VM build or device action and explicitly
marks its output `boot_candidate=false`. See
[`results/buildbox-generation-20260830.txt`](results/buildbox-generation-20260830.txt).

Canonical patch `0439` was admitted at repository commit `e33dfbce...` and
both the default and exact live profiles passed on Buildbox. The exact profile
package was fetched and recomposed twice with the unchanged serviceability DT
and ramdisk. Both DTs and both boot containers are byte-identical. Independent
validation passes all 32 LK gates, rejects ten DT mutations and six container
mutations, and confirms zero CPU requests. The exact padded boot2 candidate is
`1c08f1fc...`; it is an observation-only boot candidate and must not receive
the CPU8 trigger. See
[`results/offline-candidate-20260830.txt`](results/offline-candidate-20260830.txt).

The guarded installer then resolved inactive logical `boot2` from the live GPT
as `/dev/mmcblk0p30`, required the exact `7ac6f429...` predecessor, wrote and
flushed `1c08f1fc...`, obtained the same full-partition readback identity, and
shut the device down. It created no fresh partition backup and did not reboot.
See
[`results/deployment-boot2-1c08f1fc-20260830.txt`](results/deployment-boot2-1c08f1fc-20260830.txt).

One exact read-only boot produced exactly one predicate line and one value
line at boot ID `ec5f3d02...`. CPU0--7 remained online, CPU8--9 remained
offline, and the controller stayed armed with zero triggers, CPU requests,
CPU_OFF requests, retries, or storage writes. The five bitmaps decode against
the exact 125-entry post-`0439` arm64 capability table as follows: the early
set is AMU, HW DBM, and `WORKAROUND_845719`; each A72 target is AMU, HW DBM,
Spectre v2/v4/BHB, `WORKAROUND_1742098`, and
`WORKAROUND_SPECULATIVE_AT`; the required set is those five target-only
mitigation capabilities. Both target policy conduits are enum `1`, which the
same source defines as `ARM64_LATE_CPU_SMCCC_NONE`. See
[`results/runtime-attempt-1-value-frame-20260830.txt`](results/runtime-attempt-1-value-frame-20260830.txt).

These outputs are internally consistent with the production producers and
both targets agree byte-for-byte. The defect is therefore in the profile's
hard-coded validator: its early set omits `WORKAROUND_845719`, its target and
required sets falsely include `MISMATCHED_CACHE_TYPE`, and its production
policy predicate expects SMC despite the live producer reporting NONE. The
expected-pair effects path already models vulnerable/no-firmware v2/v4/BHB
effects and accepts a valid NONE policy, so no producer or effect relaxation is
needed.

## Conclusion

`complete-stale-profile-expectations-localized`.

## Follow-up

Repair only the three localized production expectations, then require a silent
diagnostic and exact no-blocker READY frame before any CPU8 trigger. Keep CPU9
vetoed.
