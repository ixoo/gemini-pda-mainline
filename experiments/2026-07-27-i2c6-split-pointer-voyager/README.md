# Experiment: Voyager — split reads with distinct register pointers

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-27-i2c6-split-pointer-voyager` |
| Status | `completed; exact hardware result split-pointer-echo (06,47)` |
| Subsystem | MT6797 I2C6 receive path / DA921x register access |
| Device variant | Named Gemini PDA unit |
| Date | 2026-07-27 |
| Investigators | Julien Etienne and Codex |

## Question or hypothesis

Kepler's two reads of pointer `0x05` replaced distinct prefills with stable
`05,05`. Does the same protocol-valid split-read shape return the known live
tuple `d0,c0` for two different pointers, or does each receive byte correlate
with its preceding pointer as `06,47`?

Voyager performs exactly:

1. one-message TX pointer `0x06`, then one-message RX prefilled `0x3c`;
2. one-message TX pointer `0x47`, then one-message RX prefilled `0xa6`.

Every call uses `I2C_RDWR`, `nmsgs=1`, one byte, address `0x69`. There is a
STOP between each pointer write and read.

## Provenance and environment

- Accepted unchanged Hubble boot ID:
  `cdd23c48-0bd3-4980-95c8-5e054be860d9`.
- Exact prior private Kepler capture SHA-256:
  `43127dc409bfea80dbb7a7bccd8be2727aafa040207c3f5acd8df54f24b61ef6`.
- Required prior Kepler result: `split-stable-other`, post `05,05`, one
  invocation, helper removed, retained mode-0400 root-owned guard.
- Required I2C6 counters before Voyager: all exactly `10`.
- Required counters after a complete Voyager result: all exactly `14`.
- Voyager source SHA-256:
  `53cef8eca6fc0aa7064bc34a16b97ddaf649603fe286ffd2b04026b5ea57d17b`.
- Voyager static AArch64 ELF SHA-256:
  `1a2a141a376661557610f2dd37b10a6a2da620cdbc35eab24b58129552adcd3e`.
- ELF size: 537,584 bytes; compiler: recovery-VM GCC 13.3.0.

Local proprietary-document evidence was inspected but is not copied or
committed:

- `REN_da9213_14_15_datasheet_3v3_DST_20200219-3075819.pdf`, SHA-256
  `d853349c74dad282e23f3826f2ed0c5071cbf87cf51a040c2c747d0510141638`,
  revision 3.4, pages 36–37.
- `REN_DA9213_14_15_Auto_Datasheet_02v31_DST_20251114.pdf`, SHA-256
  `e0da61ab8e126b3a04d882b7152754d832b78d3da71810f1fc56eaa8fbf118b2`,
  automotive revision 2.31, page 36.

Both documents explicitly allow a register read using repeated START or a
second START after STOP. The older document also describes direct page 2/3
access via the incremented device write/read address. Therefore Voyager's
STOP-separated read is a documented valid protocol form, not a protocol
confound.

## Safety assessment

The helper accepts no arguments and can address only `0x69`. Its only writes
are the pointer bytes `0x06` and `0x47`; it sends no register data. It has no
retry, delay, scan, `PAGE_CON`, storage, partition, watchdog, reboot, power,
CPU-control, regulator, `/dev/mem`, or subprocess path.

The host runner hash-validates the exact private Kepler capture before any
host-link check or transport. The remote gate independently requires the
unchanged boot ID, exact kernel/config/helper, retained Photon and Kepler
guards, exact CPU/handoff/USB state, childless I2C6, and exact counters at
`10`. It stages only the exact helper in volatile `/run`, creates a no-clobber
one-shot guard before execution, invokes once, removes the helper, and
requires counters `14`. Signal/disconnect cleanup removes both staging and
final helper paths.

## Associated code

- `initramfs/voyager-probe.c`: fixed four-call helper.
- `scripts/candidate_voyager.py`: exact source, ELF, boot, prior-capture, and
  counter pins.
- `scripts/build-voyager-probe.sh` and
  `scripts/validate-voyager-probe.py`: deterministic static build and audit.
- `scripts/test-voyager-ioctl.c`: intercepted-ioctl call-layout and
  classification harness.
- `scripts/run-voyager-transfer.py`: fail-closed prior-evidence, volatile
  transfer, one-shot invocation, and transcript validation.
- `scripts/test-voyager-transfer.py`: offline valid and mutation contracts.

## Procedure

1. Build twice in separate recovery-VM directories and require byte identity.
2. Run the ten-case intercepted-ioctl harness and twelve runner tests.
3. Syntax-check the generated exact-payload program with BusyBox `sh -n`.
4. On the unchanged accepted boot, run once:

   ```text
   python3 experiments/2026-07-27-i2c6-split-pointer-voyager/scripts/run-voyager-transfer.py \
     --interface enN \
     --prior-kepler-capture /absolute/path/to/artifacts/runtime-captures/kepler-split-read-20260727T180342Z/kepler-runtime-transfer.txt \
     --helper /absolute/path/to/artifacts/vm-export-voyager-20260727/voyager-calibrated-20260727/a/voyager-probe \
     --output-dir /absolute/path/to/artifacts/runtime-captures/voyager-YYYYMMDDTHHMMSSZ
   ```

5. Do not retry on this boot.

## Observations

Two calibrated recovery-VM builds were byte-identical at the pinned hash and
size. The ten-case ioctl harness passed the exact order
`TX06,RX(3c),TX47,RX(a6)`, all complete classes, and each error boundary.
Twelve host and recovery-VM runner tests passed. BusyBox syntax and ShellCheck
passed. No device or network was accessed during implementation or offline
validation.

Voyager was then invoked exactly once on the unchanged accepted Hubble boot.
The private, Git-ignored mode-0600 capture is 25,759 bytes, has SHA-256
`aae3626d0cbd5275908ff2aaa3f9507709c591b2a0aa2bd996ca0ccf4c46adc1`,
and passes the exact pinned Voyager transcript validator.

All four one-message ioctls returned exactly one with `errno=0`:

```text
TX pointer=06; RX pre=3c post=06
TX pointer=47; RX pre=a6 post=47
```

The aggregate result was `split-pointer-echo`, post `06,47`, difference mask
`0x03`, two completed pairs, four completed calls, and the specified non-live
result status `2`. Transfer-attempt, DMA-start, nonzero-start, and IRQ counters
all changed exactly from `10` to `14`.

Boot ID `cdd23c48-0bd3-4980-95c8-5e054be860d9`, CPUs `0-7`, handoff `ready`,
USB link/service state, and UDC configuration remained unchanged. The helper
was removed and its mode-0400 root-owned invocation guard retained. No reboot,
storage, watchdog, slot, CPU-control, regulator, `/dev/mem`, or `PAGE_CON`
operation occurred. The sanitized evidence is in
`results/runtime-voyager-split-pointer-20260727.txt`.

## Analysis and decision branches

- `split-expected-live`, post `d0,c0`: protocol-valid split reads recover the
  prior live values; ordinary RX/copyback works and Kepler's `05,05` was
  pointer-specific rather than a universal receive result.
- `split-pointer-echo`, post `06,47`: receive data exactly tracks each TX
  pointer. This strongly favors controller/DMA pointer-byte residue over a
  real register value; next use a kernel-side TX/RX DMA-address observer.
- `split-all-equal-pre`, post `3c,a6`: no CPU-visible receive overwrite.
- `split-mixed-equal-pre`: partial/inconclusive; stop.
- `split-stable-other`: both other bytes equal; stable but not attributable to
  the expected register tuple.
- `split-unstable-other`: both prefills changed but the tuple matches neither
  known live data nor exact pointer correlation.
- Any ioctl error, state mismatch, or counter mismatch: preserve the raw
  capture and stop without retry.

The hardware result selected the exact `split-pointer-echo` branch. Two
different TX pointers produced the same two bytes, respectively, in their RX
buffers. This exact per-pair correlation, combined with the documented-valid
STOP-separated read form, establishes that a hardware-visible write replaced
each RX prefill with its immediately preceding TX pointer. It strongly favors
controller/APDMA TX-pointer residue, but does not by itself identify the
physical writer. It is not a stable DA9214 register tuple and is not explained
by an invalid STOP-based protocol.

The result does not yet locate the error within controller FIFO state, APDMA
direction/address/length programming, or the completion/coherency boundary.
The successful ioctl returns and `10→14` counters describe completed
controller activity; the pointer correlation supplies the stronger data-path
evidence.

Neither expected DA9214 live value `0xd0` for pointer `0x06` nor `0xc0` for
pointer `0x47` appeared. The observed `06,47` must not be promoted to DA9214
register contents.

## Conclusion

`Confirmed for the scoped fault signature.` On the exact named Gemini PDA,
accepted boot, and pinned Voyager ELF, each RX byte exactly followed its
distinct preceding TX pointer while all surrounding state remained stable.
This confirms pointer-correlated hardware writes to RX memory and rejects
`06,47` as DA9214 values `d0,c0`; controller/APDMA residue is the leading
inference, not yet an exact sub-block attribution.

## Follow-up

Do not repeat Kepler or Voyager. First issue the same two pointer-only split
reads through i2c-dev's `write(2)`/`read(2)` API, which makes the I2C core use
separate DMA bounce buffers rather than the `I2C_RDWR` direct DMA-safe
buffers. If pointer correlation persists, proceed to the recovered short-FIFO
I2C6 correction; otherwise localize the direct-buffer boundary first.
