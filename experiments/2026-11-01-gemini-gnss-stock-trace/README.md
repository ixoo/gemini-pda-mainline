# Experiment: one traced GNSS session on stock Gemian

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-gnss-stock-trace` |
| Status | `running`: step 1 ran once: the DSP booted over `/dev/stpgps` on `AA F0` frames; the watcher stopped it after about a second on a TCP connection, before any measurement packets; step 2 ran one start with assistance off: 15 s of steady once-a-second DSP packets and no remote connection seen, then `mnld` trapped on its own 15 s start timer, most likely because `SUPL_enabled=0` suppresses its start-done event; step 3 ran 20 minutes with assistance off and that timer raised: steady DSP packets, no crash, no connection seen; decoded offline: one GPS satellite tracked with live navigation subframes, so the RF path works; no fix likely at this placement; step 4, a 5 minute outdoor walk, is admitted and has not run |
| Subsystem | MT6797 CONSYS GNSS: `mnld`, `/dev/stpgps` on known-good Gemian |
| Device variant | Gemini PDA (MT6797X), known-good Gemian `3.18.41+` |
| Date(s) | 2026-11-01 (step 0) |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | none |

## Question

What does stock Gemian exchange on `/dev/stpgps` during a GNSS start, and does stock GNSS work on
this device at all? The [host engine study](../2026-11-01-gemini-gnss-host-engine-study/README.md)
gives a conditional go for an open stack and names this trace as its next gate.

**Hypothesis:** with offload off, `mnld` boots the DSP over `/dev/stpgps` with `AA F0 ... AA 0F`
frames, then receives per-channel measurement packets.

**Unique observation:** the bytes themselves. They answer the study's unknowns: boot transport,
host control traffic and packet content. No retained material holds them.

## Method

Trace `mnld` from outside, with stock software unchanged:

- `mnld` is class `main` and not disabled in the Gemian init rules, so it should already be
  running in the `android` container; step 0 checks that.
- A userspace `strace` attached to its PID records `read`, `write`, `ioctl` and `open` on
  `/dev/stpgps`, with full bytes. The kernel is untouched, so no boot2 write is needed.
- `strace` is the Debian 9 package installed on Gemian at the owner's instruction, run from the host
  as root against `mnld`'s host PID. Its output goes to a RAM directory.
- Nothing on the device is known to run a GPS client, so the start comes from one datagram per
  command to `mnld`'s socket, which is what the Android HAL does. [hal-send.py](hal-send.py) does this.
  Read from `mnld`: an abstract `AF_UNIX` datagram socket named `mtk_hal2mnl`, bound with the whole
  110-byte address, and a message of two little-endian words, the first ignored, then the
  command: `0x65` init, `0x66` start, `0x67` stop, `0x68` cleanup.

**Still unknown:**
- Whether the socket is reachable from the Gemian host. Abstract names are per network namespace, so
  the sender may need `nsenter -t <mnld pid> -n`. Step 0 checks.
- Whether stock needs the HAL's position-mode command (`0x6c`) before start. The first run leaves it
  out. No listener is bound on `mtk_mnl2hal`, so `mnld`'s replies have nowhere to go; that this is
  harmless is untested.

## Step 0: read-only inspection (no radio action; standing Gemian authorization)

Under the [standing inspection authorization](../../docs/SAFETY.md#standing-gemian-inspection-authorization).
Verify the OS, kernel and boot identity first. Then record:

- whether `mnld`, `mtk_agpsd`, `MPED` and any FLP client are running (H0 of the
  [reverse-engineering record](../2026-11-01-gemini-gnss-re/README.md));
- `/dev/stpgps`, `/dev/gps_emi`, `/vendor/firmware`, and `mnld`'s retained log lines if any;
- the contents of `mnl.prop` and `gps.conf` wherever they exist: `EPO_enabled`, `BEE_enabled`,
  `SUPL_enabled`, `OFFLOAD_enabled`, and any clock settings;
- whether `strace`, `python3` and `nsenter` are present, whether `@mtk_hal2mnl` shows in
  `/proc/net/unix` and in `/proc/<mnld pid>/net/unix`, and the time source, because the engine uses
  the host clock.

Do not copy `mtkgps.dat`, which can hold a last position, or `ML4A_000`, which is calibration.
Only their presence and size are noted.

| Step 0 finding | Next |
| --- | --- |
| `mnld` absent, or its configuration selects a path with no device | Stop and report; step 1 may be pointless |
| An FLP client, or offload selected | Report; it changes the hypothesis |
| EPO, BEE or SUPL enabled | See network below; the owner decides before step 1 |
| As expected | Step 1, if approved |

## Step 1: one traced start (radio action; needs approval)

**Effects:**
- WMT GPS function-on and the stock start, performed by stock `mnld`; the LNA GPIO goes high by
  stock code. GNSS receives only (inferred from the documents).
- Stock writes under `/data/misc/gps`, such as `mtkgps.dat`, and to `gpsdrv` sysfs. This changes
  stored GNSS state on the device, including a position if a fix arrives.
- No partition, NVRAM, boot or firmware write by this procedure. No new firmware file.

**Network:** assistance can send data off the device. EPO downloads from MediaTek's servers, and SUPL
can send cell and location data. Step 0 found no configuration, so both default to on. The owner decided
on monitor and stop: [watch-net.py](watch-net.py) sends stop and cleanup as soon as uid 1021 has a socket
with a remote peer. This reduces exposure but does not prevent a first connection, and DNS through the
container's resolver would not show under uid 1021. SSH uses the known-good Wi-Fi as usual.

**Procedure:** device near a window or outdoors, on stable power, Wi-Fi up.
1. Attach `strace -f -tt -xx -s 65536 -P /dev/stpgps -o <RAM file> -p <mnld pid>`, and confirm it
   is capturing.
2. Start `watch-net.py` for 1200 s, send init, wait 2 s, then send start.
3. Hold until the watcher exits, at most 20 minutes.
4. Send stop and cleanup, if the watcher did not. Detach `strace`, confirm a gateway ping, and copy the
   capture and the `mnld` logcat lines to private artifacts.

**Budget:** one start in one Gemian boot. No retry.

| Observation | Meaning | Next |
| --- | --- | --- |
| `AA F0` boot, then measurement packets | The host path is confirmed | Decode packets offline; decide on the open stack |
| GFNS `A5` frames | Offload is in use after all | Stop and rethink: the `MNL.bin` inference would be wrong |
| No traffic, or `mnld` fails or uses a serial path | Stock GNSS does not start this way | Check the trigger offline; a further start needs a new request |
| Boot works, packets flow, no fix | Normal if indoors or a cold start | The protocol is still decodable; a fix is not needed |
| A fix arrives | Stock GNSS works, the first time on record | Keep the capture as the reference |
| The watcher fires | Assistance ran despite the missing HAL state | The trace so far is still used; a further start needs a new request |

**Stop rules:** firmware assert or whole-chip reset in the log; Wi-Fi lost beyond a normal gap; any
Oops; unusual battery or SoC temperature; `mnld` restart loop. On a stop: send stop, detach `strace`,
keep the evidence. Recovery is an ordinary Gemian reboot, and the primary boot path is not changed.

## Step 0 result (2026-11-01)

Boot `d999c089`, kernel `3.18.41+`, Debian 9. Run by the custodian; raw output is private under
`artifacts/gemian-d999c089/gnss-step0/`. Nothing was sent to `mnld`, and nothing was written or copied.

**Observed:**
- `mnld`, `mtk_agpsd` and `MPED` run as uid 1021. No process named `flp` showed.
- `/dev/gps_emi` is absent. The firmware directories hold no file matching `mnl`.
- No `mnl.prop` or `gps.conf` turned up in the bounded search. `/data/misc/gps` is empty, with no
  `mtkgps.dat`, which suggests stock GNSS may never have run from this data state.
- `/dev/stpgps` is root-only on the host, but the container has its own node owned by `gps` (uid 1021),
  so `mnld` can open it. `persist.mtk.wcn.combo.chipid` is `0x6797`, and `persist.radio.mnl.prop` is empty.
- `strace` is absent; `python3` and `nsenter` are present. `mtk_hal2mnl` appears in both `/proc/net/unix`
  and `mnld`'s, so the sender can run from the host. The clock is right.
- Logcat works, with 4442 lines, and has no line for the offload option, `flp_mnl_mode` or `EPO_enabled`.
- The default route is through `wlan0`, so the internet is reachable. oFono reports the modem powered but
  offline, so no cellular registration now; SIM presence was not read.

**Read from the decompile of `mnld`:** with no config file, EPO, BEE and SUPL all default to on. The
EPO download goes through a check that includes network state, which the HAL normally reports and
this procedure does not. So EPO should not start, but that is inferred. Step 1 showed this wrong; see step 2 for why.

**So step 1's network precondition is not met as written:** those features cannot be shown off.

**`strace`:** on the owner's instruction, the custodian installed Debian 9's `strace` 4.15-2 from the
archive on 2026-11-01, as the only package change, so `/usr/bin/strace` is a new file on Gemian's root
filesystem, not a RAM copy. It has not been run. The Method above is updated accordingly. Tracing a
32-bit `mnld` with it is untested.

## Step 1 result (2026-11-01)

Boot `d999c089`, `mnld` pid 1637, device in place by the owner's word. Run by the custodian, with script
hashes checked. Evidence is private under `artifacts/gemian-d999c089/gnss-step1/`. One start, as budgeted; no
retry.

**Observed:**
- `hal-send.py` works: `mnld` opened `/dev/stpgps` and ran function-on, with the GPS LNA call in `dmesg`.
- **Every frame is `AA F0 ... AA 0F`. No GFNS frame was sent.** So stock's start is the host path, as
  hypothesized. No assert, whole-chip reset or Oops.
- **The DSP boots over STP:** a header frame, then 43 fragment frames of up to 1400 bytes plus stuffing, each
  acknowledged by one DSP frame carrying its number, in under 0.6 s. The header matches the image header in
  `libmnl`, and the payload compared matches that image byte for byte up to the first stuffed byte.
- **The DSP then answers** with a first-message packet, ID `0xFE2C`, 54 bytes. The host follows with control
  frames, IDs `0xFE05` and `0xFE03`, including one long `0xFE03` frame.
- **The watcher fired about 1 s after start,** on an established TCP connection from `mnld`'s uid to a public
  CloudFront address, port 443. The trace ends about 0.74 s after open. **No measurement packet was seen,
  so whether the DSP's data is usable is still unanswered.**
- `/data/misc/gps` was empty and now holds `ARC.BIN`, `BEE.BIN`, `EPO.DAT`, `EPOHAL.DAT`, `QEPOHAL.DAT`,
  `cache.dat` and `mtkgps.dat`. These remain on the device; they were not read or copied.

**Wrong in this record:** step 0's "EPO should not start" was an inference, and it was wrong in practice:
the network check did not hold it back. What was sent over that connection is not known, since only
`/dev/stpgps` was traced. That the host is an EPO server, and that the files came from it rather than from
stock assets, are both inferences.

**Settled by this:** the `strace` method works at this timing, and the boot transport is STP, not UART.
**Still open:** measurements, navigation bits, how much host control the DSP needs, and whether stock
reaches a fix.

## Step 2: one traced start with assistance off (radio action; owner approved)

Approved by the owner on 2026-11-01, near a window. Measurements need a longer run without the connection.

**Correction to the earlier plan:** this section said `mnl.prop` would turn the EPO download off. Read from
the decompile, it does not. `EPO_enabled` in `mnl.prop` goes into the profile sent to the engine. The download
at start checks `EPO_ENABLE` from `/data/misc/gps/gps.conf`, read again at each start, and whether the EPO data
has expired. It logs the network state but does not test it, which explains why step 0's inference failed.

**Writes,** both new files in `/data/misc/gps`, owned by `gps`:
- `gps.conf`: `EPO_ENABLE=0`
- `mnl.prop`: `EPO_enabled=0`, `BEE_enabled=0`, `SUPL_enabled=0`, `SUPLSI_enabled=0`

Both are `key=value`, one per line. `mnld` loads `mnl.prop` in its GPS start path, and that load holds the values
the start uses, so no restart is needed. The owner approved this correction after the attempt below.

**Network:** this should prevent the download rather than catch it; that is read from the decompile and not
yet seen. The quarter-EPO download has no host-side switch found, so that the engine will not request it with
EPO off is an inference. The watcher stays on, with step 1's limits.

**Procedure:** device near a window, on stable power, Wi-Fi up.
1. Verify identity, one `mnld`, the clock and Wi-Fi. Write the two files through the container. Do not read them
   back; check size and owner only.
2. Run step 1's sequence: `strace`, watcher for 1200 s, init, 2 s, start, hold, stop, cleanup, detach. `strace` also
   watches the two files. Stop if the RAM directory falls under 32 MiB free.
3. **Gate, during the start:** the settings cannot be confirmed earlier, because `mnld` reads them as it starts. If
   the trace does not show both files opened within 5 s of the start command, send stop and cleanup. That uses
   the start. Until then the receiver may run on default settings, with assistance on; the watcher still applies.
4. Copy the capture and logs to private artifacts.
5. **Restore:** delete the two files, restart `mnld`, and confirm `mnld` is running with one process. Other files in
   `/data/misc/gps` stay; `mnld` may change them during the run. Their use with EPO off is unknown.

**Budget:** one start in Gemian boot `a0b54f1d`. No retry. Effects and stop rules are step 1's. A fix would store
a position in `mtkgps.dat`, which stays on the device, unread.

| Observation | Meaning | Next |
| --- | --- | --- |
| DSP packets beyond the boot exchange | The packets can be decoded | Decode offline; decide on the open stack |
| A fix arrives | Stock GNSS works, the first time on record | Keep the capture as the reference |
| Boot, then keep-alives only | No signal at this placement, or the engine waits for something | Check offline; a further start needs a new request |
| The gate stops the run | `mnld` did not open the files as read from the decompile | Check offline; a further start needs a new request |
| The watcher fires | These settings do not hold the connection back | Identify the path offline; a further start needs a new request |
| Assert or `mnld` failure | Maybe the settings, the seven files, or `strace` | Compare with step 1; a further start needs a new request |

### First attempt (2026-11-01): stopped at its gate

Boot `a0b54f1d`, run by the custodian; evidence is private under `artifacts/gemian-a0b54f1d/gnss-step2/`. The attempt
used an earlier gate: restart `mnld`, then require `mnld`'s log lines or an advanced access time on `mnl.prop`. Neither
appeared, so no start was sent. No `strace` or watcher ran. The two files were removed and `mnld` restarted.

**Observed:** `/data` is `relatime`. The access time stayed unchanged across the restart, and logcat held no `mnld`
line at all.

**Inferred, not tested:** the gate could not pass, so this does not show that `mnld` skipped the file. The requested read-back
most likely left the access time just after the modification time, and `relatime` then does not update it. The
gate was also at the wrong moment, since the values a start uses come from the load in the start path.

### Result (2026-11-01)

Boot `a0b54f1d`, run by the custodian, evidence private under `artifacts/gemian-a0b54f1d/gnss-step2/start/`. Near a window,
one start, gate passed: `mnld` opened and read both files about 0.4 s apart at the start.

**Observed:**
- **No remote connection seen** by the watcher in the 93 s it ran, which includes the whole time `mnld` was alive.
- **The DSP boot repeated step 1.** It was all `AA F0` frames with no GFNS frame. No assert, whole-chip reset or Oops.
- **Steady traffic for about 15 s.** Each second the host sent the same set: `0xFE00`, `0xFE01`, two `0xFE03` (6 and 126
  bytes), `0xFE08`, `0xFE1C`, `0xFE05`. Each second the DSP sent one each of `0xFE28` (12 bytes), `0xFE30` (61), `0xFE37` (65) and
  `0xFE2C` (48), plus three to six `0xFE29` frames of 61 bytes, with twelve across the first two seconds. `0xFE37` began after
  those two seconds.
- **`mnld` then died of SIGILL.** A worker thread, not the thread on `/dev/stpgps`, hit an illegal instruction about 15 s after the
  first frame, and init restarted `mnld`. The kernel reports a core dump. The monitor noticed about 78 s later.
- `EPO.DAT` and a new `QEPO.DAT` changed size at start with no connection seen.

**Inferred:**
- **The DSP payloads look masked with XOR `0xCA`.** After that, most bytes are zero, for instance 87% of `0xFE37`.
- **`0xFE29` looks like one frame per tracked channel,** so the hypothesis's measurement packets. A few values of its first
  byte recur once a second, the count changes over time, and a block of bytes in it differs in nearly every frame.
  Nothing here has yet tied its fields to `libmnl`'s parser, so this is not decoded.

**Crash cause, from the logs and the decompile:** the kernel logged `0xdefe`, Thumb `udf`, at the fault address on a
thread named `POSIX timer 4`. No core file or usable tombstone exists. That address's page offset and instruction match
`mnld_gps_start_timeout`, which crashes on purpose. Its timer is 15000 ms by default and it fired about 15.0 s after the
start. The start-done event cancels that timer. `mnld` sends the event from its "MNL ready" callback, but that branch sits
behind the `SUPL_enabled` check, so with `SUPL_enabled=0` the event is never sent. So this setting most likely caused
the crash, and neither the engine nor `strace` did. That is inferred: no run has shown the event arriving with SUPL on and EPO off.

**Not known:** whether a fix was near. Step 1 stopped too early to compare.

**Not settled:** navigation bits and a fix. The study's gate on measurement content is partly answered.

## Step 3: one longer start with SUPL off and the timer raised (radio action; owner approved)

Approved by the owner on 2026-11-01, near a window. Step 2 stopped at `mnld`'s start timer before any long run.

**Writes:** the same two files as step 2, plus `timeout.init=1500000` in `mnl.prop`, 25 minutes in milliseconds. `mnld`
reads this value only when the process starts, so it restarts once before the start.

**Consequence, read from the decompile:** `mnld` stays in its starting state, where it ignores a HAL stop. The script
therefore ends every run by stopping the `mnld` service, and checks the watcher and `mnld` once a second. Step 2's
crash shows the kernel powering GPS down when `mnld` dies. A service stop during a run is untested, and the script logs
whether that shutdown appeared.

**Core dumps:** set up at the owner's instruction, in case of another crash. `/data/core` persists, `core_pattern` writes
there until a reboot, and the core limit is raised on the running `mnld` just before the start. A core may hold
position, so it stays private on the device and is removed only on the owner's word. A real fault in a 32-bit
Android process has not been shown to produce one.

**Procedure:** device near a window, on stable power, Wi-Fi up.
1. Verify identity, one `mnld`, the clock and Wi-Fi. Write the two files through the container, checking size and owner
   only. Restart `mnld` and confirm a stable new process.
2. Raise the core limit, check `core_pattern`, then run step 2's sequence for up to 1200 s, with the same gate at 5 s.
3. Stop the service, copy the evidence to private artifacts.
4. **Restore:** delete the two files and start `mnld`. Other files in `/data/misc/gps` stay.

**Budget:** one start in Gemian boot `a0b54f1d`. No retry. Effects and stop rules are step 1's, with a service stop in
place of a HAL stop. A failed gate or a crash uses the start.

| Observation | Meaning | Next |
| --- | --- | --- |
| Runs past 15 s | The raised timer took effect, confirming the cause | Continue to the limit |
| `mnld` still dies at 15 s | The setting did not take effect | Check offline; a further start needs a new request |
| `0xFE29` count and content evolve over time | More measurement data to decode | Decode offline |
| A fix arrives | Stock GNSS works, the first time on record | Keep the capture as the reference |
| Packets continue, no fix in 20 minutes | Normal for a cold start at a window, or the engine lacks something | Decode what arrived; a fix is not needed |
| The watcher fires | SUPL off does not hold every connection back | Identify the path offline; a further start needs a new request |
| GPS stays powered after the service stop | The service stop is not a clean end | Reboot Gemian; rethink before another run |

### Result (2026-11-01)

Boot `a0b54f1d`, run by the custodian, near a window. Evidence is private under `artifacts/gemian-a0b54f1d/gnss-step3/`. One start,
gate passed.

**Observed:**
- **It ran past 15 s.** The trace covers 1203 s with no signal, assert, whole-chip reset or Oops, on the same `mnld`, with no
  core. CPU stayed under 30 C and the battery at 25 C. Ping held.
- **No remote connection seen** in the watcher's 1200 s.
- **Steady DSP packets throughout,** about one each per second of `0xFE28`, `0xFE2C`, `0xFE30` and `0xFE37`, and `0xFE29` at 4.1 to
  6.3 per second, 5804 in all.
- **New traffic later:** `0xFE2A` (14 bytes) and `0xFE2B` (50 bytes) first appear at 268 s, 28 of each. The host also sent
  `0xFE02` 152 times, not seen in step 2's 15 s, with a different `0xFE03` size in those seconds.
- `mtkgps.dat` kept its size. Its contents were not read.

**Deviation, my error:** the script's `stop mnld` ran with no `PATH` and failed with rc 127, so the service stop did not
happen. My stubbed test could not catch this. `mnld` kept GPS running for about 82 s after the window, with no watcher
and no trace, until the custodian stopped it by hand. Radio time was about 21 min 20 s, over the 20 minute budget. The
restore deleted the two files about 50 s before that stop. No connection was open at the check, but a short
one in that gap would not have been seen. The manual stop worked: no process held the device afterward, and `dmesg` shows
the close sequence. `mnld` was then restarted on defaults.

**Inferred:**
- **The crash explanation holds:** with the timer raised, the same SUPL-off settings ran past 15 s. Whether start-done arrives with
  SUPL on is still untested.
- **Measurement packets:** step 2's reading of `0xFE29` still fits, with the same three first-byte values every second and a
  block of bytes that nearly always differs. It is not tied to `libmnl`'s parser yet.
- `0xFE2A` and `0xFE2B` may relate to navigation data, from their sparse and late arrival only.

**Not known:** what the fields mean, whether a fix came, since no client listened and the engine's output was not traced, and
which host messages the DSP needs.

### Decode (2026-11-01)

Offline, from step 3's capture and the decompile of `libmnl`. The format is in the
[driver document](../../docs/hardware/gemini-gnss-driver.md#dsp-packets-on-the-host-path). No payload is published here;
decoders and field notes are private under `artifacts/gemian-a0b54f1d/gnss-step3/decode/`.

**Correction:** the XOR `0xCA` reading from step 2 was incomplete. The real transform is a rotate right by 3, then XOR `0x59`, which
maps `0xCA` to zero. Earlier offsets were also unreliable, since frames were not yet unstuffed.

**Observed in the capture:**
- **The format is right:** all 10717 DSP frames pass `libmnl`'s checksum after unstuffing, and all 5804 `0xFE29` payloads are 57 bytes.
- **`0xFE29` is one record per channel,** with the same satellite numbers and channel numbers `libmnl` unpacks.
- **One GPS satellite was tracked.** Only GPS SV 4 reached state `0x40`, the value `libmnl`'s measurement API requires, in 152 records from
  261 to 415 s, with a signal level of 16 to 27. Other records move between satellites and show mostly zero signal, which looks like searching.
- **Live GPS navigation data arrived.** All 28 `0xFE2B` frames name SV 4, about 6 s apart, the length of a GPS subframe, from 268 to 430 s. Their
  subframe field cycles 1 to 5 in all 27 steps. 20 of 28 start with the GPS preamble, in either polarity. Among those, the
  subframe ID inside the data matches in 16 of 20, and 12 pairs of consecutive good frames step the time count by exactly 1. The
  rest look like bit errors at this weak signal; that part is inferred.

**So:** the antenna, LNA, RF path and DSP receive real GPS signals on this device, which is the first evidence of that on record. It is on
stock Gemian, not mainline.

**Inferred:**
- **No fix came.** No second GPS satellite reached that state, and a fix needs four. Nothing listened for the engine's output, so this is not
  directly observed. A window placement is the likely limit.
- The signal level is C/N0 in dB-Hz, from how the measurement API uses it.

**Still open for an open stack:** the pseudorange and time fields of `0xFE29`, which need several tracked satellites to check; which host messages the DSP
needs; the meaning of `0xFE30` and `0xFE37`; and redistribution rights for the DSP image, which only exists inside `libmnl`.

## Step 4: a 5 minute outdoor walk (radio action; owner approved)

Approved by the owner on 2026-11-01, in the words "5 min total run", choosing the 5 minute version of the drafted plan.

**Question:** does open sky give several satellites at once, so the pseudorange and time fields of `0xFE29` can be checked? A fix in 5 minutes
from a cold start is unlikely and not required.

**Effects:** as step 3, with `timeout.init=600000`. Also:
- [hal-listen.py](hal-listen.py) receives what `mnld` sends to its HAL socket, so a fix can be seen directly. That this changes nothing in `mnld` is inferred.
- A wake lock holds the device awake on battery, and is released at the end.
- Network is not needed. If Wi-Fi drops, the run continues and nobody can intervene until it ends; the watcher still applies.
- The capture, listener output and logs can hold precise position and the walked route. They stay in private artifacts and may be used to investigate. None of it is published.

**Procedure:** start the script over Wi-Fi with a 3 minute delay. The owner carries the device outside, open and in hand, and walks for the 5 minutes at normal pace.
Back in range, copy the evidence and restore as in step 3.

**Budget:** one start in the current Gemian boot. No retry. Stops: step 3's, without the Wi-Fi rule, and battery under 20%. The script ends with a service stop, killing `mnld` if that fails.

| Observation | Meaning | Next |
| --- | --- | --- |
| A fix in the listener output | Stock GNSS works end to end | Keep as the reference |
| Four or more satellites, no fix | Enough to map the pseudorange fields | Decode offline |
| One or two satellites under open sky | Short run, or an antenna or engine limit | Decode; decide whether to run longer while stationary |
| The script stops early | Depends on the reason | Keep the evidence; another start needs a new request |

## Privacy and rights

The capture is location data, and it stays private under `artifacts/` with mode 600, as do logcat
and `mtkgps.dat`. Public results carry packet types, sizes, counts and timing only, never payload
bytes that could hold position, time of fix or sentence text. Satellite identifiers and carrier-to-noise
summaries may be published without coordinates. The DSP image crosses the wire in the capture, so
it stays private; it is vendor firmware, and this repository never carries it.

## Not tested

The trigger format is read from the decompile and worked in steps 1 and 2. `strace` may disturb `mnld`'s
timing, which the keep-alive and ACK flow depend on: a failure under trace does not by itself prove
stock GNSS fails.
