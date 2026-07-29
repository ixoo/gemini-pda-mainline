# Experiment: Kepler — split I2C6 pointer/write and receive calls

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-27-i2c6-split-read-kepler` |
| Status | `completed; exact hardware result split-stable-other (05,05)` |
| Subsystem | MT6797 I2C6 receive DMA / DA9214 register access |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-27 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Photon r2 established that six combined two-message `I2C_RDWR` transactions
returned success while every CPU-visible receive byte remained equal to its
distinct prefill. Does the CPU-visible receive byte change when the register
pointer write and read are instead issued as two independent one-message
`I2C_RDWR` calls?

Kepler tests only register pointer `0x05` at address `0x69`. It performs two
pairs:

1. one-message write of `0x05`, then a separate one-message read prefilled
   with `0xa5`;
2. one-message write of `0x05`, then a separate one-message read prefilled
   with `0x5a`.

The separate read selects the controller's ordinary RX path instead of its
two-message WRRD optimization. A static comparison separately predicts a
WRRD-specific transfer-length programming problem; Kepler does not depend on
that prediction and provides an attributable runtime discriminator.

The STOP between pointer and read was initially treated as a possible
protocol confound. A post-runtime review of the retained legacy datasheet
resolved it: Renesas explicitly documents both a repeated START and a STOP
followed by a second START as valid DA9214 register-read sequences. The same
document maps the basic address plus one to direct page-2/page-3 access.
Kepler's split sequence is therefore a documented chip access shape, although
its result still cannot by itself identify the byte's physical source.

## Provenance and environment

- Required live kernel release: `7.1.3-gemini-cassini`.
- Required live boot ID:
  `cdd23c48-0bd3-4980-95c8-5e054be860d9`.
- Required decompressed configuration SHA-256:
  `83c85429cdcb7d66cb96df2c9005456afd67fc5c7dbfe5d76e9879bf45c1759b`.
- Required `/bin/cassini-probe` SHA-256:
  `30073f6ea7d0b57d3654ece5c6212da1c94ff4d24514b62d07331136a4efaf0e`.
- Required accepted Photon result:
  `post-all-equal-pre`, six completed transactions, exact tuple
  `a1,b2,c3,d4,e5,f6 -> a1,b2,c3,d4,e5,f6`.
- DA9214 protocol source: privately retained Renesas/Dialog
  `REN_da9213_14_15_datasheet_3v3_DST_20200219-3075819.pdf`, SHA-256
  `d853349c74dad282e23f3826f2ed0c5071cbf87cf51a040c2c747d0510141638`,
  Datasheet Revision 3.4, pages 36-37. The PDF is evidence and is not copied
  into Git.
- Required I2C6 pre-counters: transfer attempts, DMA starts, nonzero starts,
  and IRQ count all exactly `6`.
- Kepler source SHA-256:
  `1ff0c574ee8e02290a6f53234d2f22652ce25c385b31442e8ff2411d094e0765`.
- Kepler static AArch64 ELF SHA-256:
  `3afdaeea3f913706a0ee3f44732c37b6c0fced01f940f6d68a8356dfad946fa7`.
- Kepler ELF size: 537,584 bytes.
- Compiler: GCC 13.3.0 in the AArch64 recovery VM.
- Boot path: the already running exact Hubble/Cassini `boot2` runtime. Kepler
  contains no boot image and performs no partition installation.
- Exact controller source used for the transfer-shape comparison:
  `/home/julien.guest/src/gemini-pda-cassini-repro/linux-7.1.3-series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-source/drivers/i2c/busses/i2c-mt65xx.c`
  in the recovery VM.

## Safety assessment

Kepler is not literally bus-read-only: each pair writes the one-byte register
pointer `0x05`. It never sends a register data byte and never selects another
register or I2C address. The two receive bytes are observations only.

The exact helper accepts no arguments and contains no persistent-storage,
partition, watchdog, reboot, poweroff, CPU-control, regulator-control,
`PAGE_CON`, `/dev/mem`, delay, retry, scan, or subprocess path. It stops on
the first ioctl result other than exactly one. The complete path has exactly
four ioctl calls, each with `nmsgs=1`, address `0x69`, and length one.

The runner requires the exact accepted Hubble boot ID, kernel, command line,
configuration, Cassini helper, CPU set, handoff state, childless I2C6 adapter,
USB service, retained Photon one-shot guard, exact Photon kernel-log evidence,
and exact pre-counters before it decodes any payload. It stages the exact
hash-pinned helper only in the initial RAM root's `/run`, creates a
root-owned mode-0400 no-clobber invocation guard before execution, invokes
the helper once, and removes it after return. A power cycle removes the
guard.

The runner neither reads nor writes persistent storage. It does not access a
boot slot and cannot reboot or shut down the device. A failed gate does not
invoke Kepler. A runtime mismatch preserves a private mode-0600 transcript
and returns failure.

## Associated code

- `initramfs/kepler-probe.c`: no-argument, fixed-function split-read helper.
- `scripts/candidate_kepler.py`: accepted boot, pre/post counter, source, ELF
  hash, and size pins.
- `scripts/build-kepler-probe.sh`: deterministic static AArch64 build.
- `scripts/validate-kepler-probe.py`: source-scope and static ELF validator.
- `scripts/test-kepler-ioctl.c`: offline intercepted-ioctl harness covering
  the four-call layout, five complete classifications, and every fail-stop
  boundary.
- `scripts/run-kepler-transfer.py`: exact-Hubble-gated volatile transfer,
  one-shot invocation, and evidence validator.
- `scripts/test-kepler-transfer.py`: payload, one-invocation, forbidden-scope,
  valid-class, identity, prior-evidence, counter, and invocation mutation
  tests.

Building and offline validation require no privileges or device access. The
runtime runner requires the unauthenticated root shell available only over the
direct USB development link.

## Procedure

1. Build the helper twice in separate recovery-VM directories with
   `scripts/build-kepler-probe.sh`.
2. Require the two ELF files to be byte-identical, static fixed-address
   AArch64 executables with the pinned size and SHA-256.
3. Compile and run `scripts/test-kepler-ioctl.c` in the recovery VM. Require
   exactly four successful intercepted calls in this order:
   `TX(05), RX(a5), TX(05), RX(5a)`, with `nmsgs=1` for every call.
4. Run `scripts/test-kepler-transfer.py` on the host and in the recovery VM.
   Require all eleven tests to pass.
5. Syntax-check the fully generated remote program, including the exact
   base64 payload, with the recovery VM's BusyBox shell.
6. Confirm the named device is still on the exact accepted boot ID. Discover
   the direct USB interface whose MAC is `42:00:15:19:82:00`.
7. Invoke the runner once, using the exported exact helper and a new direct
   child below mode-0700 `artifacts/runtime-captures`:

   ```text
   python3 experiments/2026-07-27-i2c6-split-read-kepler/scripts/run-kepler-transfer.py \
     --interface enN \
     --helper /absolute/path/to/artifacts/vm-export-kepler-20260727/kepler-calibrated-20260727/a/kepler-probe \
     --output-dir /absolute/path/to/artifacts/runtime-captures/kepler-YYYYMMDDTHHMMSSZ
   ```

8. Do not retry on the same boot. The retained invocation guard makes a
   second attempt fail closed.

## Observations

Two independent calibrated recovery-VM builds were byte-identical. Each
produced a 537,584-byte static AArch64 ELF with SHA-256
`3afdaeea3f913706a0ee3f44732c37b6c0fced01f940f6d68a8356dfad946fa7`.

The intercepted-ioctl harness passed all nine cases: five complete output
classes and failures at calls one through four. The successful path issued
exactly four `I2C_RDWR` calls, each with one one-byte message at address
`0x69`, in the intended pointer-write/read order.

Eleven runner tests passed on both the host and recovery VM. Mutations to the
accepted boot ID, exact pre/post counters, prior Photon result, Photon guard,
invocation count, global section order, and helper line order were rejected.
Disconnect and signal paths remove both the staging and final volatile helper
paths. Incomplete TX and RX results are saved in the raw transcript and then
intentionally rejected as complete classifications. The fully generated
738,499-byte remote program has one probe invocation site and passed BusyBox
shell syntax.

The exact helper was exported to the Git-ignored host artifact path documented
in `results/build-kepler-20260727.txt`. No device or network connection
occurred during implementation, build, export, or offline validation.

The runner was subsequently invoked once over the direct USB development
link. Its private, Git-ignored mode-0600 transcript has SHA-256
`43127dc409bfea80dbb7a7bccd8be2727aafa040207c3f5acd8df54f24b61ef6`
and passed the exact pinned transcript validator.

The gate established exact accepted Hubble boot ID
`cdd23c48-0bd3-4980-95c8-5e054be860d9`, CPUs `0-7` online, handoff `ready`,
the exact prior Photon evidence, and all four I2C6 counters at `6`. The exact
Kepler ELF was transferred to volatile `/run`, invoked once, removed, and
left a mode-0400 root-owned one-shot guard.

All four independent one-message ioctls returned exactly one with `errno=0`.
The observations were:

```text
pair 1: pre=a5 post=05
pair 2: pre=5a post=05
```

Kepler classified this as `split-stable-other`, with two completed pairs,
four completed calls, post-difference mask `0x03`, and process status `2` as
specified for a complete non-`d9` result. Transfer-attempt, DMA-start,
nonzero-start, and IRQ counters each changed exactly from `6` to `10`.
Boot ID, CPU set, handoff, USB carrier/service state, and UDC configuration
remained unchanged.

No reboot, persistent-storage, watchdog, boot-slot, regulator, CPU-control, or
`PAGE_CON` operation occurred. The sanitized runtime record is
`results/runtime-kepler-split-read-20260727.txt`.

## Analysis

The offline results established the transfer shape and enforcement machinery.
A complete runtime result was to be interpreted as follows:

- `split-all-equal-pre` (`a5,5a`): the earlier observation is not explained
  solely by selection of the controller's WRRD programming branch. The next
  experiment should be a kernel-side RX-DMA observer; do not add more live
  register probes.
- `split-stable-d9` (`d9,d9`): ordinary single-message RX DMA and userspace
  copyback work for this access shape. The fault is isolated to the combined
  WRRD/repeated-start boundary, without distinguishing its controller and
  device-protocol halves.
- `split-stable-other`: ordinary RX produced a stable byte, but it differs
  from the prior expected `0xd9`; stop and reconcile the device state and
  register interpretation.
- `split-unstable`: ordinary RX changes the CPU-visible buffer, but the
  device/protocol result is unstable.
- `split-mixed-equal-pre`, any non-one ioctl result, or any counter/state
  mismatch: inconclusive; stop without retrying on this boot.

For every complete result, all four I2C6 counters must change exactly from
`6` to `10`, while boot ID, CPU set, handoff, USB, and UDC state remain
unchanged.

The hardware result selected `split-stable-other`: both distinct receive
prefills were replaced by the same byte, `0x05`. This rejects a universal
failure in which every I2C6 receive buffer simply survives unchanged through
userspace. It demonstrates a repeatable CPU-visible overwrite on the ordinary
single-message read shape and a transfer-shape distinction from Photon's
combined WRRD observations.

It does not establish that DA9214 register `0x05` contains `0x05`. The observed
byte is identical to the preceding pointer byte. The datasheet's byte-read
diagram explicitly permits the STOP plus second START sequence Kepler used,
so loss of the pointer merely because of STOP is not a supported explanation.
Plausible alternatives include a real device response or controller, DMA,
cache, or buffer residue involving the pointer byte. The controller IRQ and
DMA-start counters likewise do not prove the wire byte, APDMA completion, or
independently validate RX-DMA completion.

The exact `0x05` result is therefore more informative than preserved
sentinels, but less conclusive than the planned `d9,d9` branch. It supports
moving the next observation into the kernel/controller boundary rather than
treating `0x05` as a regulator identity or issuing additional userspace
register probes.

## Conclusion

`Confirmed for the scoped observation.` On the exact named Gemini PDA,
accepted Hubble boot, and pinned Kepler ELF, ordinary split one-message reads
changed both distinct CPU-visible receive prefills to stable `0x05`, while all
four controller counters advanced by four and the surrounding runtime state
remained stable. This does not confirm a DA9214 register value or complete
I2C6 RX-DMA correctness.

## Follow-up

Do not repeat Photon or Kepler merely to reproduce marker text. A new bounded
same-boot discriminator may use two already allowlisted direct-page register
pointers, `0x06` and `0x47`, with distinct receive prefills. Results
`06,47` would track the immediately preceding pointer bytes, while the
independently observed Gemian tuple requires `d0,c0`. After that discriminator,
move to the narrowly attributable MT6797 I2C6 FIFO/WRRD correction or a
kernel-side DMA-completion observer before returning to regulator or A72 work.
