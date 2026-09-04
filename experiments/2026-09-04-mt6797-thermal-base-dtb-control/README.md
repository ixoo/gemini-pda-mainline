# Experiment: MT6797 thermal base-DT serviceability control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-thermal-base-dtb-control` |
| Status | completed; attempted control invalidated because its DT disabled the required USB observation channel |
| Subsystem | appended DT discrimination before MT6797 thermal runtime |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-04 |
| Tracking goal | restore attributable thermal observability before longer CPU8/CPU9 load |

## Hypothesis

The exact thermal-stage-ledger Image, configuration, initramfs, LK container
contract, command line, and addresses remain serviceable when only the appended
DT is changed from the thermal-serviceability DT to the exact base Gemini DT
from the same Buildbox package.  Positive USB/netcat runtime identity would
attribute the two prior pre-transport returns to the thermal DT delta or probes
it induces, rather than to this Image/configuration/container.

The base DT keeps both the MT6797 thermal controller and standalone AUXADC
consumer disabled and has no thermal zone. Its ordinary Gemini model also
causes the exact-model thermal-ledger guard to refuse ownership. Subsequent
exact DT comparison found that it also disables the USB controller and PHY and
keyboard and lacks the proven simple framebuffer. It was therefore incapable
of serving as the intended positive USB control.

## Exact inputs

- Published Buildbox commit: `b66b03c722cd67584fb8fb15de493ebb084954b4`.
- Release: `7.1.3-gemini-mt6797-thermal-stage-ledger`.
- `Image.gz`: `3e1ebb8de1aeb9ff1c6c6cbe655f18d1affd751959967bfd85507d280dedd2a2`.
- Base `mt6797-gemini-pda.dtb`:
  `d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc`.
- Unchanged serviceability initramfs:
  `344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b`.
- Selected raw Android-v0 image:
  `fb660f34d631109eeeaa5625c457e141ff0beadafbdbf47375f11d11ca9e449d`,
  7,557,120 bytes.
- Selected exact 16 MiB `boot2` payload:
  `ec26245757291c4d7761683b7afc8042cc8bf98fd34a4c977946cf23a5147db5`.

No kernel build is needed: the experiment reuses the fetched, validated exact
Buildbox package and recontainers it deterministically with a different DT
already present in that package.  No native VM build is permitted or used.

## Safety and exclusions

The runtime observation is read-only.  It issues no CPU request, load,
cpufreq/OPP, thermal read, hotplug, idle, suspend, retained-RAM write, native
reboot, or device-storage operation.  CPU8 and CPU9 remain offline.

Deployment is limited to the standing-authorized, live-GPT-resolved inactive
logical `boot2`.  The installer refuses active, mounted, held, wrong-size,
read-only, underpowered, unpublished, dirty, or wrong-checksum state; skips an
already matching partition; otherwise writes once, flushes, requires a full
partition readback, and shuts the device down.  The project-start backup is the
recovery source and no fresh backup is created.  Primary `boot`, `boot3`, GPT,
preloader, NVRAM, and every other partition remain excluded.

## Procedure

1. Validate the exact published package and base/service DT pair.
2. Assemble the base-DT container twice, require byte identity, independently
   validate every member and the LK container, and reproduce exact padding.
3. Publish the experiment, exact candidate, fixed hypothesis, and result map.
4. Install only the exact padded payload to guarded inactive `boot2`, verify
   full readback, and shut down.
5. Pre-arm one bounded observer and select `boot2` once.  A pass requires the
   exact release, base DT, USB/netcat, CPU0--7, console, PWRAP/MT6351, eMMC,
   disabled thermal/AUXADC, zero zones, and no targeted errors or actions.

## Result map

- Positive exact live frame: attribute the regression to the thermal DT delta;
  split its enabled controller and zone population before another thermal boot.
- Changed-ID Gemian return without a live exact frame: inconclusive; retire the
  control and select a new independent positive observation path.
- Live frame with failed baseline predicate: preserve the frame and repair the
  exact failed serviceability boundary before thermal enablement.

The ordered next action is owned by
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).

## Observations

The exact published package passed its complete 512-patch, configuration,
image, symbol, provenance, and base/service DT validation. Two Android-v0
assemblies were byte-identical; all 32 LK gates passed; the raw and exact-zero-
padded identities reproduced the selected hashes. The read-only classifier
accepted its positive fixture and rejected ten identity, DT, CPU, console,
PWRAP, eMMC, storage, retained-write, and boot-ID mutations. Syntax,
ShellCheck, source-hash pins, live-GPT resolution, one-write limit, no-backup
policy, full-readback requirement, and clean-shutdown path pass offline. No
device or native-build action occurred.

Published commit `d6dcdf6c...` then passed every live install gate. Gemian
resolved inactive logical `boot2` as `/dev/mmcblk0p30`, wrote the exact
`ec262457...` payload over retired `dcb2b4e8...`, synchronized and flushed it,
and produced a matching full-partition readback with stable battery and USB
power. No backup or other partition write occurred. The requested clean
poweroff closed its original SSH session, but TCP/22 remained open and a new
authenticated SSH connection stalled before opening a command channel. The
device is therefore not claimed off. The observer now requires three closed
TCP/22 samples instead of treating an SSH command failure as shutdown, and its
Gemian identity probes have bounded post-authentication liveness. Physical
poweroff was required before the one control boot.

That boot2 selection produced no sampled mainline USB and returned to changed-
ID Gemian `3c428441...`. Read-only recovery confirmed empty pstore and the exact
`ec262457...` payload still on inactive `boot2`. Exact DT comparison then found
the confound: package base DT `d7b58354...` explicitly disables the USB
controller, USB PHY, and keyboard and lacks the runtime-proven simple
framebuffer. The prior thermal-serviceability DT `966351e9...` was derived from
that same base and inherited the disabled observation path. Thus neither recent
no-USB result establishes an Image/configuration failure or a thermal probe
stage. The control is retired as
`inconclusive-observation-channel-disabled-by-control-dt`; the selected
successor derives from the exact runtime-proven PWRAP/USB/eMMC DT and changes
only the thermal properties.
