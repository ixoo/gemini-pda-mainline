# Mainline CPU8 complete default-off binder

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-27-mainline-a72-default-off-binder` |
| Status | Hardware-free binder proof complete: exact Buildbox compile and QEMU 47/47; no physical candidate yet |
| Subsystem | CPU8 admission, transition owners, PSCI, and generic hotplug lifecycle |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-27 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, complete default-off physical binder |

## Question or hypothesis

Can the proven executor, recovery watchdog, retained ledger, platform-effect
owner, DA921x provider, SRAM owner, MT6797 admission, and lifecycle callbacks
be joined without duplicating ownership or allowing an unrecorded physical
effect?

## Provenance and environment

- Parent repository commit:
  `010fe5781bd18f21a23c91476389fa6e80343570`.
- Canonical series: 384 entries through `0395`.
- Canonical series SHA-256:
  `739dac63e4db1ca606df8cb7518351078a742368787443e93e8dc5d18055c4f9`.
- Manifest SHA-256:
  `57169050ce518a74b1ff04d87ebbe17794fa4684536472f6a5a1aa5c20c20c19`.
- Exact Buildbox prepared-source state:
  `9d03c2ebbde4792b9db0a136c4a12e95c4343e47fb283f413a4acd7fd6f311c0`.
- Build backend for later implementation: Buildbox only.
- Boot path and target partition: none in this phase.

Exact source identities and bounded interface findings are recorded in the
[source interface map](results/source-interface-map-20260827.txt).

## Safety assessment

This phase was a read-only audit of the exact Buildbox source. It performed no
build, MMIO, retained-RAM write, watchdog takeover, regulator or secure call,
PSCI request, CPU operation, device access, boot-image construction, partition
write, reboot, or shutdown.

The MT6797 CPU-boot callback still returns `-EAGAIN`; both lifecycle callbacks
remain unset; the membership owner still refuses admission; there is no binder
arm caller or binder Device Tree node; and no boot candidate is selected.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the repair, ownership, admission, device
  lifetime, lifecycle, and test boundaries.
- [`contract.json`](contract.json) records the exact machine-readable audit and
  selected implementation order.
- [`scripts/validate.py`](scripts/validate.py) validates the frozen record.
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) admits only the validated
  binder profile package and runs one 45-second QEMU `virt` guest with no NIC.
- [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires all 47
  membership, executor, and binder results plus the expected post-test rootfs
  panic boundary.
- [`scripts/generate-owner-stack-fix-on-buildbox`](scripts/generate-owner-stack-fix-on-buildbox)
  generates one test-only follow-up from the exact full-series source after the
  first runtime attempt exposed oversized membership-owner fixtures.
- [`scripts/generate-owner-state-isolation-fix-on-buildbox`](scripts/generate-owner-state-isolation-fix-on-buildbox)
  generates the bounded follow-up for the coupled owner/P30 state and
  configuration-aware PSCI-hook expectations exposed by the second run.
- [`scripts/generate-owner-reset-visibility-fix-on-buildbox`](scripts/generate-owner-reset-visibility-fix-on-buildbox)
  generates the guard-only repair for the P30 reset compile boundary exposed
  by the exact 0402 rebuild.
- [`scripts/generate-owner-reset-field-guard-fix-on-buildbox`](scripts/generate-owner-reset-field-guard-fix-on-buildbox)
  generates the one-file guard repair for two late-startup-only online fields
  exposed by the exact 0403 rebuild.
- [`scripts/generate-owner-fixture-contract-fix-on-buildbox`](scripts/generate-owner-fixture-contract-fix-on-buildbox)
  generates the test-only repair for the three fixture-contract mismatches
  isolated by the exact 0404 QEMU run.
- [`scripts/generate-owner-p29-claim-fix-on-buildbox`](scripts/generate-owner-p29-claim-fix-on-buildbox)
  generates the test-only completion of the public preflight, validation, and
  claim sequence in both legacy P29 fixtures.

## Audit result

Direct glue is rejected. The individual owners are sound, but seven boundary
repairs are required before they can safely form a physical path:

1. make regular executor checkpoints fallible and require a terminal retained
   commit, so a ledger error cannot be ignored before a hardware effect;
2. admit only one membership-owned CPU8 token instead of trusting caller
   Booleans, while keeping CPU9 and every unarmed request closed;
3. hold immutable references to the watchdog, platform-state, and BigiDVFS
   supplier devices, resolved by an unarmed default-off binder device;
4. expose a narrow binder API so arm64 does not depend on the executor's
   driver-private header;
5. terminalize the binder before the existing P32 rollback publisher on a
   generic CPU-up failure; and
6. add one exact post-proof membership success publication, because the current
   owner never commits CPU8 membership outside bootstrap and test seeding.

The current executor and watchdog constants both specify 15000 ms. The
watchdog identity remains evidence only. Ledger, platform, SRAM, membership,
and lifecycle records share the membership transaction identity; the provider
lease has its own exact generation/cookie handle, linked by the owner proof.

## Selected implementation

Generate five logical patches from this contract:

1. repair the executor's retained-checkpoint contract and test every new
   failure boundary;
2. add membership-owned admission, CPU_ON consumption, publication,
   finalization, clean rejection, and four real-owner KUnit cases;
3. add the closed DT binding without a base DT node;
4. add the default-off binder, typed physical adapters, and MT6797 lifecycle
   handoffs; and
5. add five injected binder KUnit cases and the hardware-free profile.

The binder proof adds no late CPU caller and no enabled binder DT node. Its
static validator and sole bounded no-network QEMU run must demonstrate zero
physical calls, zero production CPU requests, zero CPU_OFF, and zero retries.
Only after that proof may a separate device-candidate change add one exact late
caller and one enabled binder node.

## Buildbox compile result

The exact repaired revision `0f5a1d709ee2ff8d103aa762d44e1e2ae4e6a080`
passed the `a72-default-off-binder-kunit` build and package validator on
buildbox. The realized configuration selects exactly the membership-owner,
executor, and binder KUnit options and keeps `HOTPLUG_SPLIT_STARTUP` disabled.
The new binder production and test objects compiled without a binder-specific
warning. The full log retains inherited diagnostics: 44 compiler-warning lines
in older membership/DVFSP sources, 12 `ranges_format` DTC warnings, and one
patch whitespace warning. Exact identities and the warning breakdown are in
the [compile evidence](results/buildbox-compile-0f5a1d70.txt).

The built package is intentionally not a boot candidate. It has no late CPU
caller and no binder DT node, and it has not been written to any device.

## First QEMU result

The first actual 45-second, no-network QEMU run reached the 30-case membership
owner suite, then exposed the compiler's inherited large-frame warnings as a
real arm64 kernel-stack defect. Seventeen cases faulted while clearing local
40--75 KiB fixtures, three small cases passed, and one further case failed only
after the preceding faults had corrupted shared owner state. The guest then
panicked with `Kernel panic - not syncing: kernel stack overflow` before the
remaining owner cases, executor suite, or binder suite could run.

The raw log remains a private ignored artifact; its sanitized identity and
classification are in the [runtime rejection evidence](results/kunit-qemu-stack-overflow-0f5a1d70-20260828.txt).
This is a test-only blocker, not evidence about the physical CPU8 path. The
next revision moves every large owner observation, transaction, and snapshot
into one KUnit-managed per-case fixture. A new exact package will receive one
new bounded run; a physical candidate remains a separate later change.

## Owner KUnit stack repair

Buildbox generated and replay-validated one test-only patch from the exact
full-series source. It changes only
`arch/arm64/kernel/mt6797_a72_membership_test.c`: all 30 owner cases remain,
but their large observations, transaction, and snapshot now share one
KUnit-managed per-case scratch allocation. The remaining zero transaction is
static, and `memchr_inv()` checks it without creating another large stack
object.

The exact canonical
[`0401` patch](../../patches/v7.1.3/0401-arm64-mediatek-move-MT6797-A72-owner-KUnit-state-off-stack.patch)
has SHA-256
`28d73ca2035d457022c4d8589db7344599044d83a5b1a6d4bf130093136edaf7`.
Strict checkpatch reports zero errors, warnings, or checks. Generation and
replay observed zero production-file changes and performed no physical or
device action.

The corrected exact profile rebuild passed on Buildbox. It removed the former
40--75 KiB owner-test frames and retained one 5,632-byte warning in the P32
case, below the 16 KiB arm64 task stack. The default multithreaded TCG launch
then produced an empty serial log; an explicit single-thread TCG diagnostic
booted immediately and completed all 47 cases. The stack overflow is gone,
the executor passes 12/12, and the binder passes 5/5. The owner suite now
passes 20/30 and exposes two stale pre-binder hook expectations plus eight
subscenarios that reseed membership state without resetting the coupled P30
test state. Exact identities are in the
[second runtime rejection evidence](results/kunit-qemu-owner-isolation-1f26f2fc-20260828.txt).

The harness now pins single-thread TCG for deterministic launch. Buildbox
generated and replay-validated the exact canonical
[`0402` patch](../../patches/v7.1.3/0402-arm64-mediatek-isolate-MT6797-A72-owner-KUnit-state.patch),
with SHA-256
`e0f55cfbf702186518de20b6c1bef7637d64a1a682bae4f99fa00322e36528d5`.
It retains all 30 owner cases, adds one coupled case reset, converts 11 basic
and six CPU9 reseeds to reset the P30 state with membership, and makes the
three PSCI-hook expectations binder-aware. Strict checkpatch reports zero
errors, warnings, or checks.

The patch changes only the membership-owner test source. Generation and replay
observed zero production-file changes and performed no physical or device
action. The first exact profile rebuild was rejected while compiling the owner
test: the existing `arm64_late_cpu_startup_test_reset()` declaration and
definition were guarded only by the standalone late-startup KUnit option,
while this profile selects the owner KUnit option. The exact failure is in the
[0402 compile evidence](results/buildbox-compile-fail-21ff0073-20260828.txt).

Buildbox generated and replay-validated that bounded repair as the exact
canonical
[`0403` patch](../../patches/v7.1.3/0403-arm64-expose-MT6797-A72-owner-KUnit-P30-reset.patch),
with SHA-256
`862542ec2a89db3eda79358fecd823b720f173b891cdee47325266fa692833b9`.
It widens only the existing reset's preprocessor guard to either test
configuration and keeps the online-state helper under its original narrower
guard. Strict checkpatch reports zero errors, warnings, or checks across 31
lines. The patch changes two production-owned source files but adds only test
preprocessor guards; it changes no production configuration, function body,
or runtime path.

The first exact 0403 rebuild passed the original declaration boundary, then
failed while compiling the shared reset body because it still cleared the
`test_online_cpu` and `test_online` fields that exist only under the standalone
late-startup KUnit option. The exact failure is in the
[0403 compile evidence](results/buildbox-compile-fail-a8942401-20260828.txt).

Buildbox generated and replay-validated that bounded repair as the exact
canonical
[`0404` patch](../../patches/v7.1.3/0404-arm64-guard-late-CPU-online-KUnit-reset-state.patch),
with SHA-256
`e677de07b9d48c1030a144df4517be620b30083f741ef2e670579a83876299b5`.
It changes only `late_cpu_startup.c` and adds exactly one `#ifdef/#endif` pair
around the two late-startup-only assignments. Strict checkpatch reports zero
errors, warnings, or checks across 10 lines.

The common P30 reset remains visible to the owner suite, while production
configuration and runtime behavior remain unchanged. The exact 0404 Buildbox
compile passed, and its bounded single-thread TCG QEMU proof emitted all 47
cases: the owner suite passed 22/30, while the executor passed 12/12 and the
binder passed 5/5. The eight failures reduce to three stale test-fixture
classes: partial plan-identity invalidation, CPU8-only fields retained in the
CPU9 prestate fixture, and two P29 paths that omit the Binder public-preflight
claim. Exact identities and classification are in the
[third runtime rejection evidence](results/kunit-qemu-owner-fixtures-91217dda-20260828.txt).

Buildbox generated and replay-validated the test-only 0405 repair from exact
repository commit `4fc67aaf2985668da34e1fc3d771ee121a0e8fe7`. It changes only
`arch/arm64/kernel/mt6797_a72_membership_test.c`, repairs the three fixture
classes above, retains all 47 cases, and changes no production file. The patch
SHA-256 is
`df13fbfdc7a974e8da8f3fbee1f6f61cddb359c8f781ddb5af0e44d9cf99ca49`;
strict checkpatch reports zero errors, warnings, or checks. Generation and
source replay performed no physical or device action. It was admitted in
signed commit `9366cd4923cef87a4c3f57c1f954fb5257139942`. This profile is
not a boot candidate.

The canonical 0405 admission is signed commit
`9366cd4923cef87a4c3f57c1f954fb5257139942`. Its exact Buildbox profile build
passed and produced package
`linux-7.1.3-gemini-a72-default-off-binder-kunit-3b64bed4-010f5c59`.
The sole new 45-second single-thread TCG run emitted all 47 cases and improved
the owner suite from 22/30 to 29/30; the executor remained 12/12 and the binder
remained 5/5. It proved that 0405 repaired all identity and CPU9 fixture drift.

The remaining valid P29 rollback failed because its fixture stopped after
public preflight and never validated and claimed CPU8. The mutation companion
therefore passed before reaching its intended mutated-proof check. Exact
identities are in the
[fourth runtime rejection evidence](results/kunit-qemu-owner-p29-claim-9366cd49-20260828.txt).
Buildbox generated and replay-validated that bounded test-only repair from
exact repository commit `be6d82625d6cbf00c1f2efa7f51f282c1f28fcef`.
It completes preflight, validation, and claim in both P29 fixtures, changes no
production file, and has patch SHA-256
`d85a84dc5458c5cd6c513f17596f58b08de727acad2f37b9727f1670c0f36b9c`.
Strict checkpatch reports zero errors, warnings, or checks. The exact canonical
[`0406` patch](../../patches/v7.1.3/0406-arm64-mediatek-claim-CPU8-in-P29-KUnit-fixtures.patch)
was admitted in signed commit
`3efb123a64b9eb86e307cf957cdb81298b1986f5`.

The clean exact commit compiled on Buildbox as package
`linux-7.1.3-gemini-a72-default-off-binder-kunit-5bf78b43-010f5c59`.
Its one fresh bounded, no-network, single-thread TCG run passed all 47 cases:
owner 30/30, executor 12/12, and binder 5/5, with no failures or skips. Both
the valid P29 rollback and its mutated-proof rejection reached their intended
claimed-transaction paths and passed. The expected post-suite rootfs panic
occurred only after KUnit completed.

This closes the hardware-free binder proof. The classifier recorded zero
production callers, physical backends, physical CPU requests, CPU_OFF requests,
retries, MMIO, retained-RAM access, SMCs, device actions, or enabled binder DT
nodes. Exact package and runtime identities are in the
[passing runtime evidence](results/kunit-qemu-pass-3efb123a-20260828.txt).
No second run of either earlier artifact occurred, and this KUnit package is
not a boot candidate.

## Follow-up

The authoritative ordered next step is
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). This experiment
proves the default-off binder and its dependencies without hardware access. It
does not itself admit a device candidate; Gate 7 now owns the separate design
and validation of one decision-bearing CPU8 physical candidate.
