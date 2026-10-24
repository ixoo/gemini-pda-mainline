# Autorate boot: no data frame acknowledged with the fixed-rate bit cleared

Result record, 2026-10-24. One boot on the `mt6797-a53-wifi-autorate`
profile: the pipelining tree plus 0242 (clear the descriptor's fixed-rate
bit for ordinary data frames so the firmware selects the rate; management
and security frames keep OFDM 6 Mbit/s). Build input `88f5edaf`, boot
`673ab08e…`, candidate `1b04c2a9…`, boot2 `08a930e8…`, admitted by the host
watcher. Same laptop and AP as the series.

## Observed

Scan, authentication, association, both EAPOL replies and both key
commands completed as on every single-arm boot: every frame with a fixed
6 Mbit/s descriptor was acknowledged (`status=0`). The data phase then
queued four ordinary frames (the leaf's DHCP discovers, 342 bytes, three
pages each) and the firmware reported each with TX status 3 after about
three seconds, the retry-limit result in the public gen3 status
enumeration, so nothing reached the access point: `tx_queued=4 tx_done=0
tx_failed=4`, DHCP never bound, no listener, no measurement. The host's
disconnect ended the data phase at 12.2 s; the teardown then completed in
full (PM abort, deauthentication delivered, an absence notice arriving
before stage 3 counted as "outside teardown" by 0243, stage 3 with credits
returned, disable `status=0`), and the device returned to changed-boot
Gemian `c977624f-203f-487f-a31e-8d0125ffe654`.

## Reading

The station record already carries the OFDM rate set and the 5 GHz PHY
type, so the firmware's selector was not starved of rates; yet every
auto-rate frame went unacknowledged while fixed-rate frames to the same
peer succeeded in the same lifetime. Clearing the bit alone is therefore
not the rate lever. The next hypothesis is the transmit parameters the
firmware derives when the station record is updated (its basic rate set,
desired PHY set and default fixed rate code, which the vendor driver
populates together), not the per-frame descriptor; that needs the vendor
driver's public station-record path read against our command before
another boot. 0242 is retired from the series with its profile; the
descriptor stays fixed at OFDM 6 Mbit/s, which the pipelining boot has
shown still leaves room up to about 3.2 Mbit/s of goodput on this host
path.

## Evidence

`artifacts/wifi-throughput-autorate-1/` (sealed session, 2,600 records),
install receipt under
`artifacts/device-install-evidence/mt6797-wifi-tx-autorate-deployment-1/`,
[scalars](results/tx-autorate-runtime-scalars.json).

## rate-2 (2026-10-24): the vendor's data descriptor, same result; the block is upstream of the descriptor

Proposal 0255 built ordinary data descriptors exactly as the vendor data
path does: no fixed-rate bit, zero power offset and the rate word (bytes
24–27) left zero, so the firmware's adaptation chooses from the station
record's rate set; management, EAPOL and the reserved deauthentication
kept their fixed 6 Mbit/s descriptors. One boot on the lifecycle tree
(build `4a37c041`, boot2 `f02087dc…` over `87d7b532…`, boot `4afdfa74…`),
five-chunk protocol planned.

**Per-frame completion status is the headline.** Nine host frames
completed: authentication and association (fixed rate) status 0; the two
EAPOL frames (fixed rate) status 0; the reserved deauthentication (fixed
rate) status 0; and every one of the four ordinary data frames, the DHCP
discovers at 342 bytes, status 3 after three attempts each, one every
three seconds until the leaf gave up (DHCP failed, no lease, no
measurement, the host disconnect refused by the window guard). Teardown
completed normally and the device returned to changed-boot Gemian
`78b5c75b-5a8b-4598-9b7e-61acbf0f35e9`; log complete.

This is the same outcome as the autorate boot with a descriptor the
firmware's own driver would have produced, so the descriptor is excluded:
whatever the firmware derives for an unforced data rate from the station
record (its rate set, the HT and capability fields, or its rate policy)
yields frames the access point never acknowledges, while a forced 6 Mbit/s
is acknowledged every time. That distinction is the result. It also fits
the idle-link loss of lifecycle boot 10: a firmware-originated keep-alive
takes its rate the same way. Proposal 0255 is retired; the rate lever
moves to the station record, a larger question that needs the private
reference before another boot. Scalars: [rate-2](results/tx-rate2-runtime-scalars.json).

## Rate-visibility boot (predeclared, 2026-10-24; runs after the equivalence boot)

Both unforced-rate boots ended with status 3 on every ordinary data frame
and nobody could name the rate the firmware chose, because the TX-done
event's rate word was parsed but never logged. Profile
`mt6797-a53-wifi-rate` is the lifecycle profile plus two proposals:
[0262](../../patches/proposals/0262-wifi-mt6797-record-the-firmware-rate-word-of-every-TX-completion.patch)
logs one extra line per completion (`join TX rate: pid= status= rate=0x…
flags=0x…`, the firmware's rate word valid with flag bit 0, behind
`CONFIG_MT6797_TX_DONE_RATE_RECORD`; the existing completion line is
unchanged) and
0263 (retired after the boot; in the git history as `patches/proposals/0263-wifi-mt6797-send-ordinary-data-frames-without-a-fixed-rate.patch`)
is the retired 0255 as it was: ordinary data frames with the fixed-rate
bit clear and the rate word zero, management and security frames at their
fixed basic rates (the control: they must complete with status 0 as
before).

Headline: the rate word of every frame that completes with status 3, as
a histogram, decoded as the MediaTek rate code (mode in bits 6–8: 0 CCK,
1 OFDM, 2 HT mixed, 3 HT greenfield, 4 VHT; index in bits 0–5; the forced
descriptor's OFDM 6 Mbit/s is 0x4b) and also shown raw, with the status-0
management frames' words beside them as the control.

Branch table, decided before the boot:

| Status-3 rate words | Meaning | Next |
|---|---|---|
| a plausible legacy rate (CCK or OFDM index in the station's basic/supported set) | the descriptor and the rate table are exonerated; the fault is elsewhere (power, antenna, QoS/HT fields) | compare the frame's other descriptor fields with the fixed-rate frames that succeed |
| an HT/VHT MCS (mode 2–4) the legacy-only station record never negotiated | the station record / BSS info shape is the lever | declare the station's HT capability or constrain the record's PHY type set |
| zero, or an index outside any rate table | the unforced path indexes an empty rate table | the rate table the firmware builds from the station record (desired rate set, PHY type set) is the lever |
| flag bit 0 clear on the failing frames | the firmware reports no rate for them | the record cannot name the rate; fall back to the vendor's rate-set bits and a fixed-rate sweep |

One boot, five chunks, one lifetime, as the other measurement boots. 0263
is retired again after the boot whatever the answer; 0262 stays available
for measurement profiles.

## Rate-visibility boot: result (2026-10-24) — branch 3, an empty rate table

Build `91629f5b` (profile `mt6797-a53-wifi-rate`), boot2 `bb9b9389…` over
`a0bbc52e…`, mainline boot `cff73c8a…`, returned to Gemian `28318e8b…`,
complete sealed log. The join reached the data phase; four ordinary data
frames were queued and all four failed (status 3); the five fixed-rate
control frames completed (status 0). The headline, from the new
`join TX rate` record (flag bit 0 set on every line, so the firmware
reported a rate for each frame):

| Completion status | Frames | Rate word | Decoded |
|---|---|---|---|
| 0 (management / security, fixed rate) | 5 | `0x004b` | OFDM 6 Mbit/s: mode 1 (bits 6–8), index 11, the descriptor's own code |
| 3 (ordinary data, unforced) | 4 | `0x0000` | mode 0, index 0: the CCK 1 Mbit/s code, which no 5 GHz receiver decodes |

The control frames confirm the rate-word format (the same code the
descriptor carries at `0x4b << 2`), so the zero is a real zero, not a
different encoding. Branch 3 of the table: the unforced path indexes an
empty rate table and sends at entry 0; the descriptor is exonerated (a
fixed code in the same descriptor goes out and is acknowledged) and so
is the power table. The lever is the rate table the firmware builds from
the station record: its inputs are the desired non-HT rate set (bits 6–13
for 6–54 Mbit/s), the desired PHY type set (OFDM only, 8), the BSS basic
rate set, the default fixed-rate code (`0x4b`) and the record's state
sequence. Our record sends OFDM-only and the 6–54 set, so the next single
variable is which of those the firmware's table build actually consumes;
the vendor host derives the desired set from the association response's
operational set and walks the record through states 1, 2 and 3, each an
update command. That boot is predeclared when it is next in the queue.

0263 is retired again, as announced; 0262 stays available to measurement
profiles. Scalars: [`results/tx-rate3-runtime-scalars.json`](results/tx-rate3-runtime-scalars.json).

## State-2 station record boot (predeclared, 2026-10-24)

Branch 3 named the lever: the firmware's rate table for this station is
empty. The vendor host walks the station record through states 1, 2 and 3,
each an update command, and derives the desired non-HT rate set from the
association response; this driver sends state 1 before authentication and
state 3 after association, with the desired set from the beacon. The
smallest difference first:
[0266](../../patches/proposals/0266-wifi-mt6797-update-the-station-record-at-state-2-after-authentication.patch)
sends the state-2 update after authentication (the state-1 payload with
the state advanced, one record and one credit wait in the join). Profile
`mt6797-a53-wifi-rate` is re-created for this boot: the lifecycle profile
plus 0262 (rate record), 0263 (ordinary data without a fixed rate, the
variant under test, re-admitted for this boot only) and 0266. The single
variable against the rate-visibility boot is the state-2 update.

Headline: the rate words and status of the ordinary data frames, and the
transmit rate if any complete. Branches, decided before the boot:

| Outcome | Reading | Next |
|---|---|---|
| data frames complete (status 0) with non-zero rate words | the state sequence was the missing trigger; rate adaptation is on | measure TX against the fixed-rate 2.6–2.8; retire the forced 6 Mbit/s descriptor if TX rises |
| rate words still `0x0000`, status 3 | the state sequence is not the input the table build consumes | the desired rate set from the association response, then the record's other fields, one per boot |
| non-zero rate words but status 3 | the table is built and a rate chosen that the link does not carry | read the chosen rates; compare with the AP's supported set |

0263 retires again after the boot; 0266 is retained only on the first
branch.
