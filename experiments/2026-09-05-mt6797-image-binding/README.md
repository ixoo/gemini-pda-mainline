# Private immutable C image binding and lifetime

This implements a bounded part of the shared ownership proposal in actual C:
private immutable firmware/plan storage, persistent generations, serialized
passive client claims, complete-plan prevalidation and fault-held retention.
It does **not** implement the physical CONSYS provider. Active entry always
refuses, including for ordinary-only images. No DT registration, hardware
callback, resource-success stub, backend or device operation is added.

The single logical [review patch](0004-wifi-mediatek-retain-private-image-bindings.patch)
adds `image-binding.{c,h}` beside the existing private HIF/plan code and one
`image-binding.o` Makefile entry. It depends on plan proposal
`f9c13fe954cc8141de51b8f5c87c44632a1e3eea`; exact existing parser/plan files are
read from pinned Git objects and verified by [inputs.json](inputs.json).
No dependency implementation is forked or vendored. Canonical series, manifest
and running build inputs are unchanged. The patch is an experiment archive,
not an upstream submission: its synthetic author is non-certifying and has
no invented DCO sign-off.

## Implemented behavior

[`image-binding.c`](src/image-binding.c) caps input before allocation, copies
it to manager-owned `kvmalloc` storage, and only then calls the actual
`mt6797_image_plan_prepare()` on that allocation. Copying requires caller
stability during the call; it cannot repair a concurrently modified input.
The prepared plan is private, points into the same owned allocation and cannot
be reparsed or invalidated by an external plan owner. Public getters return
descriptive metadata only, never executable views or a byte pointer.

The mutex protects the registry, generation history and every binding's
plan/state. Each successful client claim or binding consumes a nonzero 64-bit
generation. Failed construction publishes neither handle nor generation and
does not consume one. History persists when a binding is freed or invalidated;
exhaustion at the maximum refuses rather than wrapping. Reusing a manager
allocation as a new domain does not authorize old handles: the eventual
provider must retain one domain for its lifetime, join all users before
destruction and discard all old handles. This is not use-after-free protection
or a security boundary against arbitrary kernel memory modification.

WMT/WLAN/BT/GNSS passive registrations exclude image creation; an image excludes
every new client claim and another image. Stale unclaim/release tokens cannot
remove a current claim. This proves software serialization only, not that
unregistered firmware clients are idle or that multiple independent managers
own the same hardware safely.

Every section is described and every EMI span checked against the format's
first-512-KiB window before publishing a binding. `prevalidate()` checks that
the private plan still belongs to the copied allocation and describes all
entries. These are format checks, not validation of a live reservation.
The existing `image_plan_admit/get_ordinary` mixed-image refusal is unchanged
and is not bypassed to obtain an executable payload. `begin()` returns the
validation error or `-EOPNOTSUPP`, never active success.

Explicit invalidation revokes the private plan and permits ordinary passive
cleanup. A conservative `hold_fault()` notification instead latches the first
negative error, retains the snapshot and registry claim, and refuses further
planning/entry/invalidation/release. It only makes the state less permissive;
it cannot assert successful effects or manufacture quiescence. An owner with
any claim or held image cannot be freed. No recovery/clear-held API is present.

Caller lifetime rules remain necessary: join all users before releasing a
binding or destroying its manager. A mutex cannot make a pointer safe after
another caller has freed it. This code serializes live-object operations;
it does not provide a separate reference-counted external handle service.

## Executed validation

Run `python3 -B experiments/2026-09-05-mt6797-image-binding/scripts/verify.py`.
The runner compiles the actual binding and pinned C parser/plan, with only
allocation and mutex shims. It reproduces/replays the format-patch from a tiny
managed text fixture, not a Linux checkout. Temporary state has scoped cleanup,
locking and marked stale-state removal. The committed
[validation result](validation.json) records compiler, hashes and full output.

Strict C11 warnings-as-errors, conversion warnings, AddressSanitizer and
UndefinedBehaviorSanitizer passed. The fixtures cover copied/freed caller input
and invalidated caller plans, stale generations, revoked private plans,
late-EMI defects, no output publication on failure, size-cap-before-allocation,
all three allocation failure boundaries, all four competing client types,
generation exhaustion, and fault retention with first-error preservation.
Thirty-two rounds race eight actual pthread callers for one image: each round
must publish exactly one binding and refuse the seven competitors. Allocation
accounting verifies passive cleanup and zero frees from held-release attempts.

The final held-state fixture destroys its **test allocator environment** after
checking that the production API cannot release or reactivate it and after
all users have joined. That hardware-free cleanup does not call a recovery
API, return a usable object or claim a quiescence witness. The only source
test hook sets an idle generation domain near exhaustion; it is absent from
kernel compilation and cannot decrease the counter even in tests.

Strict checkpatch reports no source findings. Its generic MAINTAINERS warning
and missing-DCO error are retained unfiltered because the archived author
makes no certification. Host shims do not validate kernel allocator/mutex integration; subsequent
kernel compilation is recorded below. No hardware test has run for this delta.

## Exact next provider connection

The existing `begin()` must remain refusing until the real provider is wired.
Do not replace its final return with success after the current unlocked
prevalidation call. A real begin operation must hold the lifetime/generation
guard across admission and first-effect marking, reject a concurrently revoked
plan, and retain an owner-backed effect state **before** any possible I/O.

That connection must supply the confirmed downloader/power epoch, actual
reserved bounds, remap/MPU policy and selector ownership, external-client
exclusion, and HIF IRQ/reset/host-ownership lifetime described in
[the shared-owner contract](../2026-09-05-mt6797-wifi-contract/SHARED_OWNER_IMPLEMENTATION.md).
It must check all EMI spans against that actual binding before any ordinary
transfer. Only then can the executor obtain internal section views, execute
ordinary transfers, perform ordered index-checked EMI copies, seal protection,
and call the real START core. Mark START attempted before its first access and
retain resources on uncertain return. Nothing here asserts eligibility for
the integration owner's separate START proposal.

Actual quiescence is also required before any future held-state release.
Neither a caller Boolean nor successful PM put may clear retention. The current
passive registry is not that provider, and AP-DMA translation remains a
separate backend issue rather than a prerequisite for PIO host implementation.
The coordinator owns eventual series selection and a separately admitted
Buildbox compile; [proposal.json](proposal.json) identifies this patch's delta.

## Coordinator integration

[The shared compile integration](../2026-09-05-mt6797-hif-start-core/INTEGRATION.json)
places this patch after START in the canonical series, under filename `0005`,
without changing its bytes. [Compilation and linkage passed](../2026-09-05-mt6797-hif-start-core/BUILD_RESULT.md).
Active entry remains refused and no device candidate is selected.
