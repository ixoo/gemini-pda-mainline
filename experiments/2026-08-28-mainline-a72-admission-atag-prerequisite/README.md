# Experiment: restore the ATAG identity prerequisite for CPU8 admission

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-atag-prerequisite` |
| Status | `exact candidate independently validated; deployment pending` |
| Subsystem | MT6797 NVMEM, DVFSP handoff, I2C6, and A72 admission |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 7, first attributable CPU8 request |

## Question or hypothesis

Does adding only the already-established built-in ATAG devinfo NVMEM provider
restore the prerequisite binding chain that stopped the first serviceable
one-shot before its admission core?

The predecessor returned exact `-EPROBE_DEFER` with the core unconsumed and
zero CPU requests. Read-only evidence showed an empty NVMEM bus and unbound
ATAG provider; DVFSP handoff explicitly waited for
`/firmware/atag-devinfo/cpu-efuse-identity@58`, followed by deferred I2C6,
clock backend, and A72 binder. The fetched and running configs both omitted
`CONFIG_NVMEM_MTK_ATAG_DEVINFO`.

## Provenance and environment

- Predecessor runtime evidence: signed commit `f65b3f60`, exact candidate
  `f4cb1b2c...`, release `7.1.3-gemini-a72-admission-live`, boot ID
  `21bb6547...`.
- Previous fetched kernel config: private ignored package config
  `265f610b...`; it contains neither `CONFIG_NVMEM=y` nor
  `CONFIG_NVMEM_MTK_ATAG_DEVINFO=y`.
- The read-only provider and CPU identity-cell implementations already exist
  in canonical patches `0057a` and `0237`; no kernel source or DT change is
  introduced here.
- The isolated profile gains one named fragment containing exactly
  `CONFIG_NVMEM=y` and `CONFIG_NVMEM_MTK_ATAG_DEVINFO=y`.
- Build only through `./scripts/build-kernel --backend buildbox`; native VM
  builds are forbidden unless the owner explicitly asks for one.
- Signed definition commit `296ce7f4` built successfully on Buildbox as
  `7.1.3-gemini-a72-admission-live`. Its fetched config is `9b9118fd...` and
  contains both required NVMEM built-ins.

## Safety assessment

Both options expose LK's retained devinfo payload through a read-only NVMEM
provider. The provider maps no efuse MMIO and has no register-write callback.
This definition adds no trigger, CPU request, CPU_OFF, retry, reset, firmware,
partition, regulator, or storage action.

A built image is not yet a boot candidate. After Buildbox compilation, the
package, configuration, restored serviceability DT, LK container, padding, and
full candidate must pass their existing exact gates before boot2 deployment.
The next boot must remain pre-trigger and prove the complete provider graph
bound over exact USB/netcat. The consumed predecessor must never be retried.

## Associated code

- `configs/gemini-a72-admission-atag-prerequisite.fragment`: two-option
  config-only repair.
- `kernel/manifest.json`: pins the new fragment in the existing isolated
  live-trigger candidate profile.
- `scripts/validate-definition.py`: checks the exact profile/config/source and
  no-action boundary.
- `results/prebuild-definition-20260828.txt`: sanitized source decision.
- `scripts/build-candidate.sh`: source-pins the prior serviceability assembler
  and substitutes only the exact Buildbox kernel package.
- `scripts/validate-candidate.py`: independently checks inputs, NVMEM options,
  Android-v0 layout, LK gates, padding, and negative mutations.
- `results/build-and-candidate-20260828.txt`: sanitized exact build and
  candidate receipt.

Private fetched packages and runtime captures remain below ignored
`artifacts/`.

## Procedure

1. Validate that the prior fetched config omits both required built-ins and
   that the predecessor runtime reports the exact deferred supplier chain.
2. Require the new fragment to contain only the two built-in NVMEM options and
   occur once in the live-trigger candidate profile.
3. Require canonical patches `0057a` and `0237` to precede the admission
   patches and provide the read-only driver plus exact identity cell.
4. Commit and push a clean definition, then compile the exact commit on
   Buildbox and fetch only its validated package.
5. Assemble and independently validate a distinct full boot2 candidate using
   the established serviceability transform; publish it before installation.
6. On its first boot, perform read-only pre-trigger qualification. Require the
   ATAG NVMEM device, handoff, I2C6/DA921x provider, clock backend, BigiDVFS,
   platform-state source, binder, controller, exact CPUs, and USB path all
   serviceable. Do not send a CPU8 token during that qualification.

## Observations

The predecessor's kernel and DT were sufficiently alive for exact USB/netcat,
controller status, sysfs bindings, `/proc/config.gz`, and dmesg. The owner saw
no working console framebuffer; that remains a contextual display limitation,
not a boot-health oracle. The direct link proved the missing configuration
without another device action.

The prior package config contains only `CONFIG_NVMEM_REBOOT_MODE=m` in the
NVMEM namespace. The new fragment adds the two missing built-ins and no other
setting. Its driver is the existing read-only ATAG parser, and the identity cell
is already present in the exact admission DT. The whole-manifest invariant
audit accepts all 156 profiles, and its self-test rejects all eight mutations.

Buildbox compiled exact signed commit `296ce7f4`, including
`drivers/nvmem/mediatek-atag-devinfo.o`; no native VM build ran. The fetched
package passed its complete checksum manifest. Two independent container
constructions agree on raw candidate `6971ee82...` and boot2-sized candidate
`fd611a4c...`. The independent validator accepts all 32 LK gates, rejects six
container corruptions, and confirms the exact two NVMEM built-ins, unchanged
serviceability DT `1478f2c8...`, unchanged ramdisk `e0dffa04...`, and zero CPU
requests.

The owner reports that the currently running predecessor boot has no visibly
working console framebuffer. Exact USB/netcat remains live and is the control
and attribution channel, so this is recorded as a framebuffer limitation, not
as a boot failure or a framebuffer-support result.

## Analysis

This is a narrower successor than adding more admission logging or repeating
the consumed trigger. It repairs the first named dependency in the live defer
chain while preserving the kernel source, DT graph, one-shot semantics, and
serviceability transform. A pre-trigger binding pass will distinguish a fixed
prerequisite graph from any later CPU8 transaction result without consuming a
token.

## Conclusion

The config-only successor is now an exact independently validated boot2
candidate. No hardware-support claim or CPU8 result follows from offline
validation alone.

## Follow-up

Publish this candidate, install exact `fd611a4c...` to inactive live-GPT
`boot2`, verify its full-partition readback, and shut down. On its first boot,
perform only read-only netcat qualification. If that proves the entire supplier
graph bound, publish a separate one-shot contract before one new CPU8 request.
If any link remains unbound, stop without triggering and use that specific
binding failure as the next decision point.
