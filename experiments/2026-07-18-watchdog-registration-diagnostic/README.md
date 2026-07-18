# Experiment: isolate MT6797 watchdog registration

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-18-watchdog-registration-diagnostic` |
| Candidate | M |
| Status | Built reproducibly; synchronized and fully read back from logical `boot2`; runtime not tested |
| Subsystem | MT6797 TOPRGU watchdog platform probe, optional bark IRQ, ramoops observation |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date | 2026-07-18 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question

Candidate L strongly reached its tracked external `/init`, but
`/dev/watchdog0` was not a character device at checks `remaining=10s` through
`remaining=5s`. Does the optional SPI137/SYSIRQ bark path prevent
`mtk_wdt_probe()` from reaching watchdog-core registration, or does the failure
remain when the basic MMIO watchdog has no interrupt?

## Evidence and correction

The [Candidate L registration audit](../2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt)
establishes the exact boundary:

- `CONFIG_WATCHDOG`, `CONFIG_MEDIATEK_WATCHDOG`, devtmpfs, and the implicitly
  enabled `watchdog@10007000` node are built in;
- the watchdog inherits root `interrupt-parent = <&sysirq>`;
- Linux 7.1.3 MediaTek SYSIRQ accepts falling edge, programs its polarity
  inverter, and presents rising edge to the parent GIC; and
- `mtk_wdt_probe()` requests a present optional bark IRQ before
  `devm_watchdog_register_device()` and returns if the request fails.

Therefore Candidate M does not change the interrupt to rising or level-high.
Those guesses would alter the evidenced physical polarity or sensitivity.
Instead it omits the optional `interrupts` property in the final diagnostic
DTB. This also matches bsg100's independently hardware-tested mainline DTB,
which registered `10007000.watchdog` without a watchdog interrupt property.
That corroboration is input, not proof for this unit or this kernel revision.

## Controlled delta

Candidate M derives from the exact final Candidate L artifact. It keeps these
bytes and contracts unchanged:

- Linux 7.1.3 `Image.gz` and the observability kernel configuration;
- forced command line, one-CPU policy, `clk_ignore_unused`, UART0 pinmux, and
  ramoops layout;
- LK Android-v0 addresses, `bootopt`, page size, gzip-plus-appended-DTB layout,
  and loader-retained simplefb clocks; and
- MT6797 auto-restart policy and the 31-second watchdog timeout.

It changes only:

1. final DTB property `/watchdog@10007000:interrupts` is deleted; and
2. initramfs `/init` becomes a unique Candidate M measurement program.

The second change is an observation mechanism, not a second hardware
hypothesis. Before any watchdog open, it reports:

- `/dev/kmsg` write success;
- read-only procfs and sysfs mount status, with a static hold instead of a
  false absence result when sysfs is unavailable;
- the live kernel DT watchdog node and absence of its `interrupts` property,
  with a static hold if LK restored the property or the live tree is
  unavailable;
- `10007000.watchdog` platform-device presence and driver symlink;
- watchdog class and character-device presence;
- every ramoops-named platform device and its driver symlink; and
- the last bounded `mtk-wdt`, watchdog, ramoops, pstore, or `10007000` kernel
  log lines, excluding Candidate M's own marker traffic.

Each one-second discovery line repeats a compact platform, driver, watchdog
class, and device-node summary. A screen transition during the countdown is
therefore still attributable even if no retained log survives.

No userspace USB-network configuration or service is started; the unchanged L
kernel still contains its compiled gadget capability. UART remains a secondary
mirror only. The program never opens storage, framebuffer, raw memory, I2C, or
a command shell.

## Reproducible build

The actual non-primary recovery VM invocation is:

```sh
DEV_VM_NAME=gemini-pda-build-recovery-20260717 \
  ./scripts/dev-vm run \
  /mnt/gemini-pda-mainline/experiments/2026-07-18-watchdog-registration-diagnostic/scripts/build-watchdog-registration-candidate.sh \
  --baseline /mnt/gemini-pda-mainline/artifacts/vm-export/boot-candidates/candidate-L-final-fresh-ee32f68
```

The script requires a clean repository, exact Candidate L manifest and
components, Linux/aarch64, and source epoch zero. It records GNU cpio, gzip,
`fdtput`, DTC, and Python versions, validates both component deltas, validates
the complete Android-v0/LK container, pins the 16 MiB capacity boundary, and
has no device or flashing interface. The default output remains in guest
`~/artifacts/boot-candidates/` until explicitly exported.

## Decision oracle

| Attributable result | Decision |
| --- | --- |
| Live DT watchdog `interrupts=present` or live node unavailable | The packaged-DTB delta is not established after LK handoff. Stop without opening the watchdog; inspect final FDT selection or LK mutation. |
| `watchdog0=present`, identity `mtk-wdt`, pretimeout `0` or unavailable, then an automatic return near 31 seconds | The optional IRQ path blocked Candidate L registration and the basic TOPRGU reset path works. Retain the basic watchdog; recover pstore and instrument SPI137 separately before restoring bark. |
| `watchdog0=present`, but `watchdog_wait=40s` or `watchdog_expiry_failed` survives | The IRQ path blocked registration, but TOPRGU start/expiry or auto-restart still fails. Use the recorded sysfs, mode-policy, and pstore state; do not change IRQ polarity. |
| `watchdog0=missing` after the bounded wait | The optional IRQ path is exonerated. Add exact `mtk_wdt_probe()` stage/errno instrumentation before another device cycle. |
| Platform device absent | Inspect final post-LK FDT mutation or platform population; do not modify the driver first. |
| Platform device present but unbound | Use the filtered probe log; instrument match, MMIO map, and registration stages if the errno is not durable. |
| Automatic return plus surviving Candidate M `console-ramoops` | Basic watchdog reset and warm-reset persistence are both established without bark/pretimeout. |
| Screen switches off | Context only. It is not evidence that watchdog discovery or expiry caused the display transition. |

No result from this candidate proves SPI137 polarity, pretimeout delivery,
native display support, UART function, or stable userspace. Do not repeat M
unchanged after its first attributable outcome.

## Attended procedure

This procedure becomes active only after the candidate has passed its exact
build, component-delta, LK-container, size, checksum, and logical-`boot2`
write/readback gates.

1. Keep external power connected and start the cycle-aware private collector
   from known-good Gemian:

   ```sh
   ./scripts/collect-device-pstore \
     --target gemini@192.168.1.50 \
     --wait-for-cycle --ask-sudo-password \
     --output artifacts/device-pstore/candidate-M-runtime-1
   ```

2. Select the verified logical `boot2` once with the silver button. Record the
   complete last visible M line, screen/backlight state, serial bytes if any,
   and whether return is automatic. Do not press power during the first 120
   seconds.
3. If Gemian returns automatically, allow the collector to finish. If it does
   not return after 120 seconds, record the state before one normal power-key
   press. A manual start does not satisfy the watchdog-return criterion and can
   destroy retained RAM evidence.
4. Apply the first matching decision-oracle row. Do not select the same image
   again unless a new independent measurement is explicitly added.

## Safety boundary

The initramfs mounts devtmpfs, read-only procfs, and read-only sysfs. All probe
diagnostics are reads except console writes to `/dev/kmsg` and tty devices.
It verifies the live DT rather than assuming the packaged property deletion
survived LK; an unavailable or present live interrupt property stops the test
before the watchdog is opened.
Only after `/dev/watchdog0` exists does it open the watchdog once, send one
ownership-handoff ping, retain the descriptor, and send no further pings. It
does not request a generic reboot. Without the optional IRQ, pretimeout and
dual-stage mode are intentionally absent; the expected reset is the standard
single-stage TOPRGU timeout. A failure may leave the device waiting for a
manual power key, so the known-good primary image and private `boot2` backup
remain mandatory.

## Associated code

- `initramfs/init`
- `scripts/build-watchdog-registration-dtb.sh`
- `scripts/validate-watchdog-registration-dtb.py`
- `scripts/build-initramfs.sh`
- `scripts/validate-initramfs-delta.sh`
- `scripts/validate-boot-delta.py`
- `scripts/build-watchdog-registration-candidate.sh`
- Candidate L source and runtime audit in
  `../2026-07-17-uart-pstore-observability/`

## Result

Two clean Linux/aarch64 VM builds from repository revision
`2bcb668e566e1cee39da3bc002172c1d219da22c` are recursively byte-identical.
The final artifact is:

- raw boot image: `gemini-watchdog-registration.boot.img`;
- raw size: `6522880` bytes;
- raw SHA-256:
  `a0a6c520fcc170ee0a422e66384559c50100ee65645811c331149beec8c347da`;
- exact Candidate L `Image.gz` SHA-256:
  `0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3`;
- Candidate M DTB SHA-256:
  `c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379`;
  and
- Candidate M initramfs SHA-256:
  `e0edeceb127e08cd0b01749e289474479ccebe8f33995d39014d7dcf8c5b25fc`.

The artifact is exported privately under
`artifacts/vm-export/boot-candidates/candidate-M-watchdog-registration-2bcb668e/`.
Its exact 16 MiB padded image SHA-256 is
`53234ca7e81b23c77b0910e1e2bcdf54dc7a2984e28bbe9baac30ad26eeb7c2b`.
The live GPT resolved one logical `boot2` at `/dev/mmcblk0p30`; all identity,
root, mount, holder, writable, size, and power gates passed. A fresh full
mode-0600 private backup was preserved before the write. The write completed
with `conv=fsync,notrunc`, explicit sync and block flush, and both the complete
device checksum and a separately copied full readback match the padded image.
The device remains in Gemian; no reboot or shutdown was performed.

See the [independent build record](results/final-build-reproduction-20260718.txt)
and [logical-`boot2` write/readback record](results/boot2-write-candidate-m-20260718.txt).
Runtime remains untested, so no hardware-support state changes.
