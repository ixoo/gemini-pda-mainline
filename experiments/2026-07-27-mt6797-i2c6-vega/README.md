# Experiment: Vega — exact I2C6 node identity

## Status

Two isolated kernel builds and the complete two-build by two-lineage candidate
matrix reproduce exactly after their permitted build timestamps are
normalized. The candidate and guarded installer are source-pinned and
validated. The exact padded candidate was installed to live-GPT-resolved
logical `boot2`, flushed, and matched by a full 16 MiB local readback. Vega has
booted three times with its delayed console, keyboard, USB Ethernet, eight
A53s, and native reboot path intact. The first two runtime attempts stopped at
the userspace adapter-discovery gate before debugfs, the invocation guard, or
any diagnostic write. Retained pstore proved that I2C6 nevertheless probed
successfully as `i2c-1`, reached `one_shot=unused`, and kept every transfer,
DMA, START, and IRQ counter at zero until each explicit reboot.

Attempt 1 incorrectly followed `adapter/device/of_node`; attempt 2 replaced
that with `adapter/device` parent equality. Exact Linux 7.1 source explains
why both failed: this I2C adapter has a bus and device type but no class, so
its bus link resolves directly to the adapter kobject below the platform
device and no `adapter/device` link exists.

Attempt 3 kept the exact installed image and used the source-proven direct
parent plus exact OF-node relation. It uniquely mapped I2C6 to `i2c-1`, passed
every pre-write and final-revalidation gate, and invoked the diagnostic
exactly once. Packed FIFO and packed DMA each read `d9,d0,c0`; the auxiliary
DMA comparison instead returned `00,00,00`, read its supposedly programmed
auxiliary length back as zero, and reached controller completion while APDMA
RX remained incomplete. The unchanged Orion success validator correctly
rejected that unexpected mixed result. A separate strict classifier records
nine software completions but only six validated receives.

The command-only recovery produced an explicit orderly reboot, clean
`i2c-1` and `1100e000.i2c` shutdown, and no panic, real Oops, warning trace,
I2C timeout, DMA/IOMMU fault, or watchdog reset. Vega is closed and must not
be repeated. Its narrow hardware conclusion is that fixed one-byte pointer
plus one-byte reads work with the special packed encoding in both FIFO and
DMA for this exact diagnostic. It does not identify the device, establish a
write contract, register a regulator, or authorize either A72.

## Pre-boot hypothesis

Orion's fixed diagnostic selects the intended controller with a string
comparison against `of_node_full_name()`. Vega changes only that selection
guard: it resolves `/i2c@1100e000` through the OF core, requires pointer
identity with the probed node, and releases the acquired reference on every
path. The special `mediatek,mt6797-idvfs-i2c` match and non-NULL DVFSP handoff
remain mandatory.

If this guard was the only setup failure, exact Vega will retain Orion's
console, keyboard, USB Ethernet, eight-A53, restart, childless-I2C6, and
one-shot safety boundary while exposing the existing root-only
`orion-run-all` file on the exact I2C6 adapter.

Attempt 3 confirmed that hypothesis. The resulting packed-versus-auxiliary
differential selected Orion's decision-table branch in which packed FIFO and
packed DMA agree while auxiliary DMA differs. The next candidate must use the
native, unforced I2C6 policy twice, require packed `0x0101`, FIFO count one,
zero APDMA-start delta, and `d9,d0,c0`, and continue to prohibit `PAGE_CON`
and data writes, provider registration, and A72 actions.

## Inputs and isolation

- Profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-vega`
- Series: `patches/series-vega-i2c6-idvfs-fifo`
- Configuration: `configs/gemini-i2c6-vega.fragment`
- Delta over Orion:
  `0118-i2c-mediatek-fix-Orion-I2C6-node-identity-check.patch`
- Kernel identity: `7.1.3-gemini-vega`
- USB identity: product `Gemini-L-Vega`, serial
  `GEMINI_VEGA_20260727`

The patch performs no I2C transfer and changes no FIFO, DMA, register,
timeout, retry, reset, DT, power, regulator, CPU, storage, or reboot behavior.
CPU8/9 remain unrequested, I2C6 remains childless, arbitrary `i2c-dev` access
remains disabled, and the active A72 and DA9211-family regulator drivers remain
disabled.

## Offline tooling

The tooling is a narrow derivative of Orion:

- `validate-package-vega.py` requires the exact Vega profile, 107-patch
  inventory, local version, USB descriptors, five attributable 0118 failure
  strings, and an exact byte-identical Orion compiled DT.
- `build-candidate-vega.sh` retains Hubble's exact initramfs and invokes the
  hash-pinned Orion DT builder and dual-lineage validator. It requires the
  serialized boot DT to remain byte-identical to Orion, then emits a
  storage-inert Android-v0 image outside the repository.
- `run-vega-one-shot.py` attributes the Vega kernel and USB identity but
  deliberately retains the existing `candidate=Orion` status grammar and
  `orion-run-all` debugfs file. It sends raw commands directly to the
  service's outer interactive ash, clearing `PS1` and `PS2` before any
  machine marker; it starts no nested shell and uses no heredoc. Its
  remote-template inventory distinguishes substitution placeholders from
  intentional runtime markers, and its EXIT attribution emits exactly one
  abort marker for any otherwise unmarked pre-completion exit. The completion
  state is committed before its terminal marker is emitted, preventing a
  signal from producing both completion and abort terminals. Capture parsing
  admits only the exact inherited service/BusyBox prelude with its bounded
  repeated session pair, binds that count to `/run/ac-status`, requires the
  banner at byte zero, and requires completion to be the final nonempty line.
  Every success-frame transition has exact newline adjacency, so no unframed
  bytes are accepted between gate, result, post-state, raw AC/dmesg, and
  completion sections; raw AC and dmesg contents remain preserved inside
  their respective frames.
  An exact pre-gate abort after that envelope remains a failed run but reports
  its machine reason directly. Its dynamically loaded Vega package validator
  is source-pinned. Linux 7.1 registers an I2C adapter without a device class,
  so its canonical bus target is the adapter kobject itself and no
  `adapter/device` link is created. The collector therefore requires the
  platform and adapter bus entries to be symlinks, canonicalizes each target,
  derives the adapter target's direct parent with shell path removal, and
  selects it only by exact equality to the canonical I2C6 platform target.
  The selected adapter's direct `of_node` link must independently resolve to
  the canonical target of the exact
  `/sys/firmware/devicetree/base/i2c@1100e000` node; that exact DT path, not a
  derived target, remains the emitted `i2c6_of`.
- Before any mapping count gate, the collector emits a bounded read-only
  `canonical-adapter-target-direct-parent-v1` topology frame. It binds the
  already validated kernel, configuration, and boot ID, records the canonical
  platform and DT targets, and inventories at most 64 C-locale-ordered adapter
  links. A bounded wire token accepts only
  `i2c-[A-Za-z0-9_-]{1,60}`; the numeric `i2c-[0-9]+` validity bit is derived
  independently and every success path still requires every adapter name to
  be numeric. A bounded preflight attributes an unsafe basename before frame
  emission, while the inventory repeats the token check against drift. Each
  entry records canonical target, direct parent, OF target, and exact match
  bits plus independently checked counts. The parser requires exact frame
  adjacency, C-order, line inventory, field order, safe token and path
  grammar, derived-parent relationship, bits, and counts on both success and
  complete-topology pre-gate abort captures. Thus a mapping/count abort
  preserves decision-changing topology without creating the invocation guard
  or writing the diagnostic.
- Childlessness is checked without deriving an adapter number: a bounded scan
  canonicalizes every actual I2C bus entry and counts only targets whose
  direct parent is the selected adapter target, while distinguishing the
  selected adapter link itself. Immediately before the guard and sole write,
  the collector repeats the platform, full adapter link/name/target,
  direct-`of_node`, childless identity, and every initial topology count. The
  repeat globally recomputes OF identity for every adapter, so a non-parent
  adapter that acquires the same exact DT target cannot hide outside the
  selected-parent branch. An ordered six-step final-revalidation frame then
  rebinds the diagnostic to that exact adapter and rechecks its non-symlink
  file type, mode, unused status, and the I2C6 handoff status. A partial frame
  is accepted only as the exact prefix attributable to its terminal abort
  reason. Frame END, gate END, and PASS immediately precede the no-clobber
  guard and write. No OF/path suffix, dot/dot-dot component, controller
  basename, or adapter-number selection heuristic participates. Missing,
  unreadable, unbound, malformed, consumed, or changed I2C6 identity aborts
  before PASS and before the diagnostic write.
- `classify-vega-mixed-result.py` is a separate post-capture classifier for
  the exact ten-line FINAL body observed in attempt 3. It requires every
  header counter, retry value, sample field, register/mode order, packed
  `d9,d0,c0` receive, and auxiliary-DMA incomplete-RX state exactly as
  captured. Its mutation suite also requires the unchanged Orion complete
  and stop-first-partial validators to reject this mixed outcome.
- `verify-vega-reproducibility.py` requires two distinct validated Vega
  packages and four distinct package/Cassini candidate lanes. It compares
  normalized package mode/size/hash inventories, removes only
  `generated_utc` from build provenance, requires distinct build timestamps,
  and requires all four complete candidate mode/size/hash inventories to be
  exact. Before accepting a candidate, it source-pins the Vega contract,
  package validator, and LK analyzer; reproduces all 32 LK gates against the
  packaged `Image.gz`, exact Orion DT, and exact Hubble initramfs; reproduces
  `analysis.txt`; and proves that the 16 MiB image is the raw boot image
  followed only by zero bytes. It emits one strict source-attributed record.
- `derive-installer.py` reconstructs and hash-verifies Orion's guarded
  installer, then derives Vega's one-write `boot2` installer. Production
  derivation requires the reviewed, stored, and source-pinned two-build/2x2
  record and exact candidate identities in `installer_vega.py`. The final
  installer was derived once to obtain its identity, self-pinned, derived
  again, and compared byte-for-byte.

Run the offline checks from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-07-27-mt6797-i2c6-vega/scripts/test-vega-contracts.py
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-07-27-mt6797-i2c6-vega/scripts/test-vega-runner.py
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-07-27-mt6797-i2c6-vega/scripts/test-vega-mixed-result.py
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-07-27-mt6797-i2c6-vega/scripts/test-vega-reproducibility.py
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-07-27-mt6797-i2c6-vega/scripts/test-vega-installer.py
bash -n \
  experiments/2026-07-27-mt6797-i2c6-vega/scripts/build-candidate-vega.sh
```

After two kernel packages reproduce, assemble each package against the exact
Cassini package and Hubble artifact into a new output parent outside Git:

```sh
experiments/2026-07-27-mt6797-i2c6-vega/scripts/build-candidate-vega.sh \
  --package PACKAGE \
  --cassini-package EXACT_CASSINI_PACKAGE \
  --hubble-artifact EXACT_HUBBLE_ARTIFACT \
  --output-parent NEW_EXTERNAL_DIRECTORY
```

Then calibrate only `VEGA_RAW_SHA256`, `VEGA_RAW_SIZE`,
`VEGA_PADDED_SHA256`, and `VEGA_MANIFEST_SHA256` from the strict record:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-07-27-mt6797-i2c6-vega/scripts/verify-vega-reproducibility.py \
  --repository REPOSITORY \
  --package-a VEGA_PACKAGE_A --package-b VEGA_PACKAGE_B \
  --candidate-a-a PACKAGE_A_CASSINI_A \
  --candidate-a-b PACKAGE_A_CASSINI_B \
  --candidate-b-a PACKAGE_B_CASSINI_A \
  --candidate-b-b PACKAGE_B_CASSINI_B \
  --output NEW_RECORD
```

Review and add that exact record as `results/build-reproducibility.txt`, pin
its SHA-256 as `REPRODUCIBILITY_RECORD_SHA256`, then derive once to obtain the
installer SHA-256, pin `INSTALLER_SHA256`, and derive again.

## Validated artifact identities

- Kernel release: `7.1.3-gemini-vega`
- Kernel `Image`: `26c9af2e6720ffd4aad659966f6f0f6b2bd58895c0a8361be800b44db7655ead`
- Kernel `Image.gz`: `97cb25193f24b60ac47dba82512cf9f58ae0182a7395f14017666c092705d4d8`
- Kernel configuration:
  `b187596fd51c3be78ff846b7f4e23fc389f9fc6045f5fd4f9329112893ed7ac7`
- Raw Android-v0 image:
  `08cf45530de0b15441680fafecad1d56557f2285b1d06307fee6ac55ae9b8975`
  (`7747584` bytes)
- Exact 16 MiB `boot2` image:
  `4fc71c508c40081c91a48e13af1c8a0ac5fb79871e04d63f98efa4ddbea3e6a7`
- Candidate manifest:
  `0abe52ebbda743bfd031fe856aa82dd8d9e9625620aa810ab1a71b9356f4ae07`
- Reproducibility record:
  `cafd78721f867d065d07925db40ea8c2301e774be1cb50e2df384a9ed00398ae`
- Guarded installer:
  `3df562f45481f1ba5cd854d896113df9b9971616e2ceef77bdb3cf91b10949d3`

The independent static audit is a conditional GO for this exact childless
DT/config and the planned single diagnostic write only after every live gate
passes. It records why childlessness and the ready marker must not be inferred
from the driver or log alone.

## Unique evidence and decision

The attempt-3 topology frame contains exactly two adapters and only `i2c-1`
has both the canonical `1100e000.i2c` direct parent and exact
`/i2c@1100e000` OF target. Every gate was repeated immediately before PASS,
the no-clobber invocation guard was created once, and the sole write returned
zero. Post-state preserved the boot ID, CPUs 0--7, handoff, USB carrier, UDC,
and exact 9/6/9/9 transfer/DMA/START/IRQ counter totals.

- Packed FIFO used `TRANSFER_LEN=0x0101`, FIFO count one, controller DMA
  disabled, no APDMA activity, exact completion IRQ, and returned
  `d9,d0,c0`.
- Packed DMA used the same packed length and returned the same tuple after
  both one-byte APDMA lengths reached zero, channel enable cleared, and
  interrupt flag became `3`.
- Auxiliary DMA read `TRANSFER_LEN_AUX=0`, returned zero bytes, and left
  APDMA enabled with RX length one and only flag `1`, despite controller
  completion and a software return of two messages.

Exact 7.1 disassembly shows that the receive bounce buffer is initially
zeroed and copied back after this controller-only success. The active Gemian
binary independently contains the special packed/FIFO path alongside the
ordinary auxiliary-length format. The causal conclusion is therefore to
retain the exact I2C6 special compatible and packed encoding, use FIFO for the
native short path, and exclude the invalid auxiliary comparison. Do not
repeat Vega or weaken the original success validator.

A read-only live Orion canary established the collector transport boundary:
raw commands reached the inherited interactive ash, prompt clearing kept every
subsequent machine marker clean, and a forced pre-gate failure emitted exactly
one attributed abort without creating the invocation guard or diagnostic
write. See
[`results/transport-canary-orion-20260727.txt`](results/transport-canary-orion-20260727.txt).

See
[`results/pre-boot-hypothesis.txt`](results/pre-boot-hypothesis.txt) for the
machine-readable pre-boot record,
[`results/build-reproducibility.txt`](results/build-reproducibility.txt) for
the exact two-build/2x2 proof,
[`results/static-kernel-audit-20260727.txt`](results/static-kernel-audit-20260727.txt)
for the independent kernel audit,
[`results/install-boot2-20260727.txt`](results/install-boot2-20260727.txt) for
the sanitized full-backup/write/flush/readback result,
[`results/runtime-candidate-vega-attempt-1-20260727.txt`](results/runtime-candidate-vega-attempt-1-20260727.txt)
and
[`results/runtime-candidate-vega-attempt-2-20260727.txt`](results/runtime-candidate-vega-attempt-2-20260727.txt)
for the two pre-write aborts,
[`results/runtime-candidate-vega-attempt-3-20260727.txt`](results/runtime-candidate-vega-attempt-3-20260727.txt)
for the complete runtime and recovery record,
[`results/runtime-candidate-vega-attempt-3-final.txt`](results/runtime-candidate-vega-attempt-3-final.txt)
and
[`results/runtime-candidate-vega-attempt-3-classification.txt`](results/runtime-candidate-vega-attempt-3-classification.txt)
for the exact extracted result and strict mixed classification,
[`results/attempt-3-packed-vs-aux-source-audit-20260727.txt`](results/attempt-3-packed-vs-aux-source-audit-20260727.txt)
for the mainline/vendor source and binary reconciliation, and
[`results/linux-7.1-i2c-adapter-sysfs-audit-20260727.txt`](results/linux-7.1-i2c-adapter-sysfs-audit-20260727.txt)
for the exact source-backed sysfs correction. See
[`scripts/test-vega-contracts.py`](scripts/test-vega-contracts.py) for the
static and mutation checks.
