# Experiment: defer the platform/provider observer until DA921x is bound

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-25-mainline-a72-platform-provider-deferred-bind-repair` |
| Status | first runtime passes provider-ready composed snapshot |
| Subsystem | MT6797 A72 platform/provider snapshot dependency ordering |
| Device variant | Gemini PDA, named project device |
| Date | 2026-08-25 |
| Boot path | retained LK, owner-selected non-primary `boot2` |

## Question or hypothesis

Will an explicit DA921x endpoint phandle and bound-device gate make the
observer defer before any platform read or retained checkpoint, then run the
unchanged one-shot platform/provider capture after the provider registers?

The predecessor attempt was serviceable but terminally unbound. Its observer
retried after the platform source bound at 1.143926 seconds, returned
`-ENODEV` at 1.146260 seconds, and was not retried after DA921x `1-0068` bound
at 46.149957 seconds. Changed-ID Gemian recovered exact `before-provider`
record 1 and exact-empty record 2. Registry source proves the empty-registry
`-ENODEV` occurs before the DA921x callback and therefore before any provider
I2C transfer. See the exact predecessor
[runtime receipt](../2026-08-25-mainline-a72-platform-provider-snapshot-second-read/results/runtime-attempt-1-provider-not-ready-20260825.txt).

## Frozen repair boundary

Canonical parent is patch `0370`. The repair is exactly three logical changes:

1. production source resolves `mediatek,provider`, requires the referenced
   `dlg,da9214-legacy` I2C device to be bound, and returns `-EPROBE_DEFER`
   before `mt6797_a72_pp_capture()` otherwise;
2. the observer binding requires that provider phandle; and
3. injected KUnit passes a missing provider reference and proves zero platform,
   checkpoint, and provider calls, while the existing ready success case still
   performs the exact four-event sequence once.

The device candidate DT will add only a phandle to the existing `regulator@68`
node and one `mediatek,provider` reference on the existing observer. Removing
those two properties must recover the byte-identical sorted predecessor tree.

The capture itself is unchanged: 26 read-only platform register observations,
then record 1, then two stable samples of provider registers
`0x56,0x51,0x5e,0xd9,0xda` for ten read-only pointer/read transfers, then record
2. There is no capture retry, register-data write, protected-clock or BigiDVFS
read, secure call, provider acquire/release, publication, owner mutation, or
CPU request.

## Provenance

- Canonical parent:
  `patches/v7.1.3/0370-soc-mediatek-test-A72-platform-provider-snapshot-observer.patch`.
- Prepared Buildbox source state:
  `2fe5ef253a8c2fa73af53fa2f3b6a98df04da4faf35263ab145a69e2a6bd795e`.
- Prepared-source integrity:
  `7abaf44dfe744882e4fdbf46db13ae0ea4a558f197ec5a39137ede67e42da718`.
- Planned canonical changes: `0371` production dependency gate, `0372`
  binding contract, and `0373` injected dependency tests.
- Buildbox generation from exact signed commit `9a2ca827` passed source,
  replay, strict-style, checksum, and byte-exact admission gates. The three
  patches retain a clearly synthetic non-certifying author, have no synthetic
  sign-off, and are not submission-ready.
- Exact admitted commit `5df73082` compiles as
  `7.1.3-gemini-a72-provider-ready-kunit` on Buildbox with no new observer
  warning. The sole no-network QEMU suite passes all seven cases, including
  provider-not-ready with zero injected effects; eight classifier mutations
  fail closed. No physical I2C, MMIO, retained RAM, device, or native VM action
  occurred.
- Exact clean commit `db62ca34` also compiles the isolated device profile on
  Buildbox as `7.1.3-gemini-a72-provider-ready`. Its fetched package and
  manifest pass with `Image.gz` `83e807d0...` and no new observer warning.
- The exact predecessor DT `ee8baf00...` derives `923575e4...` by adding only
  provider phandle `0x30` and the observer's `mediatek,provider` reference.
  Removing both properties recovers the byte-identical sorted predecessor.
- Two independent Android-v0 assemblies and padding paths produce raw
  `041896e2...` and exact 16 MiB `boot2` `f55bb272...`. All 32 LK gates pass;
  six container, 22 runtime, and 15 recovery mutations fail closed.
- Read-only Gemian preflight finds the exact predecessor `before-provider`
  record followed by an exact-empty record while `boot2` remains the failed
  predecessor `ff902d12...`. No retained-memory or partition write occurred.
- Signed publication commit `db5ba55a` is pushed to `origin/main`. The guarded
  installer resolved inactive, unmounted live-GPT `boot2` as
  `/dev/mmcblk0p30`, matched predecessor `ff902d12...`, stable power, and both
  TEE identities, then passed write, sync, flush, full 16 MiB readback
  `f55bb272...`, cleanup, and confirmed clean shutdown. It made no fresh
  backup, retained-RAM write, primary-boot write, or reboot request.
- The first owner-selected boot is an exact live pass. At 46.168676 seconds,
  after DA921x bound, the observer emitted terminal
  `provider_ready_gate=passed`. It completed one two-sample platform snapshot
  with 26 observations and one two-sample provider snapshot with ten read-only
  transfers; the stable provider tuple is `7b/c1/00/46/46`. Stage-27 USB,
  T-PHY, I2C5, keyboard, all three suppliers, and CPUs 0--7 remained healthy.
  CPUs 8--9 and every protected-clock, BigiDVFS, secure, provider-action,
  publication, owner-mutation, and CPU-request path remained closed. The
  collector sent no reboot and left mainline running.
- Build backend: Buildbox only. A native VM kernel build is prohibited unless
  the owner explicitly requests that specific build.

Exact identities, effects, and exclusions are pinned in
[`contract.json`](contract.json); the call and decision boundary is frozen in
[`DESIGN.md`](DESIGN.md).

## Safety assessment

The definition, patch generation, replay, style checks, KUnit compile, and QEMU
run are hardware-free. The eventual candidate keeps exact `maxcpus=8` and the
same read-only ceiling as its predecessor. The new readiness path performs
only DT lookup, device lookup, reference management, and bound-state testing;
it does not access I2C, MMIO, retained RAM, storage, clocks, regulators, secure
firmware, or CPUs.

No unchanged predecessor retry is allowed. The repaired physical attempt is
eligible only after generated patch admission, isolated Buildbox compile,
no-network KUnit,
reversible DT validation, deterministic Android-v0 assembly, live-GPT guarded
`boot2` write/readback/shutdown, and a pre-armed result classifier.

## Decision map

| Unique result | Interpretation | Decision |
| --- | --- | --- |
| Exact live identity, provider-ready terminal receipt, both snapshots complete | Dependency repair worked and ten provider reads completed | Qualify the composed provider tuple; isolate protected-clock next |
| Observer remains deferred while DA921x is bound | The explicit dependency or deferred-probe trigger is wrong | Repair only provider lookup/linkage |
| Exact live bounded provider-read error after provider-ready | Readiness is fixed; failure is inside the ten reads | Split the fixed provider read sequence |
| Changed-ID Gemian with no record | Capture never crossed the first checkpoint | Correlate live defer/error; do not implicate provider I2C without evidence |
| Changed-ID Gemian with only record 1 | Capture reached the provider callback but did not return | Split the fixed provider read sequence |
| Changed-ID Gemian with both records | Provider returned; later observation/serviceability failed | Repair only the post-checkpoint path |

## Next

Retire this artifact: the explicit provider dependency and composed read-only
tuple are qualified for this exact boot. Freeze the next third-reader boundary
before changing code: add only one stable protected-clock observation after
the passed platform/provider snapshot, retain independently recoverable
before/after checkpoints, and keep BigiDVFS reads, provider actions,
publication, owner mutation, and CPU admission closed.
