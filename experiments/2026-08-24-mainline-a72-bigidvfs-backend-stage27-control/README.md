# Experiment: A72 BigiDVFS-backend probe on the passed Stage-27 reader DT

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-a72-bigidvfs-backend-stage27-control` |
| Status | `completed` — exact live three-backend read-free serviceability pass |
| Subsystem | MT6797 BigiDVFS secure-readback backend resource composition |
| Device variant | Gemini PDA, named project device |
| Date | 2026-08-24 |
| Boot path | retained LK, owner-selected non-primary `boot2` |

## Question or hypothesis

Does the exact passed Stage-27 plus platform-state plus clock-backend baseline
remain serviceable when only the BigiDVFS backend's read-free probe contract is
added?

The predecessor exact runtime proved that the platform-state and clock-backend
drivers bind cumulatively while the Stage-27 serviceability state survives.
This successor keeps that kernel, ramdisk, and complete DT state and adds one
enabled BigiDVFS-backend node.

The built-in BigiDVFS probe validates only `method = "smc"`, performs one
managed allocation, initializes one mutex, publishes driver data, and logs
readiness. It has no MMIO, clock, reset, regulator, handoff, or other resource.
The stable two-sample read function exists but has no caller in this candidate;
therefore the secure FID and all eight secure reads remain unreachable.

## Provenance and exact delta

- Buildbox package commit:
  `26274db63316bbb24eeb9bfa8de21759da666b9e`.
- Kernel release: `7.1.3-gemini-a72-early`.
- `Image.gz` SHA-256:
  `00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293`.
- Exact passed Stage-27 plus platform/clock source DTB SHA-256:
  `5f5cd8b8af73cc1ae77887bb5761b8f1cc6b62e7028a6da24d6f9a3d0f22ab4f`.
- Derived BigiDVFS-backend DTB SHA-256:
  `d439ed8f4c226eda49f5bf652f16761ba3400bd0b80685bfc8f8da371d6ed9db`.
- Exact serviceability initramfs SHA-256:
  `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f`.
- Raw Android-v0 candidate SHA-256:
  `2abb81d0ab24dc83c4e1526d0564fdd235db202d0db95a869912e1abb31f30ba`,
  6,909,952 bytes.
- Exact 16 MiB `boot2` payload SHA-256:
  `0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a`.

The sole DT delta is `/dvfsp-bigidvfs-backend` with compatible
`mediatek,mt6797-bigidvfs-backend`, method `smc`, and status `okay`. Removing
that node recovers a byte-identical sorted semantic DTS to the exact passed
predecessor. The existing platform-state and clock-backend nodes plus the
Stage-27 USB controller, T-PHY and primary PHY, I2C5, AW9523, keyboard,
framebuffer, and disabled SCP state are independently gated.

## Safety assessment

CPU8 and CPU9 remain closed by exact `maxcpus=8`. The physical observer is
absent. Probe performs zero MMIO mappings, MMIO reads or writes, clock actions,
secure calls, protected reads, platform snapshots, BigiDVFS samples,
publications, owner mutations, or CPU requests. The runtime probe is read-only
and requests no reboot.

The installer retains the established live-GPT, inactive-target, exact
predecessor, power, TEE, full-readback, cleanup, no-fresh-backup, and clean-
shutdown gates. Primary `boot`, `boot3`, preloader, NVRAM, GPT, and whole-device
writes remain excluded.

## Pre-boot decision map

| Unique result | Interpretation | Next action |
| --- | --- | --- |
| Exact USB/netcat identity, Stage-27 state exact, platform and clock bound, BigiDVFS backend bound | All three cumulative reader probes are serviceable without a read | Audit the physical observer/caller and select the first decision-bearing read boundary |
| Exact identity and serviceability, earlier readers bound, BigiDVFS backend unbound | Kernel remains serviceable; the method/bind contract failed | Capture bounded bind status and repair only that contract |
| Changed-ID Gemian before exact mainline identity | The new BigiDVFS node/probe boundary is implicated but no secure call is attributable | Add an earlier durable BigiDVFS probe-entry/completion discriminator; do not retry unchanged |
| Neither exact live mainline nor changed-ID Gemian | Observation incomplete | Diagnose transport/selection without assigning a kernel result |

Only one owner-selected `boot2` attempt is permitted. After any attributable
result, the exact payload is retired unless a repeat adds a decision-changing
independent observation path.

## Offline observations

The DT derives twice byte-identically, its reverse proof recovers the passed
predecessor semantic tree, the raw and padded candidates reproduce
byte-identically, all 32 LK gates pass, and all six container mutations are
rejected. The runtime classifier accepts the BigiDVFS-bound and unbound
serviceable branches and rejects fourteen isolation, serviceability, and
prohibited-action mutations.

No new kernel build was required: the exact Buildbox package already contains
the backend. The offline definition is published at signed commit `b458a58a`.

The guarded deployment then resolved inactive, unmounted live-GPT `boot2` as
`/dev/mmcblk0p30` while Gemian used `/dev/mmcblk0p29`, matched the exact passed
clock-backend predecessor, verified stable power and both TEE copies, and
wrote, synced, flushed, and matched the complete 16 MiB readback to
`0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a`.
It made no fresh partition backup and no retained-RAM write, removed its
temporary readback, and ended with the requested clean shutdown confirmed by
unreachability. See the [sanitized deployment receipt](results/deployment-20260824.txt).

## Runtime observation and conclusion

The collector was armed before physical selection. Attempt 1 observed two USB
topology changes, resolved the exact Gemini interface as `en7`, and completed
the netcat probe on its first try. Exact live identity was:

- full installed candidate
  `0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a`;
- kernel `7.1.3-gemini-a72-early`, boot ID
  `34730097-51c4-4c93-ae0f-87e257c0d6bc`, and uptime 50.33 seconds;
- CPUs possible/present `0-9`, online `0-7`, offline `8-9`, with one exact
  `maxcpus=8` token;
- one bound platform-state device, one bound clock backend, and one bound
  BigiDVFS backend;
- zero physical-observer devices; and
- exact `okay` status for USB, T-PHY, I2C5, and keyboard.

The runtime probe requested no platform snapshot, protected-clock read,
BigiDVFS read, storage access, binding change, regulator or clock action,
secure call, observer or owner registration, CPU admission, or reboot. Pstore
exposed no file and no early marker; that absence is not used as negative
evidence. The owner's boot report is corroborating only. Mainline was
deliberately left running.

Conclusion: **confirmed** for this exact revision and named device. The
platform-state, clock, and BigiDVFS backends all bind cumulatively without
regressing the Stage-27 serviceability baseline. This proves the complete
read-free reader composition only, not a platform snapshot, protected-clock
read, BigiDVFS SMC, register value, publication, CPU power transition, or
CPU8/CPU9 admission. The exact payload is retired. Sanitized evidence is in
the [runtime receipt](results/runtime-attempt-1-serviceable-20260824.txt).

The predeclared bound branch now applies. Source audit rejects reusing the old
full physical observer as the first read because it performs platform,
DA921x-provider, and protected-clock reads before its first retained
checkpoint. The first independently attributable read boundary is therefore
the stable platform-state snapshot alone; later readers remain excluded.
