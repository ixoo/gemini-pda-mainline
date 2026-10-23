# PIO throughput baseline 1 consumed — invalid measurement, independent loss-path failure

One attempt, 2026-10-23, from host revision `b8cc6490`, under the
[predeclaration](THROUGHPUT_BASELINE_PREDECLARATION.md). Fresh boot
`0b917a11-3fcd-4c5b-ab3e-0749ed8066b4` matched installed kernel
`3da69187ec93fd15b28fda3fbdbf118c37ad55a5`, release
`7.1.3-gemini-a53-private-p2e-delivery`, and boot2 SHA-256
`5f63e2d32fc0b921b4fc60d5a50baeb045d1155598ad4108fb0afe6629bfefdd`.
Live notes and RAM members verified before firmware start; the common init
passed 285/285. No build, installation or image change. This consumes the
standing boot allowance; no retry of this consumed run is permitted. A separately named corrected run
is conditional on the owner's subsequent offline gates.

## Measurement result and harness error

Join, DHCP, three of three pings and public-key Wi-Fi SSH authentication
succeeded. BusyBox dd/nc was used because the installed RAM root has no iperf3.
The existing AP/setup and one initial key lifetime were retained.

| Direction | Application observation | Completion/errors | Device CPU idle |
| --- | --- | --- | --- |
| Device TX → host | 842,312 received bytes over 31.067160709 s before SSH died; stalled transfer, invalid baseline | EOF after SSH exit 255; host socket errors 0; no device pipeline exit or final counter snapshot | Unavailable: final snapshot missing |
| Host → device RX | Not started after the first failure | No transfer attempted; zero bytes is not a measured rate | Unavailable |

This baseline is **invalid**; no throughput rate is claimed. The sealed cycle server log
explicitly reports `Idle timeout`, 30 seconds after authentication. The reviewed
leaf starts Wi-Fi dropbear with `-I 30`; the measurement command emits no SSH
output during its bounded 60-second transfer. Carrying that policy into this
quiet command was a harness preparation error, missed by the local socket and
constructor fixtures. The driver window remained open at the post-client USB
check, with no fatal or terminal record then. Do not attribute the interrupted
measurement to a driver cap or use it as a DMA comparison baseline.

Remote tagged owner/process group and local endpoints were proved quiescent.
The command did not emit its final EOS timestamp, so the helper withheld the
standard disconnect: **not attempted**, rather than attempted/refused. The
retained finite session path subsequently ended on connection loss. No second
measurement or control attempt was made. Any future measurement needs an
explicitly reviewed correction for SSH liveness and failure-path teardown;
the owner has since authorized one corrected run only after offline protocol
and loss-path analysis have answers.

Across the sealed session, 626 ordinary TX allocations completed, pending=0,
unowned=0, wraps=4; all 626 ordinary completions report status 0. A separate
reserved completion also reports status 0. In the extended partial device
observation interval [24.580,55.820) s, 591 TX-done records have status 0 and
none nonzero. That interval extends through the post-client observation; it
is not an exact host-transfer interval. Per-direction final netdev deltas and
CPU idle cannot be reconstructed from the retained before-only snapshots.

## Independent first end-to-end connection-loss result

At device log time 387.342600 s, the BSS timeout observation reported reason=4,
beacon age 364290 ms and checked-RX age 143 ms. Data ended for `connection-loss`,
elapsed 366091 ms. This later monitor result is separate from the earlier SSH
idle timeout; no causal claim about the missing beacons is established here.

Reserved PID 127 completed with **TRANSMITTED, status 0, class=2**, at internal
PM+366.357114252 s. The phase=completion delivery line precedes pairwise removal.
There is no cleanup-phase repetition because healthy stage 3 was not reached.
The submission log is at PM+366.332082 s (6.332082 s after a nominal 30-second
multiple); this far-phase observation remains consistent with the earlier
delivery model and does not narrow its blocking window. Log/internal observation
timestamps are not wire timestamps or an acknowledgement/encryption proof.

Mask and PM-abort credit returned; pairwise removal op=2/sequence=32 was
credited. Group removal op=3/sequence=33 was submitted without a retained credit.
The first driver stop reports **status=-110, debt=1, cleanup=0, branch=8**.
The loss-path teardown **did not retire its ledger**. This is the first
end-to-end exercise of the connection-loss path. No stage-3 terminal, whole
ledger, completed key deletion or healthy cleanup is claimed. Both local disable records retain removal_command_credit=0 and
no_reuse=1. No poison/debt/admission rule was weakened. There is no firmware-stop
action or `firmware stopped (` record; OS return does not prove firmware cleanup.

## Preservation, return and decision

Runtime evidence remains private under `artifacts/wifi-throughput-baseline-1/`.
All 73 entries of `PRE_RECOVERY_SHA256SUMS` independently rehashed; its SHA-256
is `92a18018943bf1539fa6563ae36547ea62d966b6e167dda7815022b697b5e1f9`.
Complete kmsg: 616820 bytes, 4602 contiguous records (0–4601), SHA-256
`776b2681c2f74dbad9aae208933edca1b922bb78add0c175b1e6f41e6fc4f908`.
Boot-matched host/device quiescence and A53 RAM-service regression passed.
One reviewed native return succeeded; an independent strict LAN SSH check
confirmed `3.18.41+`/aarch64 and changed Gemian boot
`1c5d22fe-aa8f-4f51-8250-c20790761b9f`. No further device action was taken in this run.

Reconnect stays closed as a limitation; single-lifetime baseline retained and
0229/0230 dormant. The [offline DMA contract](DMA_TRANSFER_CONTRACT.md) still
refuses TX DMA implementation on unknown address routing, ownership and error
quiescence. No DMA option, rebuild or second boot was added. This run establishes
neither a full throughput baseline nor unchanged whole-ledger teardown behavior.
See [sanitized scalars](results/throughput-baseline-1.json).
