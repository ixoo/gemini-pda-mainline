# A41 immutable-plan boundary design

## Scope

Patch 0151 replaces the ABI 2 mixed attestation with an ABI 3 transaction
boundary. It defines what a complete future evaluator and infallible
architecture commit must exchange. It does not implement either success
path.

The design keeps these independent:

1. fallible target and system evidence;
2. a core-normalized, state-free immutable plan;
3. an architecture-owned monotonic receipt;
4. a copied READY token for later admission consumers.

Profile callbacks may collect and verify evidence. They do not own capability
mutation or receipt state.

## Exact evaluator input

The selected expected profile yields 40 compiled local descriptors. The
source audit freezes the following partition:

| Class | Count | Slots |
| --- | ---: | --- |
| Source/profile-static PRESENT | 4 | 9, 66, 94, 121 |
| Source/profile-static ABSENT | 30 | See `results/capability-census.tsv` |
| Evidence-dependent | 6 | 33, 36, 69, 79, 81, 82 |

This census is input to a future evaluator, not implemented or runtime state.
ABI 3 therefore makes the current MT6797 classifier return UNRESOLVED for
every descriptor and makes profile validation return `-EAGAIN`.

AMU and hardware dirty-bit management are target-present but also
early-present. Erratum 1742098 and speculative-AT are the two statically
known newly required rows. The four dynamic rows with typed mutation effects
are CTR mismatch, Spectre-v2, Spectre-v4, and BHB.

## Evidence schema

Each target has a plain, field-wise AArch64 and AArch32 register image plus
separate cache, interrupt, virtualization, firmware, ASID, granule, and
active-VA evidence. Validity masks make absence of evidence distinct from a
zero architectural value.

Capability state and method choice are separate:

- Spectre-v2 state uses CSV2 and WA1; its usable mitigation also needs the
  conduit and callback.
- Spectre-v4 state uses SSBS and WA2; its effect needs method, conduit, and
  policy.
- BHB state is absent only for CSV2.3 on this A72. ClearBHB, ECBHB, WA3,
  conduit, Spectre-v2 state, vector template, and policy select the method.
- CTR mismatch needs both raw and Linux-effective CTR plus the finalized
  system value and strict mask.
- GICv5 legacy and ICH_HCR_EL2.TDIR are compatibility validations, not
  invented enable actions.

## Plan and typed effects

The immutable plan owns canonical, compiled, classified, early, target,
required, and conflicting capability bitmaps. It also owns expected native
and compat HWCAPs and typed effects for:

- CTR mismatch and user CTR trapping;
- Spectre-v2 state, conduit, callback, hyp vector, and alternative;
- Spectre-v4 state, method, conduit, policy, and firmware alternative;
- BHB state, method, loop count, system method, vector, alternative, and
  Spectre-v2 dependency;
- compat AES suppression;
- speculative-AT finalization.

The plan carries no lifecycle state. Its identity must eventually be computed
by canonical field-wise serialization; ABI 3 intentionally has no identity
writer.

## Receipt and publication

The receipt is separate `__ro_after_init` architecture-owned state. A future
commit must copy the plan identity and exact typed effects into it only after
all infallible mutations complete. Verification callbacks receive the plan
and receipt as const inputs.

The current transaction order is:

`REGISTERED -> BLOCKED`, or, only after future closure,
`REGISTERED -> PLAN_FROZEN -> COMMITTED -> SYSTEM_VERIFIED -> READY`.

Preparation checks the profile, planner, and validator results plus every
blocker before copying the draft plan. A nonzero canonical identity is
mandatory. The plan is copied before the release-store of PLAN_FROZEN.

The architecture commit entry is the first operation in
`setup_system_capabilities()`. NONE and BLOCKED return without action.
Any currently impossible PLAN_FROZEN state panics because the mutation
implementation is unavailable. No current source writes COMMITTED,
`commit_complete`, or committed effects.

System and user verification compare receipt ABI, profile, plan identity,
and every typed effect before and after callbacks. READY publication copies
only the admission-facing token, rechecks the receipt, and release-stores
READY. The accessor acquire-loads READY and exposes only that token.

## Independent admission boundary

The ABI 3 work does not relax CPU admission. The selected profile retains
`maxcpus=8`; patch 0092 keeps `cpu_boot=-EAGAIN` and
`cpu_can_disable=false`. A36, P17, and P18 have no READY identity to
consume.

## Identity boundaries

The in-source parent digest identifies the exact patch-0150 selected source
state. The configuration digest identifies ordered manifest inputs. Neither
claims a resolved `.config`, built image, LK container, boot2 contents, or
running image. Those non-circular bindings remain explicit blockers.

## Validation boundary

Offline validation pins the patch, source parent/commit/tree, selected
series, manifest profile, configuration inputs, census, evidence gaps, and
schemas. It applies the patch only in a temporary source tree and performs no
build, network, or device operation.

The mutation suite proves that provenance drift, a partial census, inferred
BHB state, a missing field or blocker, lifecycle reordering, receipt drift,
commit success or live mutation, weaker READY publication, CPU-veto changes,
and build/device authorization all fail closed.
