# Experiment: LK CPU clock-frequency iterator repair

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-17-mainline-lk-cpu-clock-iterator-repair` |
| Status | exact candidate validated offline; one guarded attempt pending |
| Subsystem | Planet/MediaTek LK final-DTB CPU filtering before Linux entry |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-17 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline handoff prerequisite to CPU8 work |

## Question or hypothesis

Do the ten exact Stage-27 `clock-frequency` properties let the installed LK
CPU filter finish and reach the unchanged arm64 Image? The immediately stopped
I2C5 candidate is unchanged except for this one coherent metadata group.

The pinned Planet LK source calls `target_fdt_cpus()` before kernel
decompression and final handoff. Its loop advances `last_node` only after an
active CPU supplies `clock-frequency`. The stopped DT's first child,
`cpu@0`, lacks that property, so the `continue` path selects the first child
again. This is a concrete pre-Linux non-progress mechanism, not another
kernel-probe guess.

## Provenance and environment

- Pinned public LK source commit:
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
- Audited `lk/platform/mt6797/atags.c` SHA-256:
  `2085ee837776586a86c1e03504f3220ee7dc2bedf46934729c9042d3702bcb87`.
- Audited `lk/app/mt_boot/mt_boot.c` SHA-256:
  `9380b89d367770acf29f1c5b7f4856cc87bc4b64afd17aa9fa1fd621c213ecda`.
- Live `lk` and `lk2` match the project-start loader capture, SHA-256
  `75ec9f0ba97af9e68d964b304e0de809f9b4546982570bd16b2e7fe88823282c`.
  The installed image contains the expected CPU-filter and final-jump strings.
  Source/binary behavioral equivalence is a high-confidence inference, not a
  symbolized byte-level proof.
- Exact kernel package remains repository commit
  `98996fdfbf09f8de2a6b86e488defef22fcc7968`, release
  `7.1.3-gemini-entryled-a`.
- No kernel compilation is needed. No native VM build is permitted or run.

## Safety assessment

The ten properties are CPU frequency metadata already present in the
runtime-proven Stage-27 control. They do not request CPU bring-up. CPU8 and
CPU9 remain closed by the unchanged kernel configuration, command line, and
admission instrumentation.

The predecessor's established I2C5/AW9523/polling-keyboard serviceability
group remains present, so its previously reviewed bounded probe and keyboard
transactions remain the only expected runtime register-data writes. SCP stays
disabled, the watchdog IRQ stays absent, USB stays peripheral, xHCI stays
disabled, and the DA921x/I2C6 write closure is unchanged.

Any installation is limited to the standing logical-`boot2` policy, exact
live-GPT resolution, full-partition readback, and clean shutdown. No fresh
partition backup is made.

## Associated code

- `scripts/build-lk-cpu-clock-dtb.sh`: source-pinned derivation that adds the
  exact ten Stage-27 values and validates all ten CPU property inventories.
- `scripts/build-candidate.sh`: deterministic Android-v0 assembly around the
  unchanged kernel and initramfs.
- `scripts/test-candidate.py`: independent container, serviceability, CPU
  metadata, provenance, and negative-mutation validation.
- `scripts/install-boot2.sh`: source-pinned guarded logical-`boot2` installer.
- `results/lk-cpu-clock-iterator-boundary-20260817.txt`: loader flow, exact
  non-progress mechanism, installed-loader correlation, and selection.
- `results/offline-candidate-validation-20260817.txt`: immutable identities and
  completed offline gates.
- `results/predeployment-hypothesis-20260817.txt`: unique observation and
  decision map for the one candidate attempt.

Generated candidates remain below the ignored `artifacts/` tree.

## Procedure

1. Audit the pinned LK path from appended DT selection through final jump.
2. Correlate the public source with the exact installed `lk`/`lk2` identities
   and strings, preserving the source/binary equivalence limit.
3. Derive the stopped I2C5 DT twice and add only the ten exact Stage-27 CPU
   clock properties.
4. Assemble twice, validate the Android-v0 container, and reject independent
   container, serviceability, and CPU-clock mutations.
5. Publish the exact definition before a guarded write. Arm a fresh observer
   before the physical `boot2` selection.

## Observations

Each tested current-DT derivative contains exactly one appended FDT magic at
file offset 4,777,447. The project-start GPT inventory contains no `odmdtbo`
partition, so the optional overlay load cannot explain a later mutation.

The LK loop starts at `/cpus/cpu@0`. All ten CPU nodes in the stopped I2C5 DT
lack `clock-frequency`. On the missing-property path the loop executes
`continue` before updating `last_node`; its update expression therefore calls
`fdt_first_subnode()` again. The runtime-proven Stage-27 DT supplies all ten
properties and has the same per-node property inventories after the repair.

Two independent derivations produced a 27,243-byte DTB with SHA-256
`a87558efd982007798b1c706b4df9e8048b71954423d45bbaf5fbe32515e2f14`.
Two independent assemblies produced raw SHA-256
`fe22ae352abcaf72ed2f456e6946b462c4a343589698685244ef9b3b6333e9f1`
and the exact 16 MiB boot2 payload SHA-256
`b478b79a983889514b2b8d122fb6d5ff5057e52c332882b186b82698d1de62b8`.

## Analysis

This boundary supersedes the earlier conclusion that the CPU clock
differences were passive to the built kernel. They are passive to Linux's
early admission decision but active inputs to the preceding LK CPU filter.
That distinction was missed while the investigation ranked only kernel
consumers.

Adding all ten properties is one semantic group because LK iterates every CPU
node, and a missing property at any retained CPU can trigger the same
non-progress path. The values and property inventories come from the exact
positive control rather than an inferred frequency policy.

## Conclusion

The exact stopped candidates have a credible loader-side infinite-loop
mechanism before Image entry. The clocks-only repair is the first candidate
that directly removes that mechanism while holding the kernel, initramfs,
serviceability baseline, and CPU8/9 closure fixed. Offline validation passes;
runtime classification remains pending.

## Follow-up

Publish the definition, install the exact payload once to live-GPT-resolved
inactive `boot2`, require matching full readback and clean shutdown, then arm
a fresh USB/netcat observer immediately before the owner selects `boot2`.
The ordered action is maintained in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
