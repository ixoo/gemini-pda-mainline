# Experiment: A41 expected-A72 static capability census

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a41-static-census` |
| Status | `completed` (offline source-contract validation only) |
| Subsystem | arm64 capability finalization and MT6797 late Cortex-A72 profile |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, A41 |

## Question or hypothesis

Can the ABI 3 profile classify every source/profile-static row in the exact
40-descriptor expected-A72 census while leaving exactly six target-dependent
rows unresolved and keeping every plan publication, capability mutation, and
CPU8/CPU9 path unreachable?

This is a provisional expected-model census. It is not observed CPU8/CPU9
hardware evidence and cannot close the capability-inventory blocker.

## Provenance and environment

- Kernel release: Linux 7.1.3, official archive SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Patch 0152 source parent: commit
  `9257e46ea3fd8da4766cfd0dba4b15af56cf0d6a`, tree
  `30c9cf493dda6501620e0713e657184566e5f339`.
- Patch 0152 source commit:
  `63e5d894150a5d5d1d897a639199a096815bb385`, tree
  `c3db9d87cf885b6e2313041e1e3b8b28ea8e98c1`, diff SHA-256
  `ab27efd5d334ac4fd18a41371db6efaf7d07bf5ead2df9991d612ba5ddcaf4c0`.
- Format-patch:
  [0152](../../patches/v7.1.3/0152-arm64-classify-static-MT6797-late-CPU-capabilities.patch),
  SHA-256
  `61ff3351799c9313d89b4ab572f6511371e04f6c6f3625b3d730ad7d77b9abbf`.
  It uses a synthetic, non-certifying experiment author, has no
  `Signed-off-by`, and is not submission-ready.
- Selected series:
  [`patches/series-a72-reject-gate-a41-static-census`](../../patches/series-a72-reject-gate-a41-static-census),
  94 entries, SHA-256
  `12b46a348af31ebbe506480716e2bb517044da095e5902b8bfb59622188e859f`.
- Ordered patchset identity:
  `c06e83ea4491a28c18a5db9563497413984e578c9bdbb2ce6f3da35e2e115352`.
- Externally computed selected source-state identity:
  `f073150a6bbfb6af1d4262f4b754534118181ee40284d60a59aa1068740d118d`.
- In-source non-circular parent identity:
  `bf192fa874aea9838cece3f58eec0bba2a18dc43bfe094ad9f6d635b9809ca32`.
  It identifies the exact patch-0151 selected source state, not patch 0152 or
  a running image.
- Selected manifest profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41-static-census`.
- Ordered configuration-input identity:
  `6fa24adaa512d804172b170b205f574b4d461b4263bc0d374c6499f78b7f3d7c`.
  It is not a resolved or running `.config` identity.
- Build/compiler: not invoked; no compile claim is made.
- Boot path and target partition: none.

## Safety assessment

The work was read-only with respect to hardware. No kernel build, package,
boot image, partition write, CPU request, firmware call, or device connection
was made. The inherited `maxcpus=8` policy and patch-0092 `.cpu_boot =
-EAGAIN` and `.cpu_can_disable = false` vetoes remain unchanged.

The owner reported a boot2-to-Gemian cycle during this source-only work. It is
recorded as unattributed recovery chronology in the parent experiment and is
not evidence for this patch or for A72 behavior.

## Associated code

- Patch 0152 and its selected series/profile above.
- [Design](DESIGN.md).
- [Static census](results/static-census.tsv).
- [Implementation markers](results/implementation.tsv).
- [Kernel static review](results/kernel-static-review-20260805.txt).
- `scripts/validate.py` and `scripts/test_mutations.py`; both are offline and
  require no privilege.

## Procedure

1. Start from exact source commit `9257e46e…` and inspect all 40 compiled local
   descriptors from the prior census.
2. Add source-owned pure classifiers for private feature and erratum matchers;
   never call a target matcher on the executing A53.
3. Classify only the expected Cortex-A72 model, rejecting a populated
   hypervisor target-implementation override and non-default KPTI state.
4. Validate the exact compiled, classified, present, required, conflicting,
   and effect bitmaps, the embedded identities and blockers, and the absence
   of observed/method evidence.
5. Require the validator and profile preparation to return `-EAGAIN`, and
   verify that identity publication and architecture mutation remain absent.
6. Run strict static, repository, patch-application, and adversarial mutation
   checks. Do not build or access the device.

## Observations

- Exact census: 40 compiled local descriptors, 34 provisionally classified.
- PRESENT: slots `9`, `66`, `94`, and `121`.
- ABSENT: 30 rows listed in the machine-readable census.
- UNRESOLVED: slots `33`, `36`, `69`, `79`, `81`, and `82`.
- Only compat-AES clearing and speculative-AT finalization appear in the
  provisional effect draft. Dynamic CTR/Spectre/BHB effects remain empty.
- The partial validator accepts that exact expected-only draft and returns
  `-EAGAIN`; `local_caps_planned` and every plan-identity word remain zero.
- KPTI uses the actual source-owned safe list and requires
  `__kpti_forced == 0`; BBML2 uses its actual source-owned allowlist. MIDR
  classification returns unresolved when the architecture target-implementation
  override is active.
- Strict checkpatch on the source diff reports 0 errors, 0 warnings, and 0
  checks. The archived format-patch reports only the intentionally missing
  `Signed-off-by` error.

Exact validation counts and tool versions are frozen in the offline and
mutation transcripts after the scripts in this directory.

## Analysis

The hypothesis is confirmed only for the blocked provisional census. The core
now distinguishes all source-static expected-A72 outcomes from the six rows
that actually need register, GIC/hyp, cache, and firmware evidence. Unknown
slots, changed matcher semantics, target-implementation substitution, KPTI
policy drift, missing identities, removed blockers, populated method evidence,
and bitmap/effect drift all remain fail-closed.

This does not prove the two physical targets are Cortex-A72. A future complete
plan must require separate valid observed MIDRs for CPU8 and CPU9, the exact
resolved/running configuration and image identity, and complete evidence for
the six unresolved rows before it may compute a plan identity.

## Conclusion

Confirmed for Linux 7.1.3 source commit `63e5d894…`: the exact expected-A72
static census is implemented as `PARTIAL_STATIC_CAPABILITY_CENSUS`. A41 is
incomplete; PLAN_FROZEN, COMMITTED, READY, build, boot candidate, device
action, and hardware-support claims remain unauthorized.

## Roadmap boundary

[The roadmap](../../docs/ROADMAP.md) remains the sole owner of ordered next
steps and exit criteria. No unchanged device boot can close the source and
evidence gaps recorded here.
