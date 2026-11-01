# Experiment: GNSS driver first step, the STP link and a silent device

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-gnss-link` |
| Status | `parked`: T1 passed; T3's start caused a firmware exception, inferred to be because the engine needs `MNL.bin`, which this device lacks; the receiver has produced no data |
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
- `CONFIG_GNSS=y` is already in the station configuration, so the driver only
  adds a module. `Image` still changes, because it embeds the configuration
  (see [Build](#build)).

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
| Buildbox build | passes; see [Build](#build) |
| Interrupt handler and teardown | exercised by T1; the failure paths and the ACK timer's expiry were not triggered |
| On the device | T1, below. The receiver was not started |

## Build

Buildbox-2, commit `7ab57de0`, job `7ab57de0…-mt6797-a53-station-m1`, 590
patches, inventory `0877cb7d…`, validated and fetched. No device action.

| File | SHA-256 |
| --- | --- |
| `Image.gz` | `ee620135256732d4d095d6210a7bb177c3cc55daf82b01c5327e2b57951a41c6` |
| `gnss-mt6797.ko` | `024591361ab5819a6fdb5ca2d26f09d0150f366dea7baab88d6ab1b865d9e483` |
| `mt6797-consys.ko` | `9c47dacad5bd70d62ac6af235d650904608fb871432456e1549fdd748e7fdd42` |

Compared with the jack-detection package `d053ffd1` (inventory `13d0656e…`), the
series before these patches:
- Observed: the configuration differs by the one `CONFIG_GNSS_MT6797=m` line, the
  Gemini DTBs are identical, and among modules only `mt6797-consys.ko` changes and
  `gnss-mt6797.ko` is new.
- `Image.gz` differs (`51e5c1f8…` there). Inferred: only through the embedded
  configuration (`CONFIG_IKCONFIG=y`), whose size shifts later symbols. The byte
  differences were not walked one by one.

## Device test T1 (no radio action)

Run by the parent session as custodian. Hypothesis as above. The unique
observation is what the firmware has sent on BTIF since the start chain ended,
and whether the link answers next to a running Wi-Fi.

Setup: a station with Wi-Fi up, either booted from this package or from
`d053ffd1` with the two modules above swapped in by the reviewed reload path. The
release string matches and the station has no module versioning. Record
`uname -a`, the boot ID and the module hashes.

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

## T1 result: passed (2026-11-01)

Station 30, boot `4ac95e75`, package `b3cfdeb6`, `Image.gz` `ee620135…`, with the
same `gnss-mt6797.ko` and `mt6797-consys.ko` hashes as above. Run by the custodian;
log and full `dmesg` are private under `artifacts/station-work-30/boot-4ac95e75/gnss-t1/`.
Audio modules were loaded and idle.

**Observed:**
- Loaded but not opened, `mt6797-stp` is absent from `/proc/interrupts`.
  `/dev/gnss0` exists with type NMEA.
- Three 60 s opens and one 600 s open each read 0 bytes and logged
  `result=0 reply=10 bytes 02 04 06 00 00 04 df 0e 68 01`, the same option bytes
  as at negotiation.
- The link's sequence numbers continued across opens (tx 2, 3, 4, 5). Every halt
  shows `failed=0 busy=0 discarded=0 dup=0 wmt-unsolicited=0`, with rx, tx and ACK
  counts rising by exactly the one query per open. No GFNS frame arrived.
- The interrupt count held at 17171 for all 20 samples of the 600 s open. The line
  is gone after each close, and there was no `nobody cared`.
- During the 600 s open: ping through `wlan0` 300/300, 11.9 ms average, state
  `COMPLETED`.
- `rmmod` of `gnss-mt6797`, `mac` and `mt6797-consys`, then reload: common init
  285/285, join on 5200 MHz, lease, gateway 3/3. No Oops, warning or call trace.

**What this settles:** the firmware sent nothing on BTIF between the start chain
and the first open, or in up to 600 s of listening. The link answers next to a
running Wi-Fi, and task 2 is silent without function-on.

**Limits:** one boot. Wi-Fi was checked by ping only, not throughput. There was
little link traffic, so a loaded link and all failure paths remain untested. The
longest idle before an open was about 5 minutes.

## Offline findings for T2 (retained `libmnl` decompile, firmware strings)

- **The configuration can be left out.** The vendor sender `FUN_0001b846` sends
  type `0x14` with zero length when it has no configuration. The firmware has
  both `GFNS_REQ_MNL_INIT: Use AP cfg` and `Use Default cfg`. Inferred: zero length
  selects its defaults, so a first start needs none of the 49 bytes, and no
  clock calibration. This replaces H3 for the first run.
- **Vendor order** (`mtk_gps_ofl_mode_update`): `0x13`, `0x14`, `0x44` (bitmap),
  `0x83`, NV download open, then `0x40`. Stop is `0x41`.
- **`0x83` payload** (`FUN_0001ee60`): `u16` year minus 1900, then `u8` month from
  zero, day, hour, minute, second, in UTC. Bytes 8-9 are zero. Bytes 7, 10 and 11
  are never written, so they are stack contents there.
- **`0x7e` payload** (`FUN_00018ed8`), 28 bytes in order: `recv` as two `u32`s
  (low, then multiples of 0x10000), `proc`, `pdrop`, `rdrop` (always 0), `pkt`,
  window (always 0x10). It is sent once 0x800 new bytes arrived, or right after
  the firmware's `0x36`, which also resets the counters and enables these ACKs.
- **Keep-alive** (`FUN_0001b0bc`) has no timer: type `0x76` goes out when a progress
  counter passes 0x400 bytes more than at the last one. Which counter
  `FUN_0001a3d0` returns is not established.
- The GPS AFE words are already written by the CONSYS start, and no patch in the
  tree uses GPIO 69.

**Still unknown:** whether the engine runs without the NV download; whether the
keep-alive matters at this traffic level; whether a physical LNA exists; whether
Wi-Fi and GNSS tolerate each other without the vendor's de-sense packet.

## T2: first receiver start (radio action, admitted)

The owner approved both stages below on 2026-11-01. This covers exactly these
effects. Anything else, including a retry outside the stop rules, needs asking
again. Stage A is
[0421](../../patches/proposals/0421-soc-mediatek-mt6797-consys-let-a-client-send-and-swi.patch)
and [0422](../../patches/proposals/0422-gnss-mt6797-turn-the-receiver-on-while-the-device-is.patch).
Stage B has no code yet.

**Hypothesis:** H1 of the [reverse-engineering
record](../2026-11-01-gemini-gnss-re/README.md), with default configuration: type
`0x0a` frames carrying NMEA text appear without an NV download.

**Effects, on open of `/dev/gnss0`:** the T1 link check; WMT GPS function-on
(`01 06 02 00 02 01`, the opcode other functions use with their own flag byte);
then `0x13`, zero-length `0x14`, `0x44` with bitmap 0 (delete nothing), `0x83` from
the system clock, and `0x40`. The `0x7e` ACKs and `0x76` keep-alive follow as
above. On close: `0x41`, 100 ms, function-off, then the link halts.

The vendor's NV download open is left out on purpose; that is what H1 tests.

**Not used:** no firmware file beyond what every start loads; no calibration read
or written, including `ML4A_000` and NVRAM; no EPO, SUPL or network; NV requests
from the firmware are counted and not answered; no partition write.

**RF:** GNSS only receives (inferred: no transmit path is documented for it). Wi-Fi
stays on as the owner's access point allows, with no new channel or transmit power.

**Two stages, one boot each at most:**

| Stage | Change | Length | Decides |
| --- | --- | --- | --- |
| A | Module only, GPIO 69 left alone | One 5 minute open, `wlan0` idle, then one with ping | Does the firmware produce frames, and does Wi-Fi survive function-on and function-off? |
| B | GPIO 69 high while open (needs a DT patch and a boot2 write) | One open of at most 20 minutes, with the device near a window or outdoors | Does a fix arrive, and does the GPIO change signal levels? |

| Observation in A | Next |
| --- | --- |
| `0x0a` frames with `$G` sentences | Go to B |
| Frames, but only NV requests (`0x40`-`0x49`) | The engine waits for NV: H1 is refuted; design the NV exchange offline |
| Function-on answers, then silence | Check the default-config path offline; no blind retries |
| Function-on refused or timed out | Stop; function-off; CONSYS reload |

Stage A commands, with the modules from the package loaded after Wi-Fi is up. The
output file is location-capable, so it stays under private `artifacts/`:

```sh
timeout 300 cat /dev/gnss0 > gnss-a1.txt          # wlan0 idle
dmesg | grep -E 'STP link|WMT GPS|GFNS type|closed:|mt6797-gnss'
# then the same with a ping through wlan0 running, to gnss-a2.txt
rmmod gnss-mt6797
```

Finish with one CONSYS and `mac` reload and a gateway ping. Publishable from the
files: byte counts, sentence names and their counts, and how many lines do not
start with `$`.

**Stop rules:** any firmware assert, link stop, Oops or warning; Wi-Fi lost for more
than the normal ping gap; battery or SoC temperature outside the station's usual
range. On a stop: close the device, unload, CONSYS reload. No retry in one CONSYS
lifetime.

**Privacy:** a fix is location data. Kernel logs keep frame types and counts only.
Sentences are read through a private path under `artifacts/`, and only sentence
names, satellite counts and carrier-to-noise summaries are published. Latitude,
longitude and time-of-fix text are not.

**Separate:** the read-only Gemian check (H0) tells whether stock could serve as a
reference. It is not needed for T2.

## T2 stage A result: stopped (2026-11-01)

Station 30, boot `4ac95e75`, modules from `fff5cf30` (`gnss-mt6797` `047d7da2…`,
`mt6797-consys` `c944a664…`, `mac` `6f626e6c…`, core `425b8add…`). Run by the
custodian; private evidence under `artifacts/station-work-30/boot-4ac95e75/gnss-t2a/`.
The one approved open was used and not retried. No sentence was produced.

**Observed:**
- Link check passed, and `WMT GPS function on: result=0 reply=5 bytes 02 06 01 00 00`.
  The firmware accepted function-on, the first time on mainline.
- About 5 ms later: `STP link stopped (-71)`. The start sequence had gone out
  (`tx=7`, `sent=51`). No frame reached the GFNS client (`received=0`), and the log
  does not hold the refused bytes.
- About 1.2 s later Wi-Fi's command path stopped answering: `join stopped:
  status=-110`, connection lost, scans refused. `wlan0` had been idle.
- Function-off then returned `-5`, because the link had stopped. CONN was never told.
- Unloading all three modules powered CONN off, but two reloads, one including the
  core, each stopped with `WMT negotiation: result=-16 phase=1` before sending
  anything. No Oops or warning. The soc read 30.7-31.4 C.
- The system clock read 1970, so `0x83` carried that date.

**Read from the public vendor parser (`stp_core.c`):**
- Tasks 5 and 6 use their own framing: no checksum check, payload, then two CRC
  bytes that are discarded. Outside debug mode, task 5 is a firmware assert that
  starts a whole-chip reset. In debug mode, task 6 is the runtime firmware log.
- My engine refuses both tasks with `-71`, the error seen. So do other shapes it
  counts as malformed, such as a sequence outside the window. The vendor skips bytes
  until it sees a frame start.

**Inferred; the bytes are what decides:**
1. The firmware sent a task 5 assert, caused by something in the start sequence
   (an empty `0x14` and the 1970 date are the suspects). That alone explains Wi-Fi
   dying.
2. Or it sent a harmless frame that my engine refused. Then Wi-Fi died because
   the host stopped reading and acknowledging, which left firmware blocked.

**Wrong in this record:** "Wi-Fi does not use this link" held only for host code.
The firmware shares one microcontroller, so a failed GNSS link can take Wi-Fi with
it. Stopping interrupts on a link failure is the wrong policy once GNSS runs.

**Inferred cause of the `-16`:** of the checks that return `-EBUSY` at that point,
with `default-rx=0`, the likely one is the setup's refusal of a nonempty BTIF RX FIFO. BTIF sits outside CONN, so an unload does not clear it. T1 left it
empty, which is why T1's reload worked.

## D1: read the stale bytes and recover (no radio action beyond a normal start)

[0429](../../patches/proposals/0429-soc-mediatek-mt6797-consys-start-despite-stale-BTIF-.patch)
logs up to 64 stale BTIF bytes at start and lets the existing clear remove them.

**Hypothesis:** the FIFO holds the firmware's next bytes, and CONSYS then starts.
**Unique observation:** those bytes, which survive only until this boot ends.

| Observation | Meaning | Next |
| --- | --- | --- |
| Text or a task 5 header in the bytes | Firmware assert likely | Find the cause offline before any new start |
| Task 6 header or plain log text | Harmless firmware log | Teach the engine tasks 5 and 6, then ask the owner about a retry |
| Task 2 frame or other STP data | The engine refused a real frame | Keep the bytes; fix the refusal offline, then ask |
| No stale bytes, `-16` persists | The inference above is wrong | The new refusal message names the cause, or else it is the DMA or post-clear check; a reboot recovers |
| Bytes logged, Wi-Fi back | Recovery holds without a reboot | Run one join and a gateway ping |

**Stop rules:** one load; any Oops, warning or assert; no GNSS open.

## D1 result: recovered, firmware message still unknown (2026-11-01)

Station 30, boot `4ac95e75`, `mt6797-consys.ko` `25571312…`, one load, no GNSS open.
Private evidence under `artifacts/station-work-30/boot-4ac95e75/gnss-d1/`.

**Observed:** `1 stale BTIF bytes: 7b`, then negotiation `result=0`, common init
285/285, join on 5200 MHz, lease, gateway 3/3. No Oops, warning or assert. So the
`-16` inference holds, and a stale RX byte alone can block every later start.

**Inferred, from reading the code path:**
- The two refused reloads returned before any FIFO clear, so that byte was
  probably left from the original failure.
- One byte in a FIFO that had 30 s to fill means the firmware sent almost
  nothing after the refusal: no long text, and no retransmissions, though its frame
  was never acknowledged. That leans toward firmware that stopped running (cause 1),
  but does not prove it. `0x7b` has no STP start bit, so it starts no frame.

**Unknown:** what the refused bytes were. None of the table's first three rows can
be chosen; only the recovery row applies.

## T3: retry (radio action, admitted)

The owner approved steps A1 and A2 on 2026-11-01. One open each, plus A2's second
open with ping; anything else needs asking again.

[0431](../../patches/proposals/0431-soc-mediatek-mt6797-consys-read-firmware-messages-an.patch) parses tasks 5 and 6 as the
vendor does and logs them in hex, keeps the 64 bytes before a failure and 64 after
it, and keeps reading after a failure so the firmware is not left blocked.
[0432](../../patches/proposals/0432-gnss-mt6797-add-a-parameter-to-stop-after-GPS-functi.patch) adds `start_engine=0`, which
stops after function-on. The effects are those of T2 stage A, split in two, and
nothing new reaches the firmware.

**Hypothesis:** function-on alone is harmless, and the frame after it tells cause 1
from cause 2.

**Before either open:** set the system clock to the real time, which removes the 1970
date as a suspect.

| Step | Open | Decides |
| --- | --- | --- |
| A1 | `start_engine=0`, 60 s, `wlan0` idle | Is function-on alone what the firmware reacts to? |
| A2, only if A1 is clean | `start_engine=1`, 5 minutes, `wlan0` idle, then one with ping | Do frames arrive? |

| Observation | Next |
| --- | --- |
| A1 logs an assert or stops | Function-on itself is the problem; stop and read the bytes offline |
| A1 clean, A2 logs an assert or stops | The start sequence is the problem; read the bytes, and vary only what they point to, with a new request |
| Firmware log messages only, link alive | Harmless; continue |
| A2 gets `0x0a` frames with `$G` sentences | Stage A's question is answered; go to stage B |

**Stop rules and privacy:** as in T2. The new failure logs hold up to 128 received
bytes in hex, which could hold sentence text if a failure came after a fix, so they
stay private until read.

**Package:** Buildbox-2, commit `16865d12`, inventory `c4b94b38…`, `Image.gz`
`933a7d70…`, `gnss-mt6797.ko` `1e424b045b306286c7ca6255d822fa028ff1ab05d5f8096e128f12823e90652c`, `mt6797-consys.ko` `7a1bb9dbc9c651e4bfb87506f731ca8d1266729f9e75c38401256c5087efbeaa`. Validated, not run.

**Known risk:** Wi-Fi may drop again. A CONSYS reload with 0429 recovered it, so an
outage should not need a reboot, though this was seen once.

## T3 result: the start sequence causes a firmware exception (2026-11-01)

Station 30, boot `4ac95e75`, kernel `Image.gz` `ee620135…`, `gnss-mt6797` `1e424b04…`,
`mt6797-consys` `7a1bb9db…`, core `425b8add…`, `mac` `79808dd7…`, clock set to real UTC.
Evidence and the exact firmware analysis are private, under
`artifacts/station-work-30/boot-4ac95e75/gnss-t3/`.

**Observed:**
- **A1, function-on only, 60 s:** on and off both `result=0`. No frame on any task,
  no firmware message, gateway ping 5/5.
- **A2, start sequence with an empty `0x14`:** the five frames were acknowledged at STP
  level. 5 ms after function-on, task 5 messages reported a firmware exception. This
  is what T2 stage A hit: its `-71` was this message, and the stale `7b` was its
  first byte. The 1970 clock is no longer a suspect. The capture stopped at 64 bytes,
  so the rest of the dump is missing.
- Ping still passed right after the exception, but Wi-Fi teardown timed out. A CONSYS
  reload recovered with no stale byte; channel 40 rejoined, no reboot. The second
  open (A2b) was not run and will not run with this sequence.

**Read from the retained patch image, with Ghidra's NDS32 module:**
- Type `0x13`, the first frame of the sequence, goes to the initialization handler. That
  handler calls through a pointer in a fixed header the patch never fills, and the fault
  is at that call. The handler's checks only choose a log line; they do not skip the call.
- The config, type `0x14`, goes to a different handler and arrives afterwards. So the
  empty configuration did not cause this fault. Which handler each type reaches rests
  partly on the vendor sender, since one starting register value is outside the read window.
- The patch reads an image header at that location: entry point, engine version, and a
  partition table. It is an image format, not a callback the firmware fills itself.
- `ITYPE=0x10` is an instruction-fetch alignment check, by the bit definitions in Linux
  5.10's `arch/nds32`. That fits a jump through whatever the memory holds. The pointer's
  actual value was not captured.

**Read from the public vendor source:** `gps_emi.c` copies `/vendor/firmware/MNL.bin` to
the CONSYS memory base plus 1 MiB. **Searched, not found:** `MNL.bin` in any retained
extraction or firmware set. `mnld` does have `thread_emi_download`, which opens
`/dev/gps_emi`.

**Inferred (strong, not proven):**
- The header location is where `MNL.bin` belongs, so the missing image is the first cause:
  the engine on the microcontroller needs it, and a GFNS client without it cannot start.
- It would explain why neither patch has NMEA formatters: they would be in the image, not
  in ROM as the reverse-engineering record assumed.
- The stock path is then probably the engine in `libmnl` on the application processor,
  which feeds `/dev/stpgps` bytes to `mtk_gps_data_input`. This stays an inference until a
  stock trace confirms it.

**Other differences from stock, not shown to matter:** an empty `0x14`; a zero delete
bitmap, where `mnld` passes a value chosen by its start request; no NV download open.

**Correction:** an earlier version of this section published exact firmware addresses and
strings (commit `3e0a8110`). They now live in the private analysis named above.

**Made safe:** [0435](../../patches/proposals/0435-gnss-mt6797-do-not-start-the-receiver-by-default.patch)
makes the start opt-in, because the exception also costs Wi-Fi. A plain open only
checks the link. The link work (0418-0419) and 0429 stand.

**Kept for later:** [0439](../../patches/proposals/0439-gnss-mt6797-send-the-vendor-s-start-configuration.patch)
sends the 49 bytes `mnld` builds for chip `0x6797` when the start is requested: interface
1, DGPS mode 2, PPS duty 100, TCXO, 2000 ppb, 26 MHz, link 115200, fix every 1000 ms, chip
words `0x800000f0` and `0xffff6797`, GNSS mode 2, calibration words zero. These are `mnld`'s
defaults with no `mnl.prop`; a real `mnl.prop` was not retained. It also captures 128 bytes
before a failure and 1024 after. Host tests pass and it compiles with W=1; it has no
Buildbox package and has not run. No device run is proposed: by the above, it would reach
the same fault.

## Options

1. **Look for `MNL.bin`.** A later search of the private Gemian dump did not find it either
   ([driver note](../../docs/hardware/gemini-gnss-driver.md#scope-and-the-current-blocker)).
   What remains is any other firmware image the owner has, and a bounded read-only check on
   live Gemian (`/vendor/firmware`, `/dev/gps_emi`, H0). If it exists, the start can resume,
   with new memory handling and redistribution questions.
2. **Capture a stock session.** A Gemian `/dev/stpgps` trace would confirm or refute the
   stock-path inference. This is a radio action on Gemian and needs its own protocol.
3. **Run the vendor engine** under a shim: proprietary, not a standard stack.
4. **Stay parked**, with the link and records kept.

## Associated code

- [test-stp-engine.c](test-stp-engine.c), [test-gfns.c](test-gfns.c) and
  [run-tests.sh](run-tests.sh): `run-tests.sh PREPARED_LINUX_SOURCE`. No hardware.
