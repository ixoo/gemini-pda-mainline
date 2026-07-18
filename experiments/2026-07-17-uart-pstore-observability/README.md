# Experiment: establish durable early-boot observability

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-17-uart-pstore-observability` |
| Candidate | L |
| Status | Clean independent rebuild and exact candidate reproduction passed; exported and synchronized to logical `boot2` with a matching full readback; runtime not tested |
| Subsystem | UART0 pinctrl, ramoops/pstore, MT6797 watchdog restart, initramfs diagnostics |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date | 2026-07-17 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Strategy

Device tests are expensive, so each candidate must state an explicit
kernel/DT/configuration hypothesis and predeclare evidence that changes the
next engineering action. Do not spend a device cycle merely changing marker
text or hoping an unchanged kernel behaves differently. Do not repeat an
identical artifact unless repeatability itself is the stated hypothesis and a
new measurement can distinguish the outcomes.

For each test, require all of the following before synchronization:

1. a reviewable kernel, DT, or configuration delta with one distinct intended
   signal per delta;
2. a unique, attributable observation path that survives the likely failure;
3. an outcome table in which every attributable result selects a different
   follow-up; and
4. a stop condition that prevents low-information retries.

Candidate K was cancelled under this rule: it changed only `/init` and could
not make the next action differ. Candidate L establishes the observation
foundation needed by later native-display work. It deliberately multiplexes
three separately identifiable signals into one expensive boot, so it is an
observability acceptance gate rather than a single-variable causal experiment.

## Hypotheses and decision gates

Candidate L makes three evidence-backed kernel changes:

- select the Gemini UART0 route on GPIO97 RX and GPIO98 TX instead of the
  generic MT6797 GPIO234/235 group;
- expose Gemian's observed `0x44410000`/`0xe0000` ramoops reservation with
  identical downstream/mainline dmesg ranges and a mainline console zone that
  exactly overlaps Gemian's primary console zone;
  a `0x20000` mainline pmsg allocation supplies only the required address
  alignment and is never used as cross-version evidence; and
- set MT6797's firmware-defined auto-restart bit whenever TOPRGU watchdog reset
  is armed, avoiding the earlier PSCI/power-key return path.

The storage-inert initramfs writes the unique
`GEMINI_OBSERVABILITY_20260717_L` marker to kmsg, fbcon, and UART, then
opens `/dev/watchdog0`, sends one ownership-handoff ping to cancel the kernel's
inherited keepalive worker, and sends no further pings. USB networking is
retained only as a bonus, fixed read-only report; no interactive shell is
exposed. The kernel local version and USB identity are also L-specific, so a
console record from a failure before `/init` remains attributable. Before
opening the watchdog, `/init` records its sysfs identity, timeout, pretimeout,
and status into the durable console.

Linux 7.1.3 places its console at `[0x444bf000,0x444cf000)`. The pinned Gemian
3.18.79 reference source and the exact active 3.18.41+ binary both read that
range first as console ID zero, producing `console-ramoops`. A binary audit
found that both downstream console zones receive ID zero; therefore the
original second-zone design could lose the candidate record to a duplicate
filename. Candidate L instead enlarges only mainline's pmsg allocation to
`0x20000` for address alignment, placing its console on the unambiguous primary
zone and making all 175 dmesg records line up as well. Mainline snapshots and
clears the inherited header when it initializes that single zone; the pmsg
frontend and `/dev/pmsg0` are compiled out, so no later pmsg payload writes
occur and the allocation must not be counted as evidence. Physical warm-reset
retention and sysfs exposure remain Candidate L runtime gates.

The rows can overlap. First choose the primary decision from the most advanced
surviving evidence in this order: a terminal or late watchdog marker; an
attributable bark plus timed automatic return; another automatic-return result;
a usable UART/pstore/USB channel; early kernel or `/init` entry; and finally no
attributable marker. Then record every secondary channel failure as a follow-up
constraint. For example, a successful reset with silent UART still retires UART
on this unit unless another UART-specific kernel change is made.
`stage=initramfs-entered` is an entry fact, not the selected primary decision
when a later watchdog marker survives.

| Attributable observation | Decision |
| --- | --- |
| `console-ramoops` contains `-gemini-observability-L` but no `/init` marker | Candidate L entered the kernel and failed before the init marker; diagnose the final persisted kernel lines. |
| `console-ramoops` contains `stage=initramfs-entered` | Kernel and `/init` entry are durable facts; use this console path for the next native-display candidate. |
| Last marker is `watchdog0=missing`, `open-failed`, or `handoff-ping-failed` | Fix that specific watchdog discovery/ownership branch before another display test. |
| `watchdog0: pretimeout event` appears after the handoff marker and between `watchdog_wait=15s` and `watchdog_wait=20s`, then automatic return occurs after the handoff ping but before `watchdog_wait=35s` (nominally 32 seconds after that ping) | The Candidate L bark IRQ and dual-stage TOPRGU expiry both occurred; retain this bounded recovery mechanism. |
| A pretimeout line appears only before the handoff marker | It may be inherited probe-time state and is not Candidate L bark evidence; use the ordered collector fields and do not claim dual-stage operation. |
| Automatic return occurs without a pretimeout event in the attributable 15-to-20-second window | TOPRGU expiry/auto-return worked, but Candidate L dual-stage operation is not established; check the ordered event fields, recorded sysfs pretimeout, and IRQ probe log. |
| `watchdog_wait=35s` survives before an automatic return | Reset was later than the nominal expectation; one already-queued kernel keepalive may have raced the ownership handoff, so audit the exact last ping/timing before changing the driver. |
| `watchdog_wait=40s` or `watchdog_expiry_failed` survives | TOPRGU expiry failed; stop display work and audit watchdog mode/reset state. |
| UART marker visible but `console-ramoops` is empty | Use UART for the next test; investigate warm-reset retention separately. |
| `console-ramoops` marker present but UART silent | Treat this unit's UART path as unavailable; continue with pstore and do not retry unchanged UART candidates. |
| Only USB becomes reachable | Capture the persistent markers and USB evidence, then keep USB as a secondary channel; it does not replace the pstore/watchdog gate. |
| No unique marker on any channel | The attempt is unattributable; do not repeat the same image. Improve pre-kernel selection evidence or the observation mechanism first. |

One attended selection is sufficient for this gate. Hardware support remains
unconfirmed until the exact built artifact is tested and its surviving evidence
is recorded.

## One-shot attended procedure

1. Boot known-good Gemian, keep external power connected, and start the private
   collector before selecting `boot2`:

   ```sh
   ./scripts/collect-device-pstore \
     --target gemini@192.168.1.50 \
     --wait-for-cycle --ask-sudo-password \
     --output artifacts/device-pstore/candidate-L-runtime-1
   ```

2. Candidate L's exact `boot2` write/readback is now recorded in
   `results/boot2-write-candidate-l-20260717.txt`. Select that verified logical
   `boot2` once with the silver button.
   Record any UART, screen, backlight, LED, USB, and automatic-return timing.
   Screen, backlight, and LED behavior are contextual observations only in this
   experiment: they neither establish a Candidate L kernel delta nor justify an
   unchanged retry.
3. Allow the watchdog reset plus the normal Gemian boot to complete. Do not
   declare no return before 120 seconds. The collector may continue waiting for
   up to its default 300-second bound.
4. If Gemian has not returned after 120 seconds, record the state and capture
   any UART or USB report first. Then use one normal power-key press, not a long
   hold, to test a key-gated return while preserving RAM if the platform permits.
   A hard power-off or battery loss can destroy the only ramoops evidence; stop
   and report before doing that unless recovery requires it.
5. Inspect the collector's `candidate-l-evidence.txt`, exact
   `pstore/console-ramoops`, cycle record, metadata, and checksums. Apply the
   precedence and outcome table above. Do not perform a second selection of
   the same image.

## Safety boundary

The initramfs mounts only devtmpfs plus read-only procfs and sysfs. The pmsg
frontend is compiled out. It does not
access eMMC, raw memory, framebuffer devices, I2C, or generic reboot commands,
and its optional TCP endpoint emits a fixed read-only report rather than a
command interpreter.
It deliberately opens the watchdog once, sends one post-open handoff ping, and
then holds the file descriptor without further pings; on the intended MT6797
path, the driver advertises a 31-second timeout. Because the retained bark IRQ
uses dual mode and integer division when SPI137 probes, nominal bark/reset
boundaries are about 16/32 seconds. One already-queued watchdog-core work item
can race the ownership handoff, so the initramfs does not declare failure until
40 seconds after the handoff ping. Any `boot2` synchronization is a
separate operation under the standing repository policy and must pass its full
backup, power, flush, and readback gates. Never substitute another partition or
reboot during the write operation.

## Associated code

- `patches/v7.1.3/0079-arm64-dts-mediatek-gemini-fix-UART0-pinmux.patch`
- `patches/v7.1.3/0080-arm64-dts-mediatek-gemini-add-ramoops-backend.patch`
- `patches/v7.1.3/0081-watchdog-mtk-set-MT6797-auto-restart-mode.patch`
- `configs/gemini-observability.fragment`
- `initramfs/init` and `initramfs/usb-report`
- `scripts/build-observability-candidate.sh`,
  `scripts/build-observability-dtb.sh`, and
  `scripts/validate-observability-dtb.py`
- `scripts/build-initramfs.sh` and `scripts/validate-init-contract.sh`
- `scripts/test-validation-mutations.sh`
- repository helper `scripts/collect-device-pstore`
- preflight recovery evidence in
  `results/preflight-pstore-recovery-20260717.txt`
- cross-version offset/signature evidence in
  `results/cross-version-ramoops-layout-20260717.txt`
- exact active-kernel binary and live-header evidence in
  `results/exact-live-ramoops-binary-audit-20260717.txt`
- exploratory build, DT schema, exact LK binding, and negative-validator evidence
  in `results/exploratory-build-validation-20260717.txt`
- clean independent source rebuild, normalized package/candidate comparison,
  final negative-validator run, and host export evidence in
  `results/final-build-reproduction-20260717.txt`
- logical-`boot2` backup, write, sync, block flush, and full local readback
  evidence in `results/boot2-write-candidate-l-20260717.txt`

The final fresh-source raw image is 6,522,880 bytes with SHA-256
`5291832296106d36bc919671960b6150e530467057540a195bcf59e582ebb4c9`.
It was independently reproduced from a distinct fresh Linux 7.1.3 extraction,
exported under the Git-ignored host artifacts tree, zero-padded to 16 MiB, and
written only to the live-resolved logical `boot2`. The synchronized and
block-flushed partition plus a separate full local readback both have SHA-256
`22d6ea23053514c4b5ad5cc2cf9ecb41fb800318533cbe94604302134e80daea`.
This proves artifact identity and partition synchronization only. Candidate L
has not been selected or runtime-tested, so UART, pstore retention, watchdog
restart, kernel entry, and display behavior remain unproven.
