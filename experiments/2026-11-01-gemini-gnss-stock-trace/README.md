# Experiment: one traced GNSS session on stock Gemian

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-gnss-stock-trace` |
| Status | `planned`: draft protocol; not admitted; step 1 is a radio action and needs the owner's approval |
| Subsystem | MT6797 CONSYS GNSS: `mnld`, `/dev/stpgps` on known-good Gemian |
| Device variant | Gemini PDA (MT6797X), known-good Gemian `3.18.41+` |
| Date(s) | not run |
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
- `strace` runs from a RAM directory and leaves no file on persistent storage. If it is not already
  on the device, a static AArch64 build is pinned by hash in this record before use.
- Nothing on the device runs a GPS client today, so the start comes from one datagram per command
  to `mnld`'s `mtk_hal2mnl` socket, which is what the Android HAL does. The handler reads a first
  field and then a command: `0x65` init, `0x66` start, `0x67` stop, `0x68` cleanup.

**To settle offline before admission:** the socket's exact path and namespace, and the message's
exact bytes (from `gps.mt6797.so`), plus any other command the HAL sends first, such as position
mode; and how the sender runs in the container.

## Step 0: read-only inspection (no radio action; standing Gemian authorization)

Under the [standing inspection authorization](../../docs/SAFETY.md#standing-gemian-inspection-authorization).
Verify the OS, kernel and boot identity first. Then record:

- whether `mnld`, `mtk_agpsd`, `MPED` and any FLP client are running (H0 of the
  [reverse-engineering record](../2026-11-01-gemini-gnss-re/README.md));
- `/dev/stpgps`, `/dev/gps_emi`, `/vendor/firmware`, and `mnld`'s retained log lines if any;
- the contents of `mnl.prop` and `gps.conf` wherever they exist: `EPO_enabled`, `BEE_enabled`,
  `SUPL_enabled`, `OFFLOAD_enabled`, and any clock settings;
- whether `strace` is present, and the time source, because the engine uses the host clock.

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
can send cell and location data. The run goes ahead only with those off in the configuration seen at
step 0, or after the owner decides otherwise. SSH uses the known-good Wi-Fi as usual.

**Procedure:** device near a window or outdoors, on stable power, Wi-Fi up.
1. Attach `strace` to `mnld`, writing to RAM, and confirm it is capturing.
2. Send init and start. Hold for at most 20 minutes, or until 2 minutes after the first fix.
3. Send stop and cleanup. Detach `strace`, confirm a gateway ping, and copy the capture to private
   artifacts.

**Budget:** one start in one Gemian boot. No retry.

| Observation | Meaning | Next |
| --- | --- | --- |
| `AA F0` boot, then measurement packets | The host path is confirmed | Decode packets offline; decide on the open stack |
| GFNS `A5` frames | Offload is in use after all | Stop and rethink: the `MNL.bin` inference would be wrong |
| No traffic, or `mnld` fails or uses a serial path | Stock GNSS does not start this way | Check the trigger offline; a further start needs a new request |
| Boot works, packets flow, no fix | Normal if indoors or a cold start | The protocol is still decodable; a fix is not needed |
| A fix arrives | Stock GNSS works, the first time on record | Keep the capture as the reference |

**Stop rules:** firmware assert or whole-chip reset in the log; Wi-Fi lost beyond a normal gap; any
Oops; unusual battery or SoC temperature; `mnld` restart loop. On a stop: send stop, detach `strace`,
keep the evidence. Recovery is an ordinary Gemian reboot, and the primary boot path is not changed.

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
