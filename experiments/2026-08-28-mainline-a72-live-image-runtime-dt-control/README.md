# Experiment: current Image with runtime-proven A72 DT control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-live-image-runtime-dt-control` |
| Status | `offline complete; candidate validated, deployment pending` |
| Subsystem | MT6797 A72 DT population and pre-trigger serviceability |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 7 isolation control |

## Question or hypothesis

Does the exact current production `Image.gz` reach the established USB/netcat
service when paired with the closest byte-exact runtime-proven A72 DTB instead
of the later admission-controller DT population?

The prior candidate `4e0f8688...` returned to Gemian before USB and before its
dormant trigger ran. Deferring the action therefore did not restore
serviceability, but that attempt did not distinguish the current Image/config
from the later DT/probe population.

## Provenance and environment

- Current kernel: clean Buildbox commit `c147e2dd...`, profile
  `a72-admission-live-trigger-candidate`, release
  `7.1.3-gemini-a72-admission-live`, `Image.gz` `4b884c01...`.
- Control DTB: `90cfc29b...`, extracted at its exact validated LK boundary from
  candidate `6219357a...`. That candidate was hardware-serviceable with CPUs
  0--7 online, CPUs 8--9 offline, one platform/provider/protected-clock
  observation, zero I2C writes, and zero CPU requests.
- Initramfs: unchanged serviceability ramdisk `e0dffa04...`.
- Boot path: Android-v0 LK container on inactive logical `boot2` only.
- No kernel build is required: this is a deterministic re-container of an
  already fetched and validated Buildbox package. No native VM build is used.

## Safety assessment

The control DT has one platform-state node and one composed
platform/provider/clock observer, but no admission-controller or binder node.
Although the current Image contains the dormant trigger implementation, no DT
device can bind it and no runtime tool writes a trigger. The candidate has zero
CPU8/CPU9, CPU_OFF, retry, storage, retained-RAM, regulator, clock-action,
secure-call, owner-mutation, or reboot requests.

Deployment uses the standing-authorized installer: live GPT resolution of
inactive `boot2`, exact predecessor, stable power, full-partition readback, no
fresh backup, and clean shutdown. Primary `boot`, `boot3`, GPT, preloader,
NVRAM, firmware, and the active root remain excluded.

## Associated code

- `scripts/extract-control-dtb.sh`: exact source-container, offset, length, and
  digest extraction oracle.
- `scripts/build-candidate.sh`: two independent container and padding paths.
- `scripts/validate-candidate.py`: independent layout, identity, DT, and six
  negative mutation checks.
- `scripts/install-boot2.sh`: source-pinned guarded installer and shutdown.
- `scripts/collect-runtime.sh`, `remote-probe.sh`, and
  `validate-runtime.py`: pre-armed exact-MAC read-only USB observation.

Private candidates and captures remain below ignored `artifacts/` paths.

## Procedure

1. Reproduce and verify DTB `90cfc29b...` from runtime-proven candidate
   `6219357a...`.
2. Validate the current fetched package and assemble two byte-identical LK
   containers and boot2 padding images.
3. Independently validate all 32 LK gates, exact payload identities, DT node
   boundary, and negative mutations.
4. Publish the definition and offline evidence.
5. Install exact padded candidate `c2b85cad...` over exact retired predecessor
   `4e0f8688...`, verify its full readback, and shut Gemian down.
6. Arm the collector before one boot2 selection and classify the result.

## Observations

Offline assembly produces raw container `35d0c6ef...` and exact 16 MiB
candidate `c2b85cad...`. Independent assembly and padding paths are
byte-identical; all 32 LK gates and six corrupt-container mutations pass. The
DT has the exact proven platform-state and composed-observer compatibles and no
admission-controller or binder compatible.

## Analysis

This is a decision-bearing cross, not an identical retry. It changes only the
DTB relative to the retired live-trigger artifact while retaining the current
Image/config, boot addresses, command line, and serviceability ramdisk.

If USB serviceability returns, the regression is in the post-`90cfc29b` DT
population or its automatic probes. If it does not, the current Image/config
delta is sufficient and further DT partitioning is not justified.

## Conclusion

Offline candidate construction is confirmed for the exact inputs. Hardware
serviceability remains pending one physical selection.

## Follow-up

The ordered next action and decision branches are owned by
[`docs/ROADMAP.md`](../../docs/ROADMAP.md#7-bring-up-cpu8).
