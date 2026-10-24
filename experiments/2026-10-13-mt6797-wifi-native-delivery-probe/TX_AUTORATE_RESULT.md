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
