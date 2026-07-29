# Experiment: Mariner — i2c-dev API-path differential

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-27-i2c6-api-path-mariner` |
| Status | `completed; exact hardware result raw-pointer-echo (06,47)` |
| Subsystem | MT6797 I2C6 receive path / i2c-dev buffer path |
| Device variant | Named Gemini PDA unit |
| Date | 2026-07-27 |
| Investigators | Julien Etienne and Codex |

## Question or hypothesis

Voyager used four one-message `I2C_RDWR` calls. Its receive buffers were
directly marked DMA-safe by i2c-dev, and each receive byte exactly echoed its
immediately preceding pointer: `06,47`.

Does the same STOP-separated register-read sequence change when issued through
i2c-dev's ordinary `write(2)` and `read(2)` paths?

Mariner performs exactly:

1. one `I2C_SLAVE` selection of address `0x69`;
2. `write(fd, 06, 1)`;
3. `read(fd, ..., 1)`;
4. `write(fd, 47, 1)`;
5. `read(fd, ..., 1)`.

The address-selection ioctl is not an I2C transfer. The four subsequent
syscalls each produce one single-message transfer, so an accepted complete run
must change the I2C6 transfer-attempt, DMA-start, nonzero-start, and IRQ
counters exactly from `14` to `18`.

The only causal difference from Voyager is the i2c-dev userspace API and its
buffer path. Pointer values, address, message boundaries, STOP-separated read
form, boot, kernel, controller, handoff, and surrounding state remain fixed.

## Buffer semantics

The helper initializes its two userspace receive bytes to `3c` and `a6` only
so the before/after log remains unambiguous. Those bytes never initialize a
kernel receive buffer:

- `i2cdev_read()` allocates its own zeroed kernel buffer and does not copy the
  userspace byte into it;
- the current controller path then obtains a separate zeroed DMA-safe receive
  bounce buffer from the I2C core.

Therefore `3c,a6` are userspace-only logging values. The field
`post_diff_user_mask` reports only whether the final userspace bytes equal
those logging values. It is not a DMA sentinel, copyback oracle, or proof of a
hardware overwrite.

If the successful receive path performs no hardware write, both zeroed kernel
buffers predict a final userspace tuple of `00,00`. Even that result would be
only consistent with a no-write/copyback path; it would not prove that DA9214
registers contain zero, because hardware could also have supplied zero.

## Provenance and accepted predecessor

- Accepted unchanged Hubble boot ID:
  `cdd23c48-0bd3-4980-95c8-5e054be860d9`.
- Exact prior private Voyager capture SHA-256:
  `aae3626d0cbd5275908ff2aaa3f9507709c591b2a0aa2bd996ca0ccf4c46adc1`.
- Required prior Voyager result: `split-pointer-echo`, post `06,47`, one
  invocation, helper removed, and retained mode-0400 root-owned guard.
- Required I2C6 counters before Mariner: all exactly `14`.
- Required counters after a complete Mariner result: all exactly `18`.
- Exact private Mariner capture: mode 0600, 27,418 bytes, SHA-256
  `c39c248231bb2c254e4cfce4f88cd2a89b4510124215e49fc8ac9858ba22b531`.
- Mariner source SHA-256:
  `101154791c4a9918afe8438101eeb16eb8eeb2ef8dfe6032f348f6d114a1f0bc`.
- Mariner static AArch64 ELF SHA-256:
  `958ce2a16b6716f550e38667b2bc4c61e04bc0be977c9bf31f594fc30a9bf93c`.
- ELF size: 537,584 bytes; compiler: recovery-VM GCC 13.3.0.

The two Renesas datasheets cited by Voyager explicitly permit a register read
using either repeated START or a second START after STOP. Mariner retains that
same documented STOP-separated form. No proprietary document is copied into
the repository.

## Safety assessment

The helper accepts no arguments and can select only address `0x69`. It performs
one selection ioctl followed by exactly four one-byte bus syscalls. Its only
writes are pointer `0x06` and pointer `0x47`; it sends no register-data byte.

There is no retry, delay, scan, forced-address selection, `I2C_RDWR`, SMBus,
page-control, subprocess, storage, partition, watchdog, reboot, power, slot,
CPU-control, regulator, or raw-memory path.

The host runner validates the exact private Voyager capture before any host
link check. The remote gate independently requires:

- exact Hubble boot, kernel command line, configuration, and embedded helper;
- volatile rootfs and `/run`, with no prior Mariner path;
- retained empty mode-0400 root-owned Photon, Kepler, and Voyager guards and
  no retained predecessor helper or stage file;
- CPUs `0-7` online, CPU8/9 offline and not writable, handoff `ready`;
- exactly one childless I2C6 adapter at `/i2c@1100e000`;
- exact USB gadget identity, address, link, UDC, and shell-service state;
- exact pre-transfer I2C6 status and all four counters at `14`.

Only after every gate passes does it stage the exact ELF in volatile `/run`.
It creates a no-clobber one-shot guard before invocation, invokes once, removes
the helper, retains the guard, captures post-state, and requires the complete
transcript validator to see exact counters `18`. Signal or disconnect cleanup
removes the stage and helper. Raw output is written mode 0600 before an
incomplete or erroneous transcript is rejected.

## Associated code

- `initramfs/mariner-probe.c`: fixed selection plus four-syscall helper.
- `scripts/candidate_mariner.py`: exact boot, predecessor, counter, source, and
  ELF pins.
- `scripts/build-mariner-probe.sh` and
  `scripts/validate-mariner-probe.py`: deterministic static build and
  source/ELF audit.
- `scripts/test-mariner-syscalls.c`: intercepted ioctl/write/read order,
  classification, error, and short-return harness.
- `scripts/run-mariner-transfer.py`: fail-closed predecessor validation,
  volatile transfer, one-shot invocation, and exact transcript validation.
- `scripts/test-mariner-transfer.py`: offline valid, mutation, ordering,
  capture-before-rejection, and single-transport tests.

## Offline validation

Two independent strict recovery-VM builds are byte-identical:

```text
source_sha256=101154791c4a9918afe8438101eeb16eb8eeb2ef8dfe6032f348f6d114a1f0bc
binary_sha256=958ce2a16b6716f550e38667b2bc4c61e04bc0be977c9bf31f594fc30a9bf93c
binary_size=537584
```

The 14-case syscall harness passed:

- all five complete classes;
- selection error and every one of the four transfer-error boundaries;
- a zero-length return with `errno=0` at each of the four bus syscalls,
  proving immediate failure without retry.

Twelve host runner tests and the same twelve tests in the recovery VM passed.
They cover all complete classes, exact predecessor mode/hash/result evidence,
guards, state and counter mutations, helper-line and section ordering,
`05,06` as `raw-other`, rejection of a false `raw-lag` label, output capture
before rejection, and exactly one transport call.

The exact 736,546-byte generated remote program passes BusyBox `sh -n` and
ShellCheck in the recovery VM. No device or device-network session was opened
during implementation, calibration, export, or offline validation.

The selected ignored export is:

```text
artifacts/vm-export-mariner-20260727/mariner-calibrated-20260727/a/mariner-probe
```

## Procedure

Run Mariner at most once on the unchanged accepted Hubble boot. Use one fresh
mode-0700 output child:

```text
python3 experiments/2026-07-27-i2c6-api-path-mariner/scripts/run-mariner-transfer.py \
  --interface en7 \
  --prior-voyager-capture artifacts/runtime-captures/voyager-split-pointer-20260727T182152Z/voyager-runtime-transfer.txt \
  --helper artifacts/vm-export-mariner-20260727/mariner-calibrated-20260727/a/mariner-probe \
  --output-dir artifacts/runtime-captures/mariner-api-path-YYYYMMDDTHHMMSSZ
```

Mariner was invoked exactly once. Do not retry it on this boot.

## Hardware observation

The exact private capture passed the pinned transcript validator. Address
selection returned zero. Each of the four bus syscalls returned exactly one
with `errno=0`:

```text
write pointer=06; read user_pre=3c post=06
write pointer=47; read user_pre=a6 post=47
```

The aggregate result was `raw-pointer-echo`, post `06,47`,
`post_diff_user_mask=0x03`, two completed pairs, four completed bus calls, and
the specified non-live-result status 2.

Transfer-attempt, DMA-start, nonzero-start, and IRQ counters all changed
exactly from `14` to `18`. Boot ID
`cdd23c48-0bd3-4980-95c8-5e054be860d9`, CPUs `0-7`, handoff `ready`, USB
link/service state, and UDC configuration remained unchanged. The helper was
removed after its one invocation and its empty mode-0400 root-owned guard was
retained.

No persistent storage, partition, slot, watchdog, reboot, CPU-control,
regulator, raw-memory, page-control, scan, retry, or delay operation occurred.
The sanitized result is
`results/runtime-mariner-api-path-20260727.txt`.

## Hardware analysis

The result selects the `raw-pointer-echo` branch. Unlike Voyager's direct
DMA-safe `I2C_RDWR` buffers, Mariner's receive path passed through
`i2cdev_read()`'s zeroed buffer and the I2C core's separate zeroed DMA-safe
bounce buffer. The userspace values `3c,a6` never entered either kernel
buffer. A successful path with no hardware write therefore predicted
`00,00`, yet the final CPU-visible bytes were the immediately preceding
pointers `06,47`.

Pointer correlation consequently survives the zeroed kernel bounce-buffer
path; direct i2c-dev DMA-safe buffers and userspace prefill/copyback behavior
are not required to produce it. This favors a lower controller/APDMA source,
including pointer/FIFO residue, DMA direction/address/length programming, or
the completion boundary. Mariner still does not identify the physical writer,
prove a wire byte, or isolate the exact controller register or DMA fault.

The expected live Gemian tuple `d0,c0` did not appear. Values `06,47` are
pointer-correlated fault output and must not be represented as DA9214 register
contents.

## Decision table

| Complete result | Exact tuple | Interpretation and next action |
| --- | --- | --- |
| `raw-expected-live` | `d0,c0` | The ordinary write/read bounce-buffer path recovers the previously observed live values while Voyager's direct DMA-safe path echoed pointers. Localize the defect at the direct-buffer/DMA boundary before changing controller protocol. |
| `raw-pointer-echo` | `06,47` | Pointer correlation survives the different userspace and core buffer path. Favor a lower controller/APDMA source; proceed to the recovered short-FIFO correction only after recording the exact result. |
| `raw-lag` | `47,06` | Each read is one pointer write behind: the first byte matches Voyager's final pointer `47`, and the second matches Mariner's first pointer `06`. Investigate retained controller/APDMA state and completion ordering. |
| `raw-zero` | `00,00` | Consistent with successful copyback from the two zeroed kernel receive buffers without a hardware write, but hardware-supplied zero remains possible. Do not call either byte a DA9214 value. |
| `raw-other` | any other complete tuple | Record exactly and stop. In particular, the former speculative tuple `05,06` is `raw-other`, not `raw-lag`. |
| `raw-error` | incomplete selection or transfer | Preserve the raw capture and stop without retry. Any short return, syscall error, state drift, counter mismatch, or cleanup mismatch is rejected. |

Only `raw-expected-live` exits zero. Every other complete class exits two but
is accepted by the runner as a valid experimental observation. `raw-error`
exits three and is intentionally rejected after capture.

## Evidence boundary

Mariner can discriminate the direct `I2C_RDWR` DMA-safe path from the ordinary
i2c-dev/core bounce-buffer path. It cannot by itself identify the exact
controller register, DMA channel fault, or physical writer. It does not
establish DA9214 register values, regulator control, CPU power support, or a
safe write path.

The build, runner, and one exact hardware invocation are complete. Close
Photon, Kepler, Voyager, and Mariner without repetition. The next causal
change should address the controller's short-transfer data path, informed by
the recovered working Gemian FIFO/PIO behavior for transfers of at most eight
bytes, while keeping DA9214 regulator and Cortex-A72 operations out of scope.
