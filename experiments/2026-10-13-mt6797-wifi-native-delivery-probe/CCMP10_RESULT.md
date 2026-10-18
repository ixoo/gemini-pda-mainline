# C10: finite protected lifetime with mask-only metadata control

Consumed once, 2026-10-18 UTC. The source-observed mask-only comparison passed
its finite compatibility test: WPA2, DHCP, three individual ping replies,
fresh boot-bound Wi-Fi SSH authentication and complete host-protocol cleanup.
No HIF refusal or unexplained timeout occurred. This demonstrates required
metadata availability for the existing initial-PTK checker without issuing
global SET_MONITOR in this build. It does not establish maintained Wi-Fi,
firmware integrity enforcement, key retirement or reusable lifetimes.

## Identity and execution

[Preparation](CCMP10_PREPARATION.md) pins kernel input
`0d1f51194d7001fc9c6b9219726935ede36bc828`, profile, validated 852-member
package, real receipt and guarded installation. Full boot2 readback matched
`73e1ac21860e69f6e8f03fd3625022bd8d4c8e6f189c17ecc44d40f91066ed8d`.
After owner physical selection, strict USB SSH verified the expected aarch64
release and fresh boot `c80f93fe-ea39-4d6e-86b8-bfec0254c65c`.
Both selected-reader and new mask-helper symbol counts were 1; the new helper,
installed checksum/source chain and runtime submission line distinguish C10
from the identical release label on C9. Historical stable-monitor labels do not
identify the actual firmware command.

Execution checkout `8c0b80a238c8a2af76438a7b360ec7b3e0d5a062` ran one
Phase-A capture (ready, exit 0), then one actual session (exit 0). Tool sources
remain the validated `3d1b12f0` cohort; subsequent commits before execution
were source-review documentation. No retry, alternative candidate or concurrent
device accessor. The [predeclared comparison](MASK_ONLY_COMPARISON.md) retained
all RX, crypto, key, frame/byte/wall/grant and cleanup limits.

## Independent verdicts

| Area | Observed result | Limit |
| --- | --- | --- |
| Control | Exactly one enable=1/status=0 and one enable=0/status=0 mask submission. | PIO submission, not an independent firmware completion acknowledgement. Group-bit meanings and maintained register ownership remain unproved. |
| Transport | No refusal, framing-hint fault or join-stopped record in the complete sealed log. Two CLOSED type-2 transfers passed length equality. | One finite comparison does not prove why gap48 occurred previously or that every later lifetime is safe. Equality/full-transfer/poison/no-copy remain mandatory. |
| Network | WPA2 completed; DHCP exit 0, bound and lease-written; 36 checked CCMP Ethernet deliveries; 28 data submissions/completions, zero TX failures. | Initial stable PTK only; native ciphertext queued 0. TX status is not an independent measured over-air ACK. |
| Ping | Three of three individual replies: seq 0/1/2, 102.281/24.678/44.552 ms, TTL 64. | Actual retained replies, not interrupted leaf defaults. |
| SSH | Fresh-boot readiness, attempted authentication, exit 0, boot match and host ACK. | One bounded authenticated exchange, not ten minutes of sustained traffic. |
| Cleanup | CLOSED, deauthentication completed, stage 3, terminal shared pending credit 0. Both local key-disable records status 0/removal-command-credit 1/no-reuse 1. | Host cleanup and returned command credits do not prove shared-RX/key retirement. Stable-CCMP re-arm remains excluded. |
| Security | Existing strict G4/G1, per-frame shape/identity/status and seeded PN checks admitted 36 deliveries without global SET_MONITOR. | Availability is observed; firmware MIC/error attribution, GTK/rekey and stale queued-frame ownership remain separate obligations. |

The data-phase budget was 6200 ms with a 5000 ms teardown margin. Its footer
reported 6210 ms elapsed, within the unchanged grant/teardown protocol. Diagnostic
all-RX count was 192 and byte count 48202, below 512/1 MiB; checked deliveries
36, below 64. No deadline was extended and no acceptance gate was relaxed.
The legacy footer's unicast/group receive counters are separate from the new
checked-delivery counter; do not interpret their zeros as missing network traffic.

## Decision and next boundary

This reaches the predeclared required-metadata/checked-traffic branch and healthy
host-cleanup branch. Retain the mask-only source path as the demonstrated finite
basis. Do not repeat C10 unchanged or promote it directly to a normal board
profile. Absence of the old refusal is an observation, not a proved producer fix.

Next establish a source-supported per-frame integrity/PN and PTK/GTK attribution
contract, including mask ownership. The existing
[RX contract](CCMP_RX_CONTRACT_REVIEW.md) remains provisional; successful traffic
does not resolve error semantics or typed key completion. Keep rejection when
required metadata is absent. The
[key-retirement review](KEY_RETIREMENT_SOURCE_REVIEW.md) identifies two exact
unresolved BSS indirect implementations and the missing shared queued-RX ordering.
Resolve those before rekey, deletion or key-slot reuse; host generation labels,
PN resets, returned credit and elapsed time cannot supply that barrier.

Then refresh the [lifecycle design](../2026-10-07-mt6797-wifi-phase-b-join/REUSABLE_LIFECYCLE_DESIGN.md)
against the corrected source and pinned core callbacks, require both resource
and mac80211 teardown, preserve permanent fatal poison, and demonstrate two
healthy lifetimes in one boot. Only afterward replace diagnostic termination
with source-supported connection/channel monitoring and run the minimal-profile
three-ping/ten-minute authenticated-SSH/disconnect/reconnect acceptance test.
No next kernel candidate or device test is selected by this result.

## Preservation and return

[Scalars](results/ccmp10-runtime-scalars.json) and
[numeric chronology](results/ccmp10-numeric-chronology.txt) contain only fixed
numeric observations, independent network verdicts and sanitized boot identities.
The complete-through-seal log has 169909 bytes and 2113 contiguous records 0–2112,
SHA-256 `6dfc1188decbc6daec2be88daf2e551524b69d2f35f850bf7ec006ee88e562e9`.
All 63 pre-recovery entries independently match seal SHA-256
`2a604e4429101126aca1e1b0990b74027e193a53da2b745a8cd61a4a7b7218a2`.
Raw captures, network data and credentials remain private ignored evidence.

Owned helper safe/group-quiescent, boot-matched device-child quiescence and
A53 regression passed, with no helper timeout/probe/kill error. One reviewed
native return and two finite watcher connection attempts confirmed changed-boot
Gemian `2e2d8be5-54d4-4d99-a40b-91e005d19c1c`. Independent strict read-only
LAN SSH confirmed the same boot, `3.18.41+` and aarch64. C10 remains installed
but consumed; no owner physical selection is pending.
