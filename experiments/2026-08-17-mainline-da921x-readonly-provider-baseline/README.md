# Experiment: LK-repaired DA921x read-only provider baseline

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-17-mainline-da921x-readonly-provider-baseline` |
| Status | `prebuild source and profile validation passed` |
| Subsystem | retained LK DT handoff, MT6797 DVFSP/I2C6, legacy DA921x regulator provider |
| Device variant | Planet Gemini PDA, named development unit |
| Date(s) | 2026-08-17 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | none |

## Question or hypothesis

Can the runtime-proven LK CPU-clock repair be made part of the kernel-built
Gemini DT while the existing read-only LK-devinfo, DVFSP handoff, I2C6, and
DA921x provider path binds and reports both buck states with exactly zero
register-data writes?

The predecessor kernel already compiled the DA921x resource-only provider, but
its successful runtime did not exercise that provider. `CONFIG_NVMEM` was
disabled while the final DT made the DVFSP handoff depend on the LK-devinfo
NVMEM cells. Linux therefore left the handoff and I2C6 deferred, before the
DA921x client could probe. This experiment changes that one prerequisite rather
than bypassing the established I2C6 access-controller boundary.

## Provenance and environment

- Runtime-proven predecessor: exact kernel build commit `98996fdfbf09...`,
  kernel `7.1.3-gemini-entryled-a`, and exact boot2 payload
  `b478b79a983889514b2b8d122fb6d5ff5057e52c332882b186b82698d1de62b8`.
- Predecessor runtime record:
  [LK CPU-clock iterator repair](../2026-08-17-mainline-lk-cpu-clock-iterator-repair/results/runtime-attempt-1-serviceable-20260817.txt).
- New canonical patch:
  [0282](../../patches/v7.1.3/0282-arm64-dts-mediatek-add-Gemini-LK-CPU-clock-rates.patch).
- Named profile: `da921x-lk-clock-readonly-provider`.
- Build backend: Buildbox only after the exact repository revision is committed
  and pushed. A native VM kernel build is prohibited by project policy.
- Boot path after every offline gate passes: Android-v0/LK container to
  live-GPT-resolved logical `boot2` only.

## Safety assessment

This candidate keeps `maxcpus=8`, the A72-power initcall blacklist, and the
absence of any CPU8/CPU9 admission request. The DA921x provider exposes only
`get_voltage_sel`, `list_voltage`, and `is_enabled`; the observer invokes only
those read-only operations. No regulator child, supply phandle, setter,
enable/disable operation, IRQ, transition owner, or A72 consumer is added.

The NVMEM provider copies only the validated LK `/chosen/atag,devinfo` handoff
into read-only cells. It does not map or write efuse MMIO. Keeping the existing
`access-controllers = <&dvfsp_handoff>` relationship preserves the previously
validated I2C6 arbitration and cleanup boundary instead of bypassing it.

Any provider read failure, malformed identity, nonzero register-data-write
count, handoff denial, CPU8/CPU9 admission, loss of the serviceability baseline,
kernel fault, or automatic reboot rejects the candidate. A permitted boot2
installation uses the existing guarded workflow, creates no fresh backup,
requires full-partition readback, and shuts Gemian down without rebooting.

## Associated code

- [DESIGN.md](DESIGN.md): exact source/configuration boundary and runtime
  decision map.
- [Static validator](scripts/validate.py): canonical patch, profile ancestry,
  no-write, CPU-clock, and consumer-closure checks.
- [Prebuild boundary](results/prebuild-boundary-20260817.txt): sanitized live
  prerequisite and predecessor-runtime findings.

The existing DA921x KUnit suite remains the offline failure/cleanup oracle. A
new runtime collector and candidate builder will be derived only after the
Buildbox package fixes the exact Image, configuration, and DT identities.

## Procedure

1. Validate the new canonical DTS patch, profile ancestry, manifest-series
   invariant, observer no-write boundary, and CPU8/CPU9 closure locally.
2. Commit and push the exact clean repository revision.
3. Build `da921x-lk-clock-readonly-provider` only through Buildbox and fetch
   only its validated package.
4. Require the resolved configuration to differ from the successful
   predecessor only by the unique release, read-only NVMEM provider, and
   DA921x observer gates. Require the built Gemini DT to contain all ten exact
   CPU clock properties.
5. Derive the final serviceability DT from that exact package without adding a
   second CPU-clock mutation. Revalidate USB peripheral mode, xHCI closure,
   I2C5/AW9523/polling keyboard, disabled SCP input, no watchdog IRQ, I2C6
   access-controller, childless DA921x provider, and CPU8/CPU9 closure.
6. Assemble and independently validate one attributable Android-v0 candidate.
   Freeze its runtime hypothesis and observer before any device action.
7. If all gates pass, install once to inactive logical `boot2`, require exact
   full readback and clean shutdown, then observe one physical boot selection.
8. Accept only one exact DA921x bound record with 14 identity reads, two
   providers, four completed provider reads, internally consistent selector /
   voltage / enable values, and zero register-data writes, together with the
   inherited serviceability and native-reboot gates.

## Observations

The promoted predecessor reached `/init`, USB/netcat, CPUs 0-7, I2C5, AW9523,
the polling keyboard, and watchdog takeover, and later rebooted natively to
Gemian. Its final DT carried all ten exact CPU clock properties. Its dmesg also
showed the still-open provider boundary precisely:

- `11015000.dvfsp-handoff` remained deferred waiting for
  `/firmware/atag-devinfo/cpu-efuse-identity@58`;
- `1100e000.i2c` remained deferred waiting for that handoff supplier; and
- the built-in DA921x driver registered, but no DA921x client probe occurred.

On the current known-good Gemian boot, the live LK handoff property exists with
the expected non-sensitive structure: 412 bytes and fixed header words
`0x00000067,0x41000804`. No payload value was printed or recorded.

Patch 0282 adds the exact Stage-27 rates to all ten existing board CPU labels.
The new profile is an exact extension of the runtime-proven entry-ledger
profile and adds only the read-only NVMEM and DA921x observer gates plus a
unique local version. The whole-manifest canonical-series audit still passes
for all 80 profiles.

## Analysis

The previous apparent provider failure was not a regulator result. The DA921x
client was unreachable because the serviceability profile disabled the only
driver that could satisfy an already-present DT supplier edge. Enabling that
read-only provider is narrower and safer than deleting the edge: it preserves
the validated DVFSP/I2C6 ownership protocol and fails closed if LK supplies a
missing or malformed property.

The new DTS patch also removes a process hazard. Future candidates no longer
depend on a post-build CPU-clock edit merely to reach Linux; the package DT is
itself a valid input to the retained LK iterator. Linux CPU admission is
unchanged because `clock-frequency` is descriptive and `maxcpus=8` remains.

## Conclusion

The source/profile boundary is `confirmed` for prebuild validation only. No new
kernel package or hardware result exists yet. DA921x runtime registration,
selector/enable observations, cleanup, and zero-write evidence remain pending
the exact Buildbox package and one later attributable boot.

## Follow-up

Commit and push this exact definition, build the named profile on Buildbox, and
use the fetched package to freeze the final DT/container and runtime decision
map. CPU8/CPU9 admission and every writable-provider operation remain closed.
