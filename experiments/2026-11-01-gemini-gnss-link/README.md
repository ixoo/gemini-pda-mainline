# Experiment: GNSS driver first step, the STP link and a silent device

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-gnss-link` |
| Status | `running`: patches 0418-0419 written and host-tested; no device test yet; the receiver is not started by this code |
| Subsystem | MT6797 CONSYS STP link, `drivers/gnss` |
| Device variant | Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | project session, device custody with the parent session |
| Tracking issue | none |

## Question or hypothesis

What does a maintainable GNSS driver need that the station kernel lacks, and
can its transport be added without changing Wi-Fi?

Hypothesis for the first device test: on a station running Wi-Fi, a client can
take over the BTIF interrupt, continue the STP link the start chain left, get a
firmware answer in both directions and give the interrupt back, with Wi-Fi
unaffected. No radio action is part of this test.

## Where the driver stands against the documents

The [GNSS document](../../docs/hardware/gemini-gnss.md) and the
[reverse-engineering record](../2026-11-01-gemini-gnss-re/README.md) list what a
driver needs. Checked against the clean series (0390-0414):

**Observed on the device, by the Wi-Fi work:**
- Common init runs at every CONSYS start, with both ROM patches, the
  calibration exchange and the rails. Stations 25 to 29 start Wi-Fi this way,
  so this prerequisite is met. The GNSS document's "same blocker as for Wi-Fi"
  was written against the older state and is corrected.
- The BTIF clocks stay on and the link's sequence state stays in the owner after
  the chain.

**Read from the code (`mt6797-consys.c`, `mt6797-wmt.h`):**
- Every STP exchange is one-shot. `mt6797_wmt_full_exchange` takes the BTIF
  interrupt, sends one command, waits for one reply and frees the interrupt.
  After common init nothing reads BTIF. The stream parser also refuses any
  frame that is not the one expected task.
- **This is the missing prerequisite.** A GNSS receiver sends frames whenever it
  likes, so it needs a receive path that stays on.
- No code in the clean series sends GPS function-on or drives GPIO 69.
- `CONFIG_GNSS=y` is already in the station configuration, so a GNSS driver adds
  a module and should not change `Image`.

**Read from the retained decompile this session:**
- The vendor receiver's GFNS checksum covers bytes 1 to 4 of the header
  (`FUN_0001a89e` and `FUN_0001a944` in `libmnl`). On MCU-to-host frames byte 1
  carries the channel, so the channel byte counts. The document's formula only
  showed the host-to-MCU case.

**Inferred:**
- The `gnss` core fits. Open and close hooks and a byte stream are all it needs,
  and `gnss_insert_raw` is safe here because its only requirement is
  serialization, which the link lock provides, and an open device, which
  attach and detach guarantee.
- Task 2 stays silent until GPS function-on. No document shows otherwise; the
  device test checks it.

**Unknown (the first three decide the test below):**
- Whether the firmware sends anything on BTIF while nobody listens. If it does,
  the bytes sit in the FIFO, and an overflow would lose frames.
- Whether the BTIF path still answers once Wi-Fi firmware is running and after a
  long idle. Every observed WMT exchange ran during the start chain.
- Whether a Wi-Fi station tolerates BTIF interrupts next to the HIF traffic.
- Everything the GNSS record already lists: the 49-byte `MNL_INIT_CFG` values,
  whether empty NVRAM is tolerated, the keep-alive period, the ACK layout, and
  whether a physical LNA is populated.

Only the Bluetooth draft (0116-0119) has ever had a persistent link, and it never
ran on hardware; its profile excludes common init, so it was not combined with
Wi-Fi. This work reuses its engine, so its behaviour is not evidence here.

## What this step adds

[0418](../../patches/proposals/0418-soc-mediatek-mt6797-consys-run-the-STP-link-for-task.patch)
adds `mt6797-stp-engine.h` and exports `mt6797_consys_stp_attach` and
`_detach`. [0419](../../patches/proposals/0419-gnss-add-the-MT6797-CONSYS-receiver-link-only.patch)
adds the `gnss-mt6797` module and its GFNS receive parser.

- **Wi-Fi is not touched unless the device is opened.** The link runs only
  between open and close of `/dev/gnss0`. Without an open the interrupt stays
  released and no path changes. The owner registers one new child platform
  device; that is the only change a Wi-Fi-only boot has.
- **The start chain runs first.** Attach takes the owner lock, so it waits for a
  start in progress, and returns `-EAGAIN` if common init has not completed.
- **Link check.** Each attach repeats the STP option query
  (`01 04 01 00 04`) that the start chain sends during negotiation and logs the
  reply. It is a read, already sent at every start, and proves both directions.
- **Failure.** Malformed input, a refused frame, a 2 s ACK timeout or a check
  timeout stop the link until CONSYS reloads. Later opens return `-EIO`. Power,
  clocks and rails stay, and Wi-Fi does not use this link.
- **No radio action.** There is no WMT function control, no GPIO 69 and no GFNS
  transmit path in this code. Reads stay silent and writes return `-EOPNOTSUPP`.
- **Unload.** `gnss-mt6797` holds `mt6797-consys`, so a CONSYS reload needs the
  GNSS module removed first. Nothing loads it at boot.

### Deviations from the Bluetooth draft

- It uses the one-shot path's FIFO room rule (16 bytes on `LSR & 0x40`, 8 on
  `LSR & 0x20`); the draft wrote 16 on `0x20`.
- An interrupt with no source returns `IRQ_NONE`, so a stuck line reaches the
  core's spurious-interrupt detection.
- An unsolicited WMT event is not mistaken for the check's reply. The first one
  is kept and logged, since it is what this test wants to see.
- The link stops at the last detach, not at the end of negotiation.

## What was and was not tested

| Check | Result |
| --- | --- |
| `run-tests.sh` on the actual headers, ASan and UBSan, in the dev VM | passes: routing, window, ACK retirement, unbind, largest frame, stream across unbind, fail-stops; GFNS framing, channel, split at every chunk size, refusal and restart |
| `mt6797-consys.o`, `mt6797.o` in the dev VM, W=1, station configuration | no warnings |
| `checkpatch --strict` on both patches | only the MAINTAINERS note for new files |
| Buildbox build | see [Build](#build) |
| Interrupt handler, timer, teardown | review only |
| On the device | nothing |

## Build

Pending at this commit.

## Device test T1 (no radio action)

Run by the parent session as custodian. Hypothesis as above. The unique
observation is what the firmware has sent on BTIF since the start chain ended,
and whether the link answers next to a running Wi-Fi.

Setup: a station with Wi-Fi up, then the modules from the package, swapped by the
reviewed reload path. Record `uname -a`, the boot ID and the module hashes.

```sh
grep -c mt6797-stp /proc/interrupts       # 0 before any open
insmod gnss-mt6797.ko
ls -l /dev/gnss0; cat /sys/class/gnss/gnss0/type
grep -c mt6797-stp /proc/interrupts       # still 0: loaded, not opened
timeout 60 cat /dev/gnss0 | wc -c         # expect 0 bytes
dmesg | grep -E 'STP link|mt6797-gnss'
grep -c mt6797-stp /proc/interrupts       # 0 again: the interrupt was given back
```

Then two more 60 s opens, one 10 minute open with a running ping through
`wlan0`, and `rmmod gnss-mt6797`. Finish with one CONSYS and `mac` reload, as the
Wi-Fi cycle test does, and the gateway ping.

Expected log on each open: `STP link running`, `STP link check: result=0 reply=10
bytes 02 04 06 00 00 04 ...`, `STP link halted: failed=0 busy=0 ...
wmt-unsolicited=0`, `closed: 0 GFNS frames, 0 refused, 0 dropped`.

| Observation | Meaning | Next |
| --- | --- | --- |
| All opens pass, Wi-Fi unchanged, zero unsolicited | The prerequisite holds | Ask the owner to approve T2 below |
| Passes, with unsolicited WMT frames or discarded tasks | The firmware talks while nobody listens | Record the bytes, then decide whether the link must stay up from the start chain, coordinated with Wi-Fi |
| Check times out (`result=-110`) | The firmware does not answer on BTIF after the WLAN start | Stop. No retry. Diagnose offline; the next test compares a CONSYS start without WLAN |
| `result=-71`, or the reply differs | Unexpected reply bytes | Keep the bytes; correct the expected reply offline |
| `STP link stopped (-71)` at the first open | Stale or lost bytes in the FIFO | Keep the counters; the link must start listening earlier |
| Task-2 frames or GFNS counts above zero | The receiver side is talking without function-on | Stop and report; this contradicts the inference above |
| Wi-Fi throughput or join regression during an open | The link disturbs Wi-Fi | Stop, close the device, report |

**Stop rules:** any Oops, warning or call trace; `mt6797-stp` counts rising fast
while idle (a stuck line); `irq N: nobody cared`; Wi-Fi lost for more than the
ping's normal gap; or any firmware assert. On a stop, keep the log, close the
device and remove the module. A timeout does not authorize a retry in the same
CONSYS lifetime.

## Next step, T2 (radio action: not admitted)

Nothing below is in the code, and nothing runs until the owner approves it. The
protocol to review would be:

- **Effect.** WMT GPS function-on (`01 06 02 00 02 01`), GPIO 69 high, then the
  GFNS sequence: `MNL_INIT`, `MNL_INIT_CFG`, `MNL_UTC_INIT`, keep-alive,
  `HOST_START_GNSS`; on close the reverse, ending with function-off and
  GPIO 69 low.
- **Hypothesis.** H1 of the
  [reverse-engineering record](../2026-11-01-gemini-gnss-re/README.md): type
  `0x0a` frames carrying NMEA text appear without an NVRAM exchange.
- **RF.** GNSS only receives (inferred from the documents; no transmit path is
  known for it). The firmware's coexistence with a running Wi-Fi is unknown, so
  the first run keeps Wi-Fi up with `wlan0` idle.
- **Firmware and calibration.** No new file. `MNL_INIT_CFG` needs its 49 bytes,
  which include clock values normally read from `ML4A_000` in `nvdata`. The first
  run would use the documented defaults (26 MHz, 2000 ppb), so no calibration is
  read or written.
- **Privacy.** A fix is location data. Logs would keep frame types, counts and
  sentence names only, never sentence text. Sentences stay in a private path.
- **Bounds.** One open, a fixed run length, a stop on any firmware assert, no
  retry in one lifetime.
- **Still to do offline first:** recover the exact `MNL_INIT_CFG` field offsets
  and the `0x7e` and `0x35` ACK layouts from the retained decompile, and add the
  GFNS transmit path with host tests.

The cheap read-only Gemian check from the GNSS record (H0: does any FLP client
enable the offload path) is separate. It tells whether a stock session could
serve as a reference, and it needs the parent session as custodian.

## Associated code

- [test-stp-engine.c](test-stp-engine.c), [test-gfns.c](test-gfns.c) and
  [run-tests.sh](run-tests.sh): `run-tests.sh PREPARED_LINUX_SOURCE`. No hardware.
