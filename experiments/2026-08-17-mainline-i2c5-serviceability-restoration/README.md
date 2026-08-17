# Experiment: I2C5/AP-DMA and polling-keyboard serviceability restoration

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-17-mainline-i2c5-serviceability-restoration` |
| Status | one attempt returned preloader-only before changed Gemian; candidate stopped |
| Subsystem | MT6797 I2C5/AP-DMA, AW9523 pinctrl/GPIO, polling matrix keyboard |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-17 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline serviceability prerequisite to CPU8 work |

## Question or hypothesis

Does restoring the complete runtime-proven I2C5/AW9523 polling-keyboard group
to the stopped current-DT line restore mainline serviceability? Preserve the
exact stopped kernel, initramfs, Android-v0 container, USB observation nodes,
disabled SCP input, no-watchdog-IRQ path, I2C6/DA921x closure, and CPU8/9
closure. Restore the group as a coherent contract rather than enabling an
incomplete controller or an interrupt mode absent from the positive control.

The causal mechanism under test is the missing established serviceability and
shared-clock baseline, not a claim that I2C5 is required for MTU3 probe. Exact
Stage-27 dmesg proves MTU3 completed first at 0.900803 seconds; I2C5 completed
at 0.942402 seconds, watchdog at 0.967423 seconds, and the deferred polling
keyboard at 1.123543 seconds. A positive result therefore restores the full
post-MTU3 serviceability foundation but does not move the MTU3 probe boundary
earlier.

## Provenance and environment

- Stopped predecessor DT SHA-256:
  `49d8189b3801c2e95345857ff704ab0b819001c55101f16dd1949cfa5106d3aa`.
- Runtime-proven Stage-27 DT SHA-256:
  `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806`.
- Exact kernel package remains repository commit
  `98996fdfbf09f8de2a6b86e488defef22fcc7968`, release
  `7.1.3-gemini-entryled-a`.
- Packaged I2C5, AW9523, matrix-keypad, MTU3, T-PHY, and watchdog drivers are
  built in.
- No kernel compilation is needed. No native VM build is permitted or run.

## Safety assessment

This is not a no-hardware-write candidate. It restores the already
runtime-proven AW9523 keyboard probe: reset-GPIO sequencing, ChipID read, safe
GPIO/input defaults, interrupt disable, pin configuration, and polling matrix
operation. The positive Stage-27 runtime proved this exact group serviceable.
The candidate deliberately removes the current DT's unused AW9523 parent-IRQ
contract so it matches that polling control.

No DA921x register-data operation, I2C6 ownership change, regulator action,
CPU8/9 admission, storage write, or host-mode USB action is introduced. Any
device installation remains limited to the standing logical-`boot2` policy,
full readback, and clean shutdown.

## Associated code

- `scripts/build-serviceability-dtb.sh`: source-pinned stopped-predecessor
  derivation and exact coherent I2C5/AW9523/polling-keyboard restoration.
- `scripts/build-candidate.sh`: source-pinned deterministic Android-v0
  container assembly around the unchanged kernel and initramfs.
- `scripts/test-candidate.py`: independent layered container, SCP, watchdog,
  serviceability-contract, provenance, and negative-mutation validation.
- `scripts/install-boot2.sh`: source-pinned guarded logical-`boot2` installer
  with full readback and clean shutdown.
- `scripts/collect-runtime.sh`: source-pinned pre-armed USB/netcat observer
  bound to the deployment Gemian boot ID and exact candidate checksum.
- `results/serviceability-boundary-20260817.txt`: exact DT partition, built
  initcall/runtime order, shared AP_DMA evidence, write scope, and selection.
- `results/offline-candidate-validation-20260817.txt`: immutable inputs,
  candidate identities, reproducible tooling, and completed offline gates.
- `results/predeployment-hypothesis-20260817.txt`: unique observation and
  decision map for the single candidate attempt.
- `results/deployment-1-20260817.txt`: live-GPT target, predecessor, exact
  write/readback identity, and confirmed shutdown receipt.
- `results/observer-window-1-no-attempt-20260817.txt`: the first armed window's
  retained identities and explicit no-attempt classification.
- `results/runtime-attempt-1-no-mainline-usb-20260817.txt`: live observer,
  exact USB sequence, changed-Gemian recovery, reset class, empty pstore, and
  post-cycle boot2 identity.

Generated candidates remain below the ignored `artifacts/` tree.

## Procedure

1. Recompute the semantic Stage-27/current difference after the tested USB,
   SCP, and watchdog deltas.
2. Map each remaining active property group to its exact built consumer and
   positive-control timing.
3. Restore the complete polling-keyboard group, including its I2C5 timing and
   pinctrl inputs, while rejecting the unproven AW9523 parent-IRQ mode.
4. Derive twice, assemble twice, validate exact container identities, and
   reject independent semantic mutations before considering deployment.
5. Publish a one-attempt hypothesis and arm a fresh observer before any boot.

## Observations

The remaining semantic groups are CPU `clock-frequency`, chosen/simplefb,
reserved-memory compatible strings, scpsys's extra `syscon` compatible,
current-only disabled DVFSP backend nodes and unused nvmem properties, the
watchdog reset-provider property, and the active I2C5/AW9523/keyboard group.
The first six are passive or already shown not to add a unique failing branch
in the exact built consumers. The last group changes active device creation,
shared AP_DMA clock ownership, the keyboard GPIO expander, and an established
serviceability contract.

Prior independent runtime evidence attributes the surviving AP_DMA reference
to `1101c000.i2c`. The runtime-proven Stage-27 control shows successful MTU3,
I2C5, watchdog, AW9523, and polling-keyboard probes in that order. Its AW9523
node has no parent IRQ; the matrix driver first defers, then binds after the
GPIO provider appears.

An offline prototype matches the positive control's complete property
inventories on `/i2c@1101c000`, its AW9523 child, and `/keyboard-matrix`, while
preserving the stopped predecessor everywhere else. Its 27,083-byte DTB has
SHA-256
`a6b76ffc352e818d90709712a372c583ee275baf5f06ebf2cd11f593022b429c`.

Two derivations reproduced that DTB and two independent assemblies reproduced
the exact raw and padded containers. The raw Android-v0 image has SHA-256
`e115127db5b4e2bbcf8e5fa12ebf5f8da88f8e87c76712605181160fa7b6917c`;
the exact 16 MiB boot2 payload has SHA-256
`8d04c2c7e9c67dcd17189422d1968e416eb9eec304e2b9300b83f48dc9e0ebb5`.
Independent validation passed all 32 inherited LK/container gates, the exact
manifest and package provenance, SCP and watchdog closure, and the complete
I2C5/AW9523/polling-keyboard contract. Five separate serviceability mutations
were rejected. The guarded installer also passed syntax, ShellCheck, and its
derived help gate without device access.

Guarded deployment resolved logical `boot2` as `/dev/mmcblk0p30`, inactive and
unmounted while Gemian used `/dev/mmcblk0p29`. External power, 100% capacity,
and writable 16 MiB target gates passed. The installer recorded the stopped
watchdog candidate as predecessor, made no fresh backup, wrote and flushed the
exact payload, and fully read back the same SHA-256. It then requested clean
poweroff and confirmed the device unreachable without an automatic reboot.

The first post-deployment observer window was armed against the exact payload
and deployment Gemian boot ID, but no USB topology transition, exact mainline
interface, changed Gemian return, or physical-selection report occurred. It was
stopped and archived as a no-attempt window. This is not kernel evidence, does
not consume the candidate's single attempt, and does not change its installed,
untested disposition.

The fresh second observer window covered the physical attempt itself.
Preloader enumerated at 19:01:58.831 local and detached 2.612 seconds later.
No USB identity appeared before Gemian enumerated at 19:02:12.397 and RNDIS
started. The collector detected a changed Gemian boot ID; authenticated
recovery proved empty pstore, watchdog-block-class reset tokens, active root
p29, and the exact candidate still installed and unmounted on live-GPT boot2
p30.

## Analysis

Enabling only the I2C controller would be an incomplete substitute: it would
not reproduce the known AW9523 transactions, GPIO provider, deferred matrix
bind, or polling-keyboard baseline. Restoring only `status` would also retain
an IRQ contract absent from the positive control. The selected coherent group
is broader but more attributable to the actual serviceability milestone.

The runtime result rejects the complete group as sufficient. Because I2C5,
AW9523, and the keyboard all probe after MTU3 in the positive control, their
absence was already unable to explain a failure before MTU3. Restoring them
also produced no earlier mainline identity. The watchdog-class Gemian token is
consistent with the bounded fallback timing but is not unique to watchdog
expiry, and no mainline probe or pstore evidence identifies the exact reset
source. Incremental DT-property chipping has now exhausted the selected active
groups without crossing the observation boundary.

## Conclusion

Restoring the complete I2C5/AW9523/polling-keyboard group is not sufficient for
current-mainline serviceability. The attempt showed preloader but no mainline
USB identity before a changed Gemian return; pstore was empty and boot2
remained exact. This candidate is stopped. CPU8 and CPU9 remain closed.

## Follow-up

Stop incremental DT-property derivatives. Reassess the post-LK final-DTB and
pre-mainline-USB observation boundary offline, then choose an independent
decision-changing path that distinguishes loader handoff, Image entry, and
early watchdog expiry. The ordered action is maintained in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
