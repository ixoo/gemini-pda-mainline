# Experiment: one traced GNSS session on stock Gemian

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-gnss-stock-trace` |
| Status | `planned`: step 0 done; step 1 admitted on 2026-11-01 with the owner's monitor-and-stop decision; no start sent |
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
this procedure does not. So EPO should not start, but that is inferred.

**So step 1's network precondition is not met as written:** those features cannot be shown off.

**`strace`:** on the owner's instruction, the custodian installed Debian 9's `strace` 4.15-2 from the
archive on 2026-11-01, as the only package change, so `/usr/bin/strace` is a new file on Gemian's root
filesystem, not a RAM copy. It has not been run. The Method above is updated accordingly. Tracing a
32-bit `mnld` with it is untested.

## Privacy and rights

The capture is location data, and it stays private under `artifacts/` with mode 600, as do logcat
and `mtkgps.dat`. Public results carry packet types, sizes, counts and timing only, never payload
bytes that could hold position, time of fix or sentence text. Satellite identifiers and carrier-to-noise
summaries may be published without coordinates. The DSP image crosses the wire in the capture, so
it stays private; it is vendor firmware, and this repository never carries it.

## Not tested

Nothing here has run. The trigger format is read from the decompile. `strace` may disturb `mnld`'s
timing, which the keep-alive and ACK flow depend on: a failure under trace does not by itself prove
stock GNSS fails.
