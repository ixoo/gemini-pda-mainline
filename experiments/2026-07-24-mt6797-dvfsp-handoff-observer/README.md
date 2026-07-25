# Experiment: observe the MT6797 DVFSP handoff without touching I2C6

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-24-mt6797-dvfsp-handoff-observer` |
| Status | `inconclusive` |
| Runtime validation | `completed on logical boot2; ownership result unknown; I2C6 remains disabled` |
| Subsystem | MT6797 CPU-DVFS firmware, CSPM, infracfg, shared I2C6 ownership |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-24 |
| Investigator(s) | Project maintainers |
| Candidate | `AN` |

## Question or hypothesis

Can one read-only MT6797 DVFSP handoff observer be added to the exact
hardware-passed Candidate AH final device tree while retaining every other AH
node and property exactly, and can its three latched probe-window snapshots
classify the retained firmware state without accessing I2C6?

The runtime hypothesis is that three read-only snapshots of the retained CSPM
and infracfg state at approximately 0, 2, and 20 ms after probe can distinguish
active firmware from a strictly quiescent-stopped probe window. Candidate AN
must not enable I2C6, describe a DA9214, register an A72-power provider, request
CPU8 or CPU9, or write any observed register.

This is the next discriminating step before changing DA9214 support. A
quiescent-stopped result is evidence only for the current boot's probe window.
The one-time latched result is not itself synchronization. Before a later
resource-only experiment selects a narrow legacy-DA9214 variant in the
existing DA9211-family driver, reverse engineering must distinguish a
permanent DVFSP stop/handoff (including who can restart it) from Gemian's
per-transfer `SEMA_I2C_DRV` pause/release path. A proven permanent handoff
requires an in-kernel prerequisite that establishes a race-free invariant
before any I2C6 controller, adapter, or client becomes available. If firmware
can remain or become active, every I2C6 transfer must use verified
controller/SoC-level arbitration. A previous AN boot—or merely re-reading
AN's stale snapshot—does not authorize even a read-only transaction. None of
these results justifies a standalone DA9214 driver.

## Provenance and environment

- Candidate label: `AN`.
- Kernel release: Linux `7.1.3`.
- Kernel profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-`
  `a72-observer-initcall-blacklist-dvfsp-handoff-observer`.
- Patch series: 95 selected entries: corrected `0001` through `0092`
  (including the separately numbered `0057a`), plus `0094` and `0095`;
  `0093` and draft `0096` are absent.
- Patchset SHA-256:
  `021d8dde73db6282db5586573cf25b1eca7001bfdd44351e15089cbcf8c8fbf7`.
- Two independent kernel packages have identical substantive bytes and modes.
  Their only difference is the deliberately excluded generation timestamp and
  its derived package-manifest entry.
- Kernel configuration SHA-256:
  `5c3a9537ce91de3c58039974c5671a091a59cf685b659c7298142751e4294bc5`.
- `Image.gz` SHA-256:
  `ade304261204b328c4c26f99964aa46c9a2456de5e14f1598cf26c6c71684815`.
- Exact hardware-passed Candidate AH final-DT SHA-256:
  `27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845`.
- The reproduced artifact's frozen provenance field
  `functional_baseline=byte-exact-hardware-passed-candidate-ah` is imprecise:
  it means AH's hardware/board contract, not whole-artifact byte identity.
  Candidate AN necessarily has a different observer-enabled kernel. The field
  is retained only to reproduce the already installed bytes; the explicit
  kernel, DT, initramfs, configuration, and patch hashes are authoritative.
- Exact AH final-DT source:
  `artifacts/vm-export-candidate-ah-20260722/boot-candidates/`
  `candidate-AH-container-build1/`
  `candidate-AH-ad-contract-af-kernel-split-e5ba6ee0/`
  `mt6797-gemini-pda-ad-contract-af-kernel-split.dtb`.
- Source-pinned FDT semantic parser SHA-256:
  `444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66`.
- The exact AH infracfg provider is `/syscon@10001000`, phandle `0x3`,
  compatible with `mediatek,mt6797-infracfg` and `syscon`.
- Final Candidate AN DT SHA-256:
  `1a934e999c288459089e33ef19ec2bd2105b1de6cf5d808b08ba4569601a924b`.
- Raw Android-v0 boot image: `7,387,136` bytes, SHA-256
  `b30bd1830ac8b6d01a6d030815969c89239a40a742f008338899925508987933`.
- Artifact manifest SHA-256:
  `5c4210cf657928c8d487fb720ac55ad80bb3b3bfe5afa98018582d2cd667a3e9`.
- Exact zero-padded 16 MiB image SHA-256:
  `1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb`.
- Two independently assembled 18-member artifacts have byte-identical
  contents and identical modes.
- Guarded installer SHA-256:
  `7f86e620aaa2410954ea01d93241d6f8e21f2b94e1811646cbe7f672fa9f052d`.
- Candidate AN was installed from known-good Gemian to the live GPT-resolved
  logical `boot2` on 2026-07-24. The full post-flush remote checksum and a
  separately streamed full local readback both equal the pinned padded hash.
  The installer performed no reboot or slot selection. The owner subsequently
  selected `boot2`, and Candidate AN booted successfully.
- The accepted runtime capture is
  `results/runtime-candidate-an-attempt-2-20260724.txt`, SHA-256
  `6278c99ffe80e2f79541a1313195e58907255ee93f909cb903a7b430c41f8adb`.
- Candidate AN's pre-LK artifact DT remains
  `1a934e999c288459089e33ef19ec2bd2105b1de6cf5d808b08ba4569601a924b`.
  LK expanded the live FDT to 52,547 bytes, SHA-256
  `1ffc67486e68a08da3d946d7fd0bb43d83a92bbc44c7d2fef6c2e77d8c9d4b50`.
  A private whole-tree comparison accepted exactly 37 allowlisted LK handoff
  changes and proved the observer, I2C6, CPU8/CPU9, and forbidden-node
  contracts were unchanged. Device-specific values were validated only by
  shape and were not retained in the repository.

The only permitted final-DT semantic delta is:

```dts
dvfsp-observer@11015000 {
	compatible = "mediatek,mt6797-dvfsp-handoff-observer";
	reg = <0 0x11015000 0 0x1000>;
	mediatek,infracfg = <0x3>;
	status = "okay";
};
```

The `0x3` value is not allocated by this experiment. The builder resolves it
from the exact existing `/syscon@10001000` node, and the validator proves that
the complete global phandle map is unchanged.

## Safety assessment

The build and artifact tooling has no device access. The selected observer is a
diagnostic consumer, not a DVFSP provider. It maps only CSPM
`0x11015000..0x11015fff` and reads the infracfg I2C_APPM gate-status bit through
the existing syscon. It does not map CSRAM, request a DVFSP interrupt, load
firmware, enable a clock, access I2C6, bind a regulator, request CPU8/CPU9, or
write an MMIO/sysfs control. The final DT keeps I2C6 disabled and contains no
DA9214 or A72-power node.

Installation used the source-pinned exact-target helper. It resolved logical
`boot2` from the live GPT, proved it was inactive, unmounted, writable, exactly
16 MiB, and contained the exact readback-verified Candidate AL predecessor.
It required stable USB power and a present, full, healthy battery; preserved a
private mode-0600 full backup; performed one bounded 16 MiB write; synced and
flushed; and required matching remote and local full readbacks. The helper
never reboots or selects a slot.

Compilation, reproduction, and installation are not runtime hardware evidence.
The accepted Candidate AN capture supplies the remote runtime evidence. It
does not independently observe the physical display, a physical keypress, or
execution of the in-kernel reboot path.

## Associated code

- `scripts/candidate_an.py`: source-pinned Candidate AH/AL lineage, exact
  Candidate AN build/artifact identities, and capacity boundary.
- `scripts/build-an-dtb.sh`: deterministic transformation from the exact AH
  final DT to the Candidate AN experimental DT.
- `scripts/validate-dtb-delta.py`: source-pinned, whole-tree semantic
  validator. It also checks the FDT reservation map, boot CPU, global phandle
  map, exact observer resource reference, AH I2C6 boundary, CPU8/CPU9 rejecting
  method, and preserved console, USB, keyboard, and ramoops contracts.
- `scripts/normalize-build-json.py`, `scripts/validate-package.py`,
  `scripts/validate-package-reproduction.py`, and
  `scripts/test-package-validators.py`: exact patch/config/package,
  embedded-config, symbol, DT, compiled-gate, normalized-provenance,
  independent-build, and mutation checks.
- `scripts/build-candidate-an.sh`, `scripts/validate-boot.py`, and
  `scripts/validate-artifact-reproduction.py`: deterministic container
  assembly and two-tree validation.
- `scripts/derive-installer.py` and
  `scripts/test-installer-derivation.py`: source-pinned exact-target logical
  `boot2` installer derivation and mutation/static tests.
- `scripts/collect-runtime.sh`, `scripts/validate-runtime.py`, and
  `scripts/test-runtime-validator.py`: bounded USB runtime capture, independent
  C-equivalent classification, and end-to-end mutation tests.
- `scripts/collect-cycle.sh`, `scripts/derive-cycle-watcher.py`, and
  `scripts/test-cycle-watcher.py`: exact-MAC, one-shot bounded runtime watcher
  and source-pinned derivation tests.
- `scripts/validate-live-fdt-delta.py` and
  `scripts/test-live-fdt-delta.py`: private, whole-tree semantic comparison
  of the exact pre-LK artifact DT and the post-LK live FDT, plus focused
  mutation tests. The validator emits only sanitized structure/identity
  results, never device-specific property values.
- `results/build-install-candidate-an-20260724.txt`: exact build, artifact,
  installation, backup, readback, and runtime decision record.
- `results/da9214-datasheet-crosscheck-20260724.txt`: redistribution-safe
  datasheet/source conclusions; the user-supplied PDF itself is not stored.
- `results/runtime-candidate-an-attempt-1-20260724.txt` and
  `results/runtime-candidate-an-attempt-2-20260724.txt`: inconclusive
  collector-framing attempt and accepted exact runtime capture.
- `results/runtime-candidate-an-validated-20260724.txt`: sanitized accepted
  runtime verdict and decision boundary.

## Procedure

1. Build two clean kernel trees through `./scripts/dev-vm build-kernel` using
   the manifest-selected Candidate AN profile.
2. Validate both packages independently and require identical substantive
   bytes, modes, normalized provenance, config, kernel, symbols, compiled
   fail-closed CPU gate, and package DT.
3. Assemble two containers using independent kernel and exact Candidate AH
   artifact trees. Require identical 18-member artifacts, modes, raw image,
   final DT, and padded identity.
4. Source-pin all calibrated identities and derive the exact-target guarded
   installer. Require its focused tests and Bash syntax check.
5. In known-good Gemian, live-resolve and verify logical `boot2`, active root,
   mount/swap/holder state, size, writable state, power, and exact predecessor.
   Preserve a full private backup, perform the bounded write, flush, and
   require a full remote and independent local readback.
6. The owner selected `boot2`. Candidate AN booted and the USB endpoint became
   reachable. The first capture was tooling-inconclusive because the original
   interactive shell framing contaminated scalar fields; it made no hardware
   change. The collector was changed to one quoted noninteractive BusyBox
   child shell and then re-run once.
7. After more than 45 seconds of the same Candidate AN boot, capture the exact
   three latched snapshots, one classification, complete dmesg, and inherited
   remote contracts. Independently recompute the state and validate the
   post-LK FDT delta privately. **Completed** for attempt 2. A separate
   pstore/native-reboot cycle was not performed.

## Observations

Two independent clean kernel packages and two independently assembled boot
artifacts passed their reproduction gates. Candidate AN was installed to the
live-resolved inactive logical `boot2`; the exact predecessor was backed up,
and the flushed full-partition and independent local readback checksums match
the source-pinned Candidate AN padded identity.

Candidate AN booted successfully from `boot2`; the accepted capture ended at
uptime 260 seconds. The exact kernel, configuration, command line, initramfs,
installed-image attestation, observer binding, and LK-expanded live FDT
passed. CPU0--7 were online and each advanced its accounting sample; CPU8/CPU9
stayed offline and unrequested. The USB development endpoint was usable.
Through the final sample there was no kernel fault, observer error/reprobe,
I2C6 platform device, adapter, client, regulator, DA9214 activity, userspace
watchdog owner, or automatic reboot. The collector performed no device-
partition read.

The three latched observer snapshots had identical measured register payloads;
their `snapshot=0/1/2` labels necessarily differed. Each reported a stopped
timer (`before=after=0`), `PCM_CON1=0x00006c00`,
`PCM_PWR_IO_EN=0`, program counter/register 15 equal to zero,
`PCM_FSM_STA=0x00048490` in reset, and `SW_RSV0..6=0xbabebabe`.
However, `INFRA2_PDN_STA=0x00000000`, so the required I2C_APPM gate-status bit
1 was clear: the shared clock was **ungated**. The driver and an independent
C-equivalent recomputation therefore both returned `unknown`, exactly as the
fail-closed oracle requires.

The first runtime attempt is retained as an inconclusive collector-framing
result. Attempt 2 is the accepted evidence. Its remote console/keyboard checks
prove the inherited simple-framebuffer and keyboard device/keymap contracts,
but not that pixels were visible or that a physical key was pressed in this
cycle. The inherited initramfs still emits the stale text
`cpu_policy=maxcpus-1`; the exact command line, sysfs masks, `nproc`, and
per-CPU accounting independently prove that eight CPUs were online.

## Analysis

Deriving from exact AH avoids the package-tree DA9214 and A72-power nodes and
retains the previously tested board contract. Whole-tree comparison makes the
observer node the only attributable DT variable; marker text alone would not.

The audited register offsets and gate bit match the pinned vendor DVFSP source
and upstream MT6797 clock driver. The strict stopped rule matches the vendor
stop sequence: reset FSM, disabled/stable timer, cleared PWR_IO_EN, stable
program/status words, and gated I2C_APPM clock. Active wins on any modeled
firmware motion; missing or contradictory evidence becomes unknown.

The observer publishes one latched three-snapshot set. Even a valid
`quiescent-stopped` result cannot establish durable ownership transfer across
boots or later runtime. If reverse engineering proves that the stop is
permanent and identifies every restart authority, a future I2C6 experiment
must establish that invariant before controller/client availability and fail
closed on absent, stale, unknown, timeout, or mismatched state. Otherwise the
I2C controller/SoC layer—not the DA9214 driver—must serialize every transfer
through the verified pause/release protocol.

The observed reset/stable CSPM state is useful negative evidence against an
actively advancing program, but the shared I2C_APPM clock did not satisfy the
predeclared stopped contract. It may be a retained LK/bootloader clock state,
and `clk_ignore_unused` prevents Linux's normal unused-clock cleanup from
resolving that ambiguity. Neither fact proves that Linux owns the bus. Treating
the otherwise quiet snapshot as stopped would weaken the oracle after seeing
the result, so Candidate AN remains `unknown`.

## Conclusion

`inconclusive` for I2C6 ownership on the named Gemini PDA and exact Candidate
AN revisions: Candidate AN booted successfully, its inherited eight-A53/USB
runtime contract passed, and its read-only observer worked as designed. It
observed no modeled firmware motion, but I2C_APPM was ungated, so exclusive
Linux ownership remains unestablished. The result does **not** authorize I2C6
or DA9214 access.

## Follow-up

The fail-closed state decision was predeclared. The detailed engineering
actions below are refined from the observed result and subsequent review:

| Candidate AN result | Safety decision and next discriminating work |
| --- | --- |
| Exact observer reports `quiescent-stopped`, all three snapshots satisfy the fail-closed oracle, and every inherited remotely observable AH contract passes | Keep I2C6 disabled while proving whether stop/handoff is permanent and who can restart DVFSP. A one-time snapshot is insufficient. Establish a race-free pre-controller invariant or verified per-transfer arbitration before read-only legacy/non-A DA9214 identification. Do not request CPU8/CPU9 or change a rail. |
| Observer reports `active` | Keep I2C6 disabled. Prove controller/SoC-level per-transfer pause/release arbitration before any DA9214 access. |
| Observer reports `unknown`, fails to bind, faults, or any inherited AH contract changes | Keep I2C6 disabled. Candidate AN produced this result solely because I2C_APPM was ungated; it observed no modeled firmware motion. Do not repeat AN unchanged. Reverse-engineer permanent stop/handoff and the separate per-transfer `SEMA_I2C_DRV` path against the active binary, including restart authority, locking, clock/transfer ordering, timeout, and every error exit. |

Candidate AM remains reserved for the first possible active CPU8 experiment
and stays on hold. Candidate AN does not authorize an I2C6 transaction,
regulator write, voltage change, or A72 power sequence.
