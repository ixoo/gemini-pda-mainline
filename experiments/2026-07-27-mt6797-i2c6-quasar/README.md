# Experiment: Quasar — MT6797 I2C6 native packed/FIFO canary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-27-mt6797-i2c6-quasar` |
| Status | `attempt 1 complete success; exact narrow native I2C6 contract passed` |
| Subsystem | MT6797 I2C6/iDVFS combined write-read receive path |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-27 to 2026-07-28 |
| Investigator(s) | Device owner and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the ordinary Linux 7.1.3 MT6797 iDVFS policy repeat the exact Vega
packed/FIFO result without any diagnostic mode override or per-mode reset?

Quasar compiles out Orion's comparative run surface and replaces it with one
fixed, root-only, one-shot native-path canary. One write of exactly `run\n`
performs two ordered passes over fixed address `0x69`:

1. offsets `0x05`, `0x06`, and `0x47`;
2. offsets `0x05`, `0x06`, and `0x47` again.

The six distinct receive sentinels are `a5,5a,3c,96,69,c3`. Each read must
overwrite its sentinel with the prior Vega tuple `d9,d0,c0`. The run stops at
the first transport, native-policy, counter, or value mismatch.

No Quasar code selects the WRRD length mode or FIFO/DMA engine. The dedicated
MT6797 iDVFS controller data from patch 0115 must naturally program packed
`TRANSFER_LEN=0x0101`, leave `TRANSFER_LEN_AUX=0x0000`, choose FIFO for both
one-byte legs, program `CONTROL=0x003a` with controller DMA disabled, receive
one byte, and report only `I2C_TRANSAC_COMP`.

## Prior evidence

Exact Vega attempt 3 established one functional mainline I2C6 receive path:

- packed FIFO returned `d9,d0,c0`, with `TRANSFER_LEN=0x0101`, FIFO count one,
  and no I2C6 APDMA activity;
- packed APDMA returned the same tuple;
- auxiliary-length APDMA returned zeroes while its auxiliary length remained
  zero and its receive side did not complete;
- the complete run retained console, USB development shell, eight Cortex-A53
  CPUs, and orderly native reboot serviceability.

That result selects packed length encoding and excludes the unvalidated
auxiliary negative control. It does not identify the device at `0x69`, prove
arbitrary transfers, establish a register-write contract, register a
regulator, or authorize Cortex-A72 power actions. See
`../2026-07-27-mt6797-i2c6-vega/results/runtime-candidate-vega-attempt-3-20260727.txt`.

## Provenance and environment

- Kernel release and upstream input: Linux `7.1.3`, pinned by
  `kernel/manifest.json`.
- Exact predecessor series:
  `patches/series-vega-i2c6-idvfs-fifo`.
- Quasar series: `patches/series-quasar-i2c6-native-fifo`; it is the exact
  Vega series plus one logical patch,
  `patches/v7.1.3/0119-i2c-mediatek-add-fixed-Quasar-native-path-canary.patch`.
- Named profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-quasar`.
- Quasar policy: `configs/gemini-i2c6-quasar.fragment`.
- Build environment: two independent repository recovery-VM source/build
  roots through `./scripts/dev-vm build-kernel`.
- Candidate assembly: the two packages crossed with two independent assembly
  roots; all four candidates were byte-identical.
- Selected boot path: owner-selected logical `boot2`, after package/container
  validation, guarded installation, and full-partition readback.

The completed build and installation are preparation evidence. Attempt 1 is
the separate named-device hardware observation for the exact narrow Quasar
contract; it does not promote any broader I2C6 or DA9214 operation.

## Safety assessment

The profile compiles
`CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=n` and
`CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y`; therefore no `orion-run-all` file or
Orion length/engine override is present in the derivative. The sole Quasar
file is `quasar-run-native`, mode `0600`, beneath the exact I2C6 adapter's
debugfs directory. The probe gate requires the dedicated iDVFS compatible,
the canonical `/i2c@1100e000` OF node by pointer identity, and a non-NULL
DVFSP handoff.

The one-shot state is consumed before any run gate or transfer. The complete
run holds `I2C_LOCK_ROOT_ADAPTER`, requires no adapter children, a ready
handoff, zero transfer/DMA-start/nonzero-START/IRQ counters, probe initialization
counters exactly `1,1`, and adapter retries exactly one. It calls
`__i2c_transfer()` so it does not recursively acquire the held adapter lock.
Retries are changed `1 -> 0 -> 1` and restored on every exit.

Quasar never calls `mtk_i2c_init_hw()`. In particular, it performs no reset
before, between, or after successful samples. A success must preserve
`init_attempts=1` and `init_successes=1`, demonstrating that no native driver
error-recovery reset occurred. Existing driver error paths retain ownership of
their normal controller cleanup; any increment is recorded and makes the
canary fail. There is no post-success reset that could hide dirty-state or
reentrancy behavior.

Every accepted sample must report FIFO, `0101/0000`, transaction count two,
control `003a`, completion-only IRQ, FIFO count one, and all recorded I2C6
APDMA pre/IRQ/completion/post-extraction fields zero. The post-extraction
snapshot must show FIFO receive count zero, proving that the byte was drained
without a diagnostic reset. Status separates attempted transfers, software
transport completions, and value-validated samples, and reports an unprogrammed
failure as `engine=unobserved` rather than inferring FIFO from a zeroed field.
A complete success additionally requires all three result counts to be six
and absolute counters `6,0,6,6` for transfer attempts, DMA starts, nonzero
STARTs, and IRQs.

The bus operation is not literally read-only: each observation sends one fixed
register-pointer byte before reading one byte. It sends no register data byte.
There is no arbitrary address, pointer, length, engine, retry, reset, page, or
data input. `PAGE_CON` writes, data writes, i2c-dev, DA9211/DA9214 provider
registration, and active MT6797 A72 power are absent. CPUs 8 and 9 remain
unrequested with `maxcpus=8`.

Any identity, serviceability, gate, transport, policy, counter, tuple, kernel,
or automatic-reboot mismatch is a stop condition. Preserve the first result
and do not invoke the file twice or repeat an identical image.

## Associated code

- `patches/v7.1.3/0119-i2c-mediatek-add-fixed-Quasar-native-path-canary.patch`
  implements the compile-time-exclusive fixed canary and read-only snapshots.
- `patches/series-quasar-i2c6-native-fifo` selects exact Vega plus patch 0119.
- `configs/gemini-i2c6-quasar.fragment` fixes identity and the disabled
  i2c-dev/provider/A72 boundary.
- `kernel/manifest.json` pins the named profile.
- `scripts/test-quasar-contract.py` checks the patch/profile/series/manifest
  invariants and rejects representative unsafe or attribution-weakening
  mutations.
- `results/pre-boot-hypothesis.txt` is the machine-readable planned gate.

## Procedure

1. Run the local static contract and mutation test. Require JSON parsing,
   patch syntax parsing, whitespace checks, and exact Quasar-over-Vega series
   equality.
2. Build the named Quasar profile twice in independent VM output directories.
   Validate the effective series, resolved configuration, kernel identity,
   compiled DT, package inventory, and complete non-timestamp equality.
3. Assemble two candidates from the exact proven serviceability lineage.
   Require byte equality, the unchanged I2C6 resources/compatible, the exact
   Quasar kernel/configuration, and no Orion endpoint.
4. Record package, raw image, padded 16 MiB image, DT, initramfs, and manifest
   hashes in a separate build result. A guarded workflow may then install only
   inactive logical `boot2`, with full backup and matching full readback.
5. On one owner-selected `boot2` start, require exact Quasar kernel, command
   line, USB identity, console, keyboard, CPUs `0-7`, handoff, childless I2C6,
   zero counters, retries one, and an unused `quasar-run-native` file. Abort
   before the write on any mismatch.
6. Write exactly `run\n` once. Capture the complete status, I2C6 handoff
   status, kernel log, CPU/serviceability state, and boot ID. Do not retry on
   the same boot.
7. Classify the first result using the decision table below and preserve
   pstore after a separate normal reboot if needed.

## Pre-boot hypothesis, evidence, and decisions

| Exact result | Unique attributable evidence | Decision-changing next action |
| --- | --- | --- |
| Two exact `d9,d0,c0` passes; attempted/transport-completed/value-validated counts all six; every sample FIFO with `0101/0000`, `003a`, completion-only IRQ, FIFO count one then drained count zero, all-zero I2C6 APDMA snapshots; counters `6,0,6,6`; init remains `1,1`; retries `1,0,1` | The ordinary MT6797 iDVFS 1+1 policy, without Orion mode forcing or reset, independently reproduces the functional packed/FIFO path and leaves it naturally reusable | Close the I2C6 short-read policy on this named unit. Design a separate fixed read-only DA9214 identity/register-contract experiment; do not add a provider or A72 action yet. |
| First pass returns the expected tuple but the second pass differs or any native state/counter/init invariant changes | A dirty-state or reentrancy boundary exists despite a successful first transfer or pass | Stop without reset/retry. Use the exact first mismatch and snapshots to isolate controller/FIFO cleanup before any device/provider work. |
| Any sample echoes its pointer or retains its distinct prefill | The native path did not produce the established receive byte for that offset | Stop at that sample. Reconcile FIFO ordering, DATA_PORT reads, START/control, and interrupt/FIFO state; obtain a wire trace if possible. |
| A transport error, incomplete/extra IRQ, FIFO count mismatch, unexpected DMA state, or native driver reset occurs | The exact natural path failed before a repeatable read-only canary completed | Preserve the failing sample and normal driver cleanup evidence. Do not repeat Quasar unchanged or fall back to Orion's forced modes. |
| Boot, identity, handoff, childless, zero-counter, retry, CPU, console, keyboard, or USB gate fails | The candidate did not reach the attributable observation boundary | Do not write the debugfs command. Preserve console/pstore evidence and change only the failing layer. |

No branch identifies the IC, establishes writable registers, enables PAGE_CON,
registers a regulator, or authorizes either Cortex-A72.

## Observations

The static contract and all mutation tests passed. Two independent kernel
builds produced the same kernel and normalized package contents. The complete
2-by-2 build/assembly matrix produced one raw boot image,
`c621e87431641a16af65ae3d144bfc97cd6c01c28b4ce4e9f81fc6e7ea428010`,
and one 16 MiB padded image,
`73fceae91606ebf831e503585406df1e2be997edc9fddff1bcae9ec718c91d78`.
See `results/build-reproducibility.txt`.

On Gemian `3.18.41+`, the guarded installer resolved exactly one live-GPT
`boot2` partition at `/dev/mmcblk0p30`; the active root remained
`/dev/mmcblk0p29`. It required an unmounted, writable, inactive 16 MiB target,
no swap or holders, battery present/Good at 100%, and the exact prior
Vega full-partition identity. It preserved a private full backup, wrote once,
synced and flushed, and obtained an exact full-partition readback matching
Quasar's padded hash. See `results/install-boot2-20260727.txt`.

No reboot or slot selection was performed by the installer.

On the owner-selected boot2 start, the one-session runner passed the exact
kernel, command-line, configuration, canonical I2C6 topology, childless bus,
zero-counter, handoff, CPU, console-device, keyboard-device, USB, UDC, and
unused-one-shot gates. Its final adjacent revalidation passed before exactly
one `run\n` write.

All six transfers completed and validated. Both ordered passes returned
`d9,d0,c0`, overwriting all six distinct receive prefills. Every sample used
the ordinary unforced FIFO policy with `TRANSFER_LEN=0x0101`,
`TRANSFER_LEN_AUX=0`, `CONTROL=0x003a`, completion-only IRQ, FIFO count one
before extraction and zero afterward, and all-zero APDMA snapshots. Absolute
counters changed from `0,0,0,0` to `6,0,6,6`; initialization remained `1,1`,
so neither an explicit nor normal error-recovery reset occurred.

The boot ID, handoff, CPUs `0-7`, USB carrier/operstate, and UDC configuration
were unchanged after the run. The kernel log contained no fatal or I2C-timeout
signature. See
`results/runtime-candidate-quasar-attempt-1-20260728.txt`.

## Analysis

The exact narrow hardware question passed. Quasar is intentionally narrower
than Vega: it removes the forced comparative engine/length modes and the
per-mode reset, then demonstrates that the selected ordinary policy works
twice without intervening initialization. The clean second pass is the
independent reentrancy observation.

Controller and APDMA reads are diagnostic snapshots, not a wire capture.
Agreement with Vega's tuple is a transport consistency check and still does
not establish silicon identity.

## Conclusion

`Complete success for the exact fixed native-path contract.` This named unit
has a repeatable ordinary packed/FIFO one-byte-pointer plus one-byte-read path
at `0x69`, with zero APDMA starts and no controller reinitialization.

This does not establish the IC identity, a write contract, a regulator
provider, arbitrary I2C6 transfers, suspend/stress behavior, or Cortex-A72
power.

## Follow-up

Update the exact narrow I2C6 row in `docs/HARDWARE_SUPPORT.md` from this
record. Do not repeat Quasar unchanged. Design a separately reviewed, fixed
read-only DA9214 identity/register contract; do not add a provider or perform
any A72 action until that contract succeeds.
