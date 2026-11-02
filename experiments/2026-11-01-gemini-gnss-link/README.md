# Experiment: GNSS driver first step, the STP link and a silent device

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-gnss-link` |
| Status | `running`: T5 ran at a window, not outdoors: mainline tracked two live satellites and received navigation data, too few for a position; open sky is untested. Earlier: `parked`: T1 passed; T3's start caused a firmware exception, inferred to be because the engine needs `MNL.bin`; the owner states that image does not exist; the receiver has produced no data |
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

## Decision: parked (2026-11-01)

A later search of the private Gemian dump did not find `MNL.bin`
([driver note](../../docs/hardware/gemini-gnss-driver.md#scope-and-the-current-blocker)), and
the owner states that it does not exist. So the offload start has no image to run,
no further GFNS start is proposed, and 0439 stays unused. No read-only Gemian check
for the file is requested. That the engine needs this image, and that stock uses
`libmnl`, remain inferences.

Routes left, neither started and each needing its own decision:
- **Capture a stock session.** A Gemian `/dev/stpgps` trace would confirm or refute the
  stock-path inference. This is a radio action on Gemian and needs its own protocol.
- **Run the vendor engine** under a shim: proprietary, not a standard stack.

A later [offline study](../2026-11-01-gemini-gnss-host-engine-study/README.md) gives a conditional
go for an open stack on the host path. The persistent STP link (0418-0419) and 0429 stay. The link is available to other STP
clients, and 0429 helps Wi-Fi recover.

Later, patches 0451 to 0454 removed the GFNS client, and its fixture went with it, after a [minimal host](../2026-11-01-gemini-gnss-stock-trace/README.md#step-6-a-minimal-host-with-mnld-stopped-radio-and-firmware-action-owner-approved) showed the DSP path works on stock.

## T4: boot the DSP through `/dev/gnss0` (radio and firmware action; owner approved)

Approved by the owner on 2026-11-01, in the words "Approve the test", for the drafted plan.

**Hypothesis:** the DSP boots over the mainline STP link as it did on stock in [step 6](../2026-11-01-gemini-gnss-stock-trace/README.md#step-6-a-minimal-host-with-mnld-stopped-radio-and-firmware-action-owner-approved), including boot fragments split at 1024 bytes by the gnss core. Unique observation: `0xFE31`, `0xFE32` and epochs on mainline.

**Effects:** a station with patches 0451 to 0454. Opening `/dev/gnss0` drives GPIO 69 high, for the first time on mainline, and switches the GPS function on. [gnss-minihost.c](../2026-11-01-gemini-gnss-stock-trace/gnss-minihost.c) reads the DSP image from a RAM copy of the device's own `libmnl.so`, boots the DSP with the same bytes as step 6, sends the per-second frames for 60 s, sends stop and closes. Wi-Fi stays up and idle. The clock is set to the real time first. The settings file and `libmnl.so` are private, in RAM, and deleted afterwards. No partition, NVRAM or firmware file is written except the normal `boot2` install. The capture stays private.

**Risks:** a firmware assert takes Wi-Fi down until a CONSYS reload, as in T2 and T3, and might need a reboot. Evidence goes over USB. Recovery is the reviewed path to Gemian.

**Budget:** one open, no retry. Stops: any firmware assert, `STP link stopped`, Oops, warning or call trace; a failed boot; the DSP silent for 10 s. Tested offline against a fake DSP under sanitizers, and its boot and setup bytes match step 6's. Fragment splitting and hardware are not tested.

| Observation | Meaning | Next |
| --- | --- | --- |
| Header unanswered | The link or function-on state differs from stock | Compare offline; no retry |
| Stops at the first fragment | Splitting at 1024 bytes is probably the problem | Send fragments unsplit, which likely means leaving the gnss core |
| Stops at another fragment | Timing or queueing on the link | Read the counters offline |
| Boots, no epochs | Something in setup differs on mainline | Compare with stock |
| Boots and sends epochs | The mainline link works | Draft the 10 minute outdoor test |
| Firmware assert | The bytes or their timing broke something | Keep the evidence; CONSYS reload; no retry until understood |

## T4 result: the DSP boots and reports on mainline (2026-11-01)

Boot `6b3acef8`, image `boot2` `d1a882db`, kernel `7.1.3-gemini-a53-station`, run by the custodian, indoors. Module `gnss-mt6797.ko` from package `34c0e48d`, sha256 starts `d088aefa`, loaded by hand because this image's root lacks it. That package is later than the admitted commit, with patches 0451 to 0454 and this experiment unchanged. Host sha256 starts `e8606bf8`. Evidence is private under `artifacts/station-work-36/boot-6b3acef8/gnss-t4/`; `frames.log` is 211854 bytes, sha256 starts `7c239054d2816cd1`.

One open, full 60 s window, host exit 0, no stop rule fired. An earlier launch failed before the host ran, because this root has no `nohup`, so it did not open the device. Wi-Fi was not on a clean first join: the first-join fault restarted the firmware at 57 s in this boot, and a rerun got a lease before T4.

**Observed:**
- **Boot:** `0xFE31` answered the header, and all 44 `0xFE32` arrived, in 0.23 s against 0.30 s on stock in step 6. The gnss core's split at 1024 bytes caused no visible problem.
- **Bytes:** all 495 received and 476 sent frames have good checksums, with no bad frames and no leftover bytes. The driver reports 27721 bytes received and 0 dropped, equal to the host's total, and the link reports 0 discarded and 0 duplicates. The first 53 writes match step 6 byte for byte.
- **Epochs:** `0xFE28` 53, `0xFE29` 239, `0xFE2C` 54, `0xFE30` 53, `0xFE37` 51.
- **Satellites:** 53 distinct satellite channels across GPS, GLONASS and BeiDou, and none reached the valid state `0x40`. `0xFE2A`, `0xFE2B`, `0xFE3A` and `0xFE3B` did not appear.
- **Afterwards:** no assert, Wi-Fi restarts stayed at 1, 3 of 3 gateway pings, not tainted, `gnss0` type `MT6797`.
- **Missing seconds:** the DSP's millisecond counter in `0xFE2C` stepped by 2000 seven times in the 60 s, and each time no epoch came for that second. The frame sequence field does not jump across these gaps, so they do not look like loss on the link. The same counter never stepped by 2000 in the 600 s of step 6 outdoors, or in the [20 minute stock run](../2026-11-01-gemini-gnss-stock-trace/README.md) at a window, which also had no valid records in its first minute.

**Inferred:** the mainline link and the split work for the boot and for measurements. The DSP probably did not send those seven seconds, which would put the cause on its side of the link and not in the gnss core.

**Not shown:** that mainline can lock a satellite, or that GPIO 69 helps: indoors, no result tells the LNA apart from no signal. The cause of the missing seconds is unknown. Only this mainline run has them, but it differs from the stock runs in several ways at once, including the kernel, the Wi-Fi state and the host's timing against the DSP.

**Next, by the table:** draft the 10 minute outdoor test. Missing seconds matter for position if they persist outdoors, so that test should count them.

## T5: 10 minutes outdoors with no cable (radio and firmware action; owner approved)

Approved by the owner on 2026-11-02, in the words "Approve the test", for the drafted plan.

**Hypothesis:** outdoors, the DSP on mainline locks satellites as it did on stock in [step 6](../2026-11-01-gemini-gnss-stock-trace/README.md#step-6-a-minimal-host-with-mnld-stopped-radio-and-firmware-action-owner-approved), and the logged measurements give a position offline. Unique observations: valid satellites on mainline, a first real test of GPIO 69 and the antenna path there, and whether T4's missing seconds continue.

**Effects:** as T4, with the same host, settings and DSP image, for 600 s. [gnss-outdoor.sh](gnss-outdoor.sh) starts the host 180 s after it is launched, so that the owner can unplug the device and carry it outside, and writes to the data partition. The owner holds the device still, open, under open sky, preferably where Wi-Fi stays in range.

**Risks:** leaving Wi-Fi range is untested on this driver, which cannot reassociate yet. A Wi-Fi warning stops the run and spends the open, even if GNSS is fine. A firmware assert takes Wi-Fi down until a CONSYS reload. The script's limits are the only thermal and charge guard during the run.

**Budget:** one open, no retry. Stops: any firmware assert, `STP link stopped`, Oops, warning or call trace; SoC at 75 °C, battery at 45 °C or capacity under 30%; an unreadable limit; a failed boot, a failed write or the DSP silent for 10 s. A stop before the open does not spend it. The stop paths are tested with stubs in the VM, and the real `dmesg` and the device are not tested.

| Observation | Meaning | Next |
| --- | --- | --- |
| At least 4 satellites valid, position close to step 6 | GNSS works on mainline | Plan how applications would use it |
| Valid but clearly fewer or weaker than step 6 | The RF path differs: LNA, coexistence or Wi-Fi interference | Compare signal levels offline; no retry until there is a specific cause to test |
| No satellite valid in 10 minutes | The front end is not working as on stock | Compare power and pin state with stock offline |
| Missing seconds stop outdoors | They were tied to no lock or to T4's state | Note it and move on |
| Missing seconds continue | Mainline-specific, and they affect positions | Compare them with the logged Wi-Fi state; investigate before relying on positions |
| Firmware assert or Wi-Fi lost | The longer run or leaving Wi-Fi range broke something | Keep the evidence; CONSYS reload or the reviewed path back to Gemian; no retry until understood |

## T5 result: live satellites at a window, no position (2026-11-02)

**This did not test open sky.** The owner ran it at a window, in their words: "I can't really do outside today, so it's at a window, which should still be good enough to get a fix". So the table above, which compares with step 6 outdoors, does not apply directly. The closest comparison is [step 3](../2026-11-01-gemini-gnss-stock-trace/README.md), stock at a window, probably a different window position and a different sky.

Boot `92cd3b53`, image `boot2` `b8b9256b`, package `114d21cc`, run by the custodian. Module sha256 starts `d088aefa`, host `e8606bf8`, script `9461ac5f`. Opened at about 20:34:45 UTC. One open, full 600 s window, host exit 0, no stop rule fired. The script's own count reads 588 s because its loop runs slower than 1 s. Evidence is private under `artifacts/station-work-37/boot-92cd3b53/gnss-outdoor/`; `frames.log` is 1155292 bytes, sha256 starts `408ea1e45509a646`.

Conditions: a clean first Wi-Fi join, and `wlan0` up for the whole run. This image changes Wi-Fi since T4, with patches 0456 to 0473 and rate control on by default. The blank `power=` field does not prove the cable was out; USB SSH timing out during the run fits that. The custodian tried one LAN connection and one ping about a minute in, so the window has a little extra Wi-Fi traffic. Exactly how still the device was, and when it was placed, are not known.

**Observed:**

| | T5, mainline, window | Step 3, stock, window, first 600 s | Step 6, stock host, outdoors |
| --- | --- | --- | --- |
| First valid record | 217 s | 261 s | 1 s |
| Most valid satellites at once | 2 (GPS 7, GLONASS 1) | 1 | 13 |
| Seconds with any valid satellite | 382 | 126 | 591 |
| Median signal field, GPS | 28 | 25 | 31 |
| GPS `0xFE2B` subframes | 63 | 28 | 648 |
| GLONASS `0xFE3B` strings | 131 | 0 | 1261 |
| Two-second steps of the DSP counter | 0 | 0 | 0 |

- **Navigation data:** 60 of the 63 subframes start with the telemetry preamble, and subframe IDs 1 to 5 all appear. Their parity was not checked.
- **Bytes:** all 6196 received frames have good checksums, 363353 bytes, 0 dropped. The link reports 0 discarded, 0 duplicates and 0 failures.
- **Afterwards:** no assert, no Oops, not tainted, no Wi-Fi restart, 3 of 3 gateway pings. SoC stayed near 31 °C and capacity went from 86% to 84%. One battery temperature reading of 24.4 °C among readings near 15.5 °C looks like a single bad read.

**Inferred:** the receive path on mainline works with live signals, including the antenna, the front end and the LNA control's high state. With 2 satellites at once, no position can be computed, so the solvers were not run and the orbit file was not fetched.

**Missing seconds:** T4's did not return in 600 s, including the 217 s here with no valid satellite, so no lock alone does not cause them. T4 differed by its restarted Wi-Fi firmware, an older image and its indoor placement. Which of these matters is unknown, and T5 cannot separate them.

**Not shown:** a mainline position; performance under open sky; whether GPIO 69 helps, since nothing here ran with it low.

**Next:** T5's one open is spent, so a position needs a new approved run under open sky, with the same script.

## Associated code

- [gnss-outdoor.sh](gnss-outdoor.sh): the T5 run on the station.
- [test-stp-engine.c](test-stp-engine.c) and
  [run-tests.sh](run-tests.sh): `run-tests.sh PREPARED_LINUX_SOURCE`. No hardware.
