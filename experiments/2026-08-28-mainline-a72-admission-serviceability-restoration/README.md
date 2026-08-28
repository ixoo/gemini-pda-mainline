# Experiment: restore serviceability to the full CPU8 admission DT

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-serviceability-restoration` |
| Status | `runtime PASS; exact controller armed with zero execution` |
| Subsystem | MT6797 USB, keyboard, DVFSP handoff, dormant CPU8 controller |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 7, serviceability prerequisite |

## Question or hypothesis

Does restoring the exact previously proven serviceability transformation to
the full current admission DT allow its controller and binder to reach the
inert `armed` state with zero trigger executions and zero CPU requests?

The current-Image/runtime-DT control proved exact current Image/config
serviceable. Semantic comparison then found that the full admission package DT
explicitly disabled the USB controller and PHY, I2C5/AW9523, and matrix
keyboard that previous A72 candidate builders had restored. The full candidate
builder had used the raw package DT directly and silently omitted that required
transformation.

## Provenance and environment

- Exact current Buildbox package: commit `c147e2dd...`, profile
  `a72-admission-live-trigger-candidate`, release
  `7.1.3-gemini-a72-admission-live`, `Image.gz` `4b884c01...`.
- Raw full admission DT: `1bd6ce2d...`.
- Source-pinned serviceability transformer: the hardware-proven current-tree
  builder at `550527d8...`.
- Restored full admission DT: `1478f2c8...`; it retains one controller, one
  binder, platform state, clock backend, BigiDVFS backend, calibration inputs,
  resource owner, and every unrelated current DT input.
- Initramfs: unchanged serviceability ramdisk `e0dffa04...`.
- No kernel build is required or performed; no native VM build is used.

## Safety assessment

The live-trigger implementation remains default-off until the exact root-only
token is written. This experiment never writes that token. Controller probe is
required to expose an `armed` status with zero trigger executions, supplier
resolution, core consumption, and CPU requests. CPU9, CPU_OFF, retry, storage,
retained-RAM, regulator action, secure call, and reboot requests remain zero.

The serviceability transformation itself is already hardware-proven. It
enables peripheral USB and the polling-keyboard contract, restores the three
read-only handoff windows, adds a disabled SCP input node, and removes the
unused watchdog IRQ description. It does not enable xHCI, ram-console, a CPU,
or a write-bearing power action.

Any boot2 installation uses live GPT resolution, exact predecessor, stable
power, full-partition readback, no fresh backup, and clean shutdown. Primary
boot, boot3, GPT, preloader, NVRAM, firmware, and active root remain excluded.

## Associated code

- `scripts/build-serviceability-dtb.sh`: source-pinned exact DT transform.
- `scripts/build-candidate.sh`: two independent LK container/padding paths.
- `scripts/validate-candidate.py`: independent payload, serviceability-node,
  controller/binder, LK, and mutation validation.
- `scripts/install-boot2.sh`: source-pinned guarded boot2 installer.
- `scripts/remote-pretrigger.sh`, `validate-pretrigger.py`, and
  `collect-pretrigger.sh`: exact-MAC read-only armed-state capture with no
  trigger session.

Private DTBs, candidates, and runtime captures remain below ignored
`artifacts/` paths.

## Procedure

1. Audit exact DT `90cfc29b...` against raw admission DT `1bd6ce2d...`.
2. Apply the source-pinned serviceability transform twice and require exact
   output `1478f2c8...` while preserving the admission nodes/backends.
3. Re-container exact current `Image.gz`, restored DT, and unchanged ramdisk
   twice; require byte-identical raw and padded images.
4. Independently validate 32 LK gates, six corrupt-container mutations, every
   serviceability node, and controller/binder presence.
5. Publish the definition before device access.
6. Return the currently serviceable control boot to Gemian through its USB
   shell, install only exact candidate `f4cb1b2c...`, verify full readback, and
   shut down.
7. Arm the pre-trigger-only collector before one boot2 selection. Accept only
   exact `armed`, zero-execution status and leave the successful boot running.

## Observations

The raw admission DT has `status = "disabled"` on `/usb@11271000`,
`/t-phy@11290000`, its `usb-phy@11290800`, `/i2c@1101c000`, AW9523, and the
matrix keyboard. The exact source-pinned transformer changes only its bounded
20-property/one-disabled-node serviceability contract and produces DT
`1478f2c8...` twice.

The resulting DT retains one admission controller and one binder, with the
platform, clock, and BigiDVFS backends enabled. Two LK assemblies produce raw
container `b1ff92e8...`; two padding paths produce exact 16 MiB candidate
`f4cb1b2c...`. All 32 LK gates and six negative mutations pass. No device was
accessed and no kernel was built.

After publishing signed definition commit `a2282470`, the proven control boot
returned to changed-ID Gemian through the exact USB reboot wrapper. The guarded
installer resolved inactive live-GPT `boot2` as `/dev/mmcblk0p30` while root
remained `/dev/mmcblk0p29`, matched predecessor `c2b85cad...`, and wrote exact
candidate `f4cb1b2c...`. The full-partition readback matched. Stable external
power, unchanged TEE identities, no fresh backup, no retained-RAM write during
installation, and clean shutdown with three closed TCP/22 checks are recorded
in the deployment result.

The pre-armed collector then accepted the exact Gemini USB interface on its
first netcat connection. Mainline boot ID `21bb6547...` reported the exact
installed candidate and release, CPU0--7 online with CPU8--9 offline, zero
block mounts, one bound admission controller, and the read-only status/root-
write-only trigger group. Status was exactly `armed`: zero trigger executions,
supplier resolutions, core consumptions, CPU requests, CPU9 requests,
CPU_OFF requests, or retries. The collector opened no trigger session, sent no
write, requested no reboot, and left the successful boot running.

## Analysis

This repairs a candidate-construction regression rather than weakening the
CPU8 transaction. The prior full artifact could not expose its dormant trigger
over USB because the raw package DT disabled that USB path. Exact current Image
serviceability with the proven DT rules out an Image/config failure, and the
positive armed-state runtime now proves the full admission population can
remain inert and serviceable when the omitted baseline transformation is
restored.

## Conclusion

Offline construction, guarded deployment, and runtime controller
serviceability are confirmed. This experiment sent no CPU8 trigger and left
the exact successful mainline boot running.

## Follow-up

Retain DT `1478f2c8...` as the corrected baseline. Define and publish a distinct
follow-up that revalidates this same boot's exact armed state, durably records
intent, and invokes the already hardware-free-proven one-shot CPU8 trigger once
with no retry.
