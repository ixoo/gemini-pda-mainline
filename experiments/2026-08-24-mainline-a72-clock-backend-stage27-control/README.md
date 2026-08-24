# Experiment: A72 clock-backend probe on the passed Stage-27 platform DT

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-a72-clock-backend-stage27-control` |
| Status | `ready for one boot` — offline validation passed |
| Subsystem | MT6797 DVFSP clock backend and A72 platform-state composition |
| Device variant | Gemini PDA, named project device |
| Date | 2026-08-24 |
| Boot path | retained LK, owner-selected non-primary `boot2` |

## Question or hypothesis

Does the exact passed Stage-27 plus A72 platform-state serviceability baseline
remain usable when only the clock backend's read-free probe/resource contract
is added?

The immediately preceding exact runtime proved that the platform-state source
binds on the Stage-27 DT while USB, T-PHY, I2C5, keyboard, and CPU0--7 remain
serviceable. This successor keeps that kernel, ramdisk, and complete DT state
and adds one enabled clock-backend node.

Patch `0335` is already built into this kernel. At probe it performs one managed
allocation, maps only the disjoint MCUMIXED resource, resolves the already-bound
DVFSP handoff supplier, and obtains the I2C_APPM clock handle without enabling
it. It initializes only software state and driver data. The clock-snapshot
function exists but has no caller in this candidate.

## Provenance and exact delta

- Buildbox package commit:
  `26274db63316bbb24eeb9bfa8de21759da666b9e`.
- Kernel release: `7.1.3-gemini-a72-early`.
- `Image.gz` SHA-256:
  `00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293`.
- Exact passed Stage-27 plus platform-state source DTB SHA-256:
  `57e11e4392edfdb9fa695ac3f87b82aad4043bc2a61b78646bf97344bae101fd`.
- Derived clock-backend DTB SHA-256:
  `5f5cd8b8af73cc1ae77887bb5761b8f1cc6b62e7028a6da24d6f9a3d0f22ab4f`.
- Exact serviceability initramfs SHA-256:
  `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f`.
- Raw Android-v0 candidate SHA-256:
  `2ec5bd0751b71ba250a0b0e0e6d519d32375d6c445cc51a514d452fac51c995c`,
  6,909,952 bytes.
- Exact 16 MiB `boot2` payload SHA-256:
  `4c5276ecf3fe60d7df55fd1fe44235432fcd928d2174704e5928bae7d84056e4`.

The sole DT delta is `/dvfsp-clock-backend@1001a000` with:

- compatible `mediatek,mt6797-dvfsp-clock-backend`;
- only the `0x1001a000--0x1001afff` MCUMIXED resource;
- the existing I2C_APPM clock handle;
- the existing handoff provider as its access controller; and
- status `okay`.

Removing that node recovers a byte-identical sorted semantic DTS to the exact
passed predecessor. The existing handoff and platform-state nodes plus the
Stage-27 USB controller, T-PHY and primary PHY, I2C5, AW9523, keyboard,
framebuffer, and disabled SCP state are independently gated.

## Safety assessment

CPU8 and CPU9 remain closed by exact `maxcpus=8`. No BigiDVFS backend or
physical observer is present. Probe performs zero MMIO reads, MMIO writes,
clock enables, protected calls, platform snapshots, provider transactions,
BigiDVFS calls, publications, owner mutations, or CPU requests. The runtime
probe is read-only and requests no reboot.

The already authorized installer resolves logical `boot2` from the live GPT,
rejects an active, mounted, ambiguous, wrong-sized, or unwritable target,
checks power and both exact TEE identities, records the predecessor checksum,
creates no redundant backup, writes only the exact 16 MiB candidate, flushes,
requires a matching full-partition readback, and shuts the device down after
success. Primary `boot`, `boot3`, preloader, NVRAM, GPT, and whole-device
writes remain excluded.

## Associated code and procedure

- `scripts/build-clock-dtb.sh` derives the DT twice and proves the reversible
  one-node semantic delta.
- `scripts/build-candidate.sh` performs two independent Android-v0 assemblies
  and two independent padding constructions.
- `scripts/validate-candidate.sh` independently validates package, DT, layout,
  all 32 LK gates, and six negative mutations.
- `scripts/install-boot2.sh` is the source-pinned guarded live-GPT installer.
- `scripts/collect-runtime.sh` pre-arms the USB/netcat observer and leaves a
  successful mainline boot running.
- `scripts/remote-live-probe.sh`, `scripts/validate-runtime.py`, and
  `scripts/test-runtime.py` collect and classify exact live identity,
  platform/provider bind state, clock-backend bind state, serviceability DT
  state, CPU state, and prohibited effects.

Private candidates and device captures remain below ignored `artifacts/`.
The offline result is recorded in
[`results/offline-candidate-validation-20260824.txt`](results/offline-candidate-validation-20260824.txt).

## Pre-boot decision map

| Unique result | Interpretation | Next action |
| --- | --- | --- |
| Exact USB/netcat identity, Stage-27 state exact, platform state bound, clock backend bound | The cumulative read-free resource probes are serviceable | Define the minimum BigiDVFS-backend probe contract next; still perform no read or CPU request |
| Exact USB/netcat identity, Stage-27 state exact, platform state bound, clock backend unbound | Kernel remains serviceable; the clock resource/bind contract failed | Capture bounded bind status and repair only that contract |
| Changed-ID Gemian before exact mainline identity | The new clock node/probe boundary is implicated but no read or CPU action is attributable | Add an earlier durable clock probe-entry/completion discriminator; do not repeat this payload unchanged |
| Neither exact live mainline nor changed-ID Gemian | Observation incomplete | Preserve state and diagnose transport/boot selection without assigning a kernel result |

Only one owner-selected `boot2` attempt is permitted. After any attributable
result, the exact payload is retired; an identical retry is prohibited unless
it adds a decision-changing independent observation path.

## Offline observations

The DT derives twice byte-identically, its reverse proof recovers the exact
passed predecessor semantic tree, the raw and padded candidates reproduce
byte-identically, all 32 LK gates pass, and all six container mutations are
rejected. The runtime classifier accepts the clock-bound and clock-unbound
serviceable branches and rejects twelve isolation, serviceability, and
prohibited-action mutations.

No new kernel build was required: the exact Buildbox package already contains
the read-free clock backend. No device was accessed and no hardware was written
during construction or offline validation.
