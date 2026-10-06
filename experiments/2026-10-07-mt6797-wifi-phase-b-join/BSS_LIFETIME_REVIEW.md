# Phase B BSS lifetime correction under review

This is an implementation decision proposal, not device admission. Phase A
artifacts and their protocol remain unchanged.

The existing Phase B design requires a 500 ms quiet window after scan BSS
deactivation before transferring BSS 0, own-MAC 1 and BMC 0. This does not
prove a FIFO drain or completion of the firmware BSS operation. Native RX
metadata supplies frame identities and channel but no scan-versus-join epoch.
A received beacon cannot be declared late scan-owned solely from arrival time.
Those two conditions cannot serve as implementation safety proof.

## Proposed correction: retain one AIS owner

The separate Phase B profile should keep the same AIS BSS active across its
one scan and one join, without a scan-end BSS deactivation/reactivation or
slot release/transfer. BSS 0, own-MAC 1 and BMC 0 remain reserved for that one
firmware session. AP STA/WLAN index 1 and fresh PID/channel tokens are separate
single-use reservations. The existing Phase A scan profile still deactivates
its BSS as before.

The public pinned vendor `gen3/mgmt/ais_fsm.c` supports this intended host
lifetime: the connection-request path in `aisFsmSteps` activates the AIS
network before search; SCAN/ONLINE_SCAN/LOOKING_FOR activates it only if not
already active; the matching LOOKING_FOR scan completion advances the
connection path. This is source evidence for host design, not proof of our
firmware command execution or new mainline runtime.

Public revision: `c5b0be85017ad0c599725e8273842efdbecdd88a` in the
[gen3 AIS state machine](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/ais_fsm.c).

## Required implementation gates

- One completed scan sequence, no pending scan query/command or cancelled
  scan, healthy firmware/owner, all prior TC4 pages reconciled.
- The scan worker is finished before the join worker becomes the sole RX FIFO
  consumer. Host work cancellation is a host ownership fence, not an assertion
  that firmware RX is empty.
- No second scan, BSS owner or peer slot reuse in this firmware session.
- Any additional scan completion/event after the consumed matching completion
  fails stop. Parseable beacons remain asynchronous frames; validate identities
  before optional delivery, never infer their epoch from timing.
- Auth/association responses are matched to one owned AP and live protocol
  state. TXdone, activation and channel grants consume unique pending tokens
  exactly once. A late event cannot revive retired state.
- On healthy teardown only, remove the peer, abort the owned grant and
  deactivate this same BSS. Failure means terminal retirement until recovery,
  not permission to retry cleanup or reuse indices.

Keeping the BSS active changes the Phase B scan-end behavior and must be stated
in its candidate effect review and finite lifetime budget before any boot.
The bounded TX pump must not open based on the older quiet-window rule.
