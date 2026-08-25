# Experiment: defer the platform/provider observer until DA921x is bound

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-25-mainline-a72-platform-provider-deferred-bind-repair` |
| Status | planned; definition and hardware-free gates pending |
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

No unchanged predecessor retry is allowed. A physical attempt is eligible only
after generated patch admission, isolated Buildbox compile, no-network KUnit,
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

Pass the definition and mutation gates, generate the three patches on Buildbox,
admit them only after exact replay and strict style, then run the isolated
Buildbox/QEMU profile. No device action is authorized by definition or patch
generation alone.
