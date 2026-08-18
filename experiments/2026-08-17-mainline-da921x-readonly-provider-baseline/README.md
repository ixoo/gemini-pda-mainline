# Experiment: LK-repaired DA921x read-only provider baseline

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-17-mainline-da921x-readonly-provider-baseline` |
| Status | `complete; one attributable runtime pass closes Roadmap gate 5` |
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
- [DT builder](scripts/build-provider-dtb.sh): exact package-DT serviceability
  derivation with no second CPU-clock mutation.
- [Candidate builder](scripts/build-candidate.sh) and
  [independent validator](scripts/test-candidate.py): package, configuration,
  DT, Android-v0/LK, padding, no-write, and negative-mutation gates.
- [Guarded installer](scripts/install-boot2.sh): live-GPT boot2 resolution,
  exact full write/readback, and clean shutdown without a fresh backup.
- [Pre-armed collector](scripts/collect-runtime.sh): exact USB/netcat provider
  probe, sanitized classifier, native reboot request, and changed-Gemian return.
- [Prebuild boundary](results/prebuild-boundary-20260817.txt): sanitized live
  prerequisite and predecessor-runtime findings.
- [Buildbox package](results/buildbox-package-20260817.txt),
  [offline candidate validation](results/offline-candidate-validation-20260817.txt),
  [predeployment decision map](results/predeployment-hypothesis-20260817.txt),
  [deployment receipt](results/deployment-1-20260817.txt), and
  [runtime result](results/runtime-attempt-1-success-20260817.txt).

The existing DA921x KUnit suite remains the offline failure/cleanup oracle.
The runtime collector accepts only the exact complete bound record and retains
the full private dmesg below ignored `artifacts/`; its committed result will
contain only bounded, sanitized fields.

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

Buildbox built exact clean commit `7199e8229c6a...` as
`7.1.3-gemini-da921x-lkro`. Package checksums pass and the built Gemini DT
contains all ten exact clock values. Compared with the runtime-proven
predecessor configuration, the substantive delta is the unique release,
DA921x observer, read-only LK-devinfo NVMEM provider, and their expected
framework dependencies. The A72 power driver, resource owner, A72 capability
profile, and KUnit runtime remain disabled; `maxcpus=8` remains forced.

The final DT is derived directly from that package. It adds no CPU-clock
property post-build and restores only the exact proven serviceability group:
peripheral USB, disabled xHCI, disabled SCP input, no watchdog IRQ, I2C5,
AW9523, and the polling keyboard. It preserves the I2C6 access-controller,
read-only LK-devinfo cells, childless DA921x client, and zero-consumer boundary.
The independent candidate validator passes all 32 LK/container gates and
rejects twelve CPU-clock, ownership, consumer, read-only, provider-identity,
and serviceability mutations.

Guarded deployment then resolved logical `boot2` from the live GPT as inactive,
unmounted `/dev/mmcblk0p30` while Gemian used `/dev/mmcblk0p29`. Stable external
power, exact write, sync, flush, full-partition readback, temporary-readback
cleanup, and clean shutdown all passed. The predecessor checksum was recorded
without creating a fresh backup. The device was not rebooted and is confirmed
unreachable after shutdown.

The single runtime attempt then reached the exact
`7.1.3-gemini-da921x-lkro` kernel. CPUs 0--7 were online while CPUs 8--9 and all
A72 admission remained closed. The LK-devinfo handoff passed late validation,
released I2C6 through the existing access-controller edge, and preserved the
shared AP-DMA boundary. The DA921x client emitted one complete bound record:
14 identity reads, two providers, four completed provider reads, and zero
register-data writes. Both buck tuples were internally consistent: selector 70
mapped to 1,000,000 uV for each buck, with buck 0 enabled and buck 1 disabled
at the observation point.

USB/netcat, I2C5, AW9523, the 20 ms polling keyboard, tty1 shell, watchdog, and
native reboot all passed; no block device was mounted and no kernel fault
marker appeared. The initial host classifier stopped after the complete raw
capture because the USB prompt prefixed the begin marker and its procfs probe
searched for `gpio-matrix-keypad` instead of the actual `keyboard-matrix`
input name. The repaired classifier preserves unique exact marker spelling and
requires the exact dmesg registration, polling, driver-binding, and event-node
records. It classifies the same immutable capture as a pass; the remote probe
now uses the correct input name for future experiments.

One authorized native reboot returned the unit to changed-boot-ID Gemian.
Immediate recovery found empty pstore, active root `/dev/mmcblk0p29`, and the
exact candidate still unmounted on live-GPT boot2 `/dev/mmcblk0p30`. The full
partition checksum still matched. The sanitized details are in the
[runtime result](results/runtime-attempt-1-success-20260817.txt); the complete
capture remains private under the ignored `artifacts/` tree.

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

The positive runtime distinguishes the prior deferred path from a regulator
failure: the read-only NVMEM supplier, DVFSP handoff, I2C6 client, and DA921x
provider now complete in order without a DA921x register-data write. Together
with the five-case hardware-free observer KUnit suite and the earlier natural
zero-transaction identification-driver unbind/rebind lifecycle, this satisfies
the resource-only provider exit without claiming writable ownership, resume,
or rail-change safety.

## Conclusion

The runtime boundary is `success-read-only-provider`. The exact raw candidate is
`ab86ce3950a335cc863f4d0a5921b17348cb1c184fcc69f3efa326f8ed22a321`;
its exact 16 MiB boot2 payload is
`eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854`.
The one attributable boot proves that the provider can exist, report both
bucks, and preserve the inherited serviceability/native-reboot baseline with
zero DA921x register-data writes. Roadmap gate 5 is complete for this named
unit and exact revision. This is not write, rollback, resume, or CPU8/CPU9
support.

## Follow-up

Do not repeat this artifact. Open Roadmap gate 6 as a design review for one
predeclared bounded write/readback/rollback operation. CPU8/CPU9 admission and
every unreviewed writable-provider operation remain closed.
