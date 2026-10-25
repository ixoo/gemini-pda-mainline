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
0262 (retired on 2026-10-25, re-expressed on the current tree as [0275](../../patches/proposals/0275-wifi-mt6797-record-the-firmware-rate-word-of-every-TX-completion.patch))
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
0266 (retired after the boot; in the git history as
`patches/proposals/0266-wifi-mt6797-update-the-station-record-at-state-2-after-authentication.patch`)
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

## State-2 station record boot: inconclusive (join refused), 0266 retired (2026-10-24)

Build `93a9f000`, boot2 `bf9bd805…` over `51faa318…`, mainline boot
`6de6f8a9…`, returned to Gemian `93ff170a…`, complete sealed log. The
passive scan passed (`complete=1 beacon=1 credit=1`), the authentication
frame went out at the fixed rate (`0x004b`, status 0) and its response
arrived; the state-2 update then returned -22 and the join stopped with
-110 (`join stopped: status=-110 first=0 submitted=0x800 debt=2
cleanup=0 branch=2`). No data phase: none of the three branch rows was
reached, and nothing about the rate table, the state sequence or the
chosen rates follows from this boot. It is not a rate data point. The
state-2 update was never sent; the branch-3 lever (the station record's
shape) remains untested, not falsified, and stays live. The rate thread
stays closed pending the owner's explicit answer; if it is yes, the single
attempt (the encoder admitting state 2) is scheduled after the
receive-batching boots, never in the same boot as a receive measurement.

Where the -22 came from, read before any vendor interpretation: our own
code. `mt6797_join_station_payload` (`join-commands.h`) admits station
states 1 and 3 only, so `mt6797_hif_join_station` (`hif.c`) returned
-EINVAL before anything was written; the log shows no submission for
sequence 20 and the firmware never saw the record. The vendor's state-2
update is the same command (`CMD_ID_UPDATE_STA_RECORD`, 0x13) with the
same record layout and only `ucStaState` advanced
(`cnmStaSendUpdateCmd`, `cnm_mem.c`, called from `cnmStaRecChangeState`
for every state), so no different command or record exists on the
vendor side; the one concrete difference between the two hosts is the
state order (1, 2, 3 against 1, 3), which this boot did not exercise.

0266 is retired with that counter-evidence: as written, its premise
("the same payload, state advanced") was refused by our encoder, and the
rate thread gets no blind variation. Whether the encoder's admission of
state 2 is tried once, as the single informed attempt the vendor reading
allows, is the owner's decision; without it the rate thread closes and
the forced 6 Mbit/s is recorded as a characterised limit (2.6–2.8 Mbit/s
of TCP over 802.11a at 6 Mbit/s is plausible efficiency, not a defect),
reopened only by a firmware-side decode in the RE VM.

Also from this boot, not rate: the stop line's `debt=2 cleanup=0`
records pages reserved for the refused update and never released; the
failed-join path keeps a false debt. That fix goes in before the AP-loss
gate and every reconnection ([transport record](HIF_TRANSPORT_ANALYSIS.md)).

## State-2 station record boot, second attempt (predeclared, 2026-10-25): the encoder admits state 2

**Approved.** The owner's single informed attempt (after the probe and the
sweep): one boot, and the rate thread closes either way. The vendor host
walks the station record through states 1, 2 and 3 with the same update
command and only `ucStaState` advanced (`cnmStaRecChangeState` →
`cnmStaSendUpdateCmd`, `cnm_mem.c`); this driver sent 1 before
authentication and 3 after association, and the first attempt (0266) was
refused by our own encoder before anything reached the firmware.

**The tree.** The rate series: the lifecycle tree through
[0274 v2](../../patches/proposals/0274-wifi-mt6797-the-diagnostic-s-ceilings-stop-its-counts-not-the-window.patch),
then [0275](../../patches/proposals/0275-wifi-mt6797-record-the-firmware-rate-word-of-every-TX-completion.patch)
(one `join TX rate: pid= status= rate=0x… flags=0x…` line per completion,
the firmware's rate word valid with flag bit 0; the retired 0262 rebased),
[0276](../../patches/proposals/0276-wifi-mt6797-rate-code-0-sends-ordinary-data-without-a-fixed-rate.patch)
(rate code 0: no fixed-rate bit, zero power offset, zero rate word, the
vendor data form; the retired 0263 as one value of 0273's option) and
[0277](../../patches/proposals/0277-wifi-mt6797-update-the-station-record-at-state-2-after-authentication.patch)
(the encoder admits state 2; after `join_wait_management` succeeds the
state-2 update goes out with the state-1 payload and the state advanced,
one record and one credit wait, `join station state 2: status= sequence=`).
Profile `mt6797-a53-wifi-rate`: AP-DMA both ways, the received and
transmitted rate records, `CONFIG_MT6797_DATA_FIXED_RATE_CODE=0x0`. Both
series applied in order in the VM; the rate tree equals the boot D branch;
compiled at rate code 0 and 0x4c; strict checkpatch clean apart from the
series' usual absent sign-off; the descriptor fixture covers code 0.

**Harness.** Two chunks per direction (the lifecycle-9 precedent: three
per-frame records at this rate do not fit five chunks under the sealed
logger's 2 MiB), applied to the derived helper after its validators; the
probe rides (opt-in, recorded, not graded); the preflight takes the
declared count. Comparison: boot C (54 Mbit/s fixed) per chunk,
cross-session with the ±40 % floor unless boot D runs in boot C's session.

**Hypothesis.** With the state-2 update accepted after authentication, the
firmware's rate table for this station is populated and ordinary data sent
without a fixed rate completes with status 0 and a non-zero firmware rate
word.

**Unique observations.** The `join station state 2` line's status; the
first data frame's `rate=0x00`; the per-completion rate words; the
completion status histogram; the data phase ending by `disconnect`.

**TX first.** The status-3 count and `tx_failed` are read before any rate
claim; `debt=0`; no guard record.

| Reading | Cause | Next |
|---|---|---|
| state-2 update refused (`status=-22`/`-110`, join stops; or the firmware refuses the command) | the state-2 form is not accepted by this firmware from this host; the station record's shape stays the untested lever | the rate thread closes: the fixed rate is the characterised limit (54 Mbit/s acknowledged); reopened only by a firmware-side decode in the RE VM |
| accepted; data completes with status 3 and rate word 0 | the rate table is empty even after state 2: what fills it is not the state sequence | the thread closes, same reading; 0276 and 0277 are retired with this counter-evidence, 0275 stays as a record |
| accepted; data completes with status 0 and non-zero rate words | the firmware's rate control is alive once state 2 is sent | the thread opens: TX per chunk against boot C's fixed 54; the rate profile becomes the measurement tree; then the completion lever |
| accepted; mixed status with rate words present | rate control alive but losing frames at the chosen rates | read the rate words against the status; the vendor's rate-control parameters are the next question |

**The three questions.** 0277: reachability, the state-2 command is sent
from `mt6797_mac_sta_state` after the management wait and before
`join_authenticated`, through `mt6797_hif_join_station` whose encoder now
admits 2 (a refusal releases the reservation by 0267); ownership, the
station record is the firmware's, written only by the update command; what
the vendor writes, the same command and record at every state change.
0276: reachability, descriptor bytes 11, 26 and 27 from the option through
the unchanged submission path; ownership, none (the firmware reads the
descriptor); what the vendor writes, no fixed rate for plain data. The
ledger stands at seven.

**Verification of 0274 v2 on this boot.** If the queued count crosses
8,192, the ccmp-stable end line must show `beyond>0` with the data phase
ending by `disconnect`; otherwise "not exercised" (the fixture is the
evidence).
